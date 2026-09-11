from __future__ import annotations

import itertools
import queue
import threading
from concurrent.futures import Future
from enum import IntEnum
from typing import Any, Callable


class WorkerPriority(IntEnum):
    INTERACTIVE = 0
    NORMAL = 10
    BACKGROUND = 20


class WorkerPool:
    """Small bounded priority worker pool.

    Existing ``submit`` callers keep NORMAL priority. Phase 31 interactive work can
    use ``submit_priority`` without creating an unbounded thread/task queue.
    """

    def __init__(self, max_workers: int = 2, max_pending: int = 256):
        self.max_workers = max(1, int(max_workers))
        self.max_pending = max(self.max_workers, int(max_pending))
        self._queue: queue.PriorityQueue[tuple[int, int, Any]] = queue.PriorityQueue(self.max_pending)
        self._seq = itertools.count()
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._gate = threading.Condition(self._lock)
        self._shutdown = False
        self._active = 0
        self._active_limit = self.max_workers
        for index in range(self.max_workers):
            thread = threading.Thread(target=self._worker, name=f"sp-worker-{index+1}", daemon=True)
            thread.start()
            self._threads.append(thread)

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        return self.submit_priority(WorkerPriority.NORMAL, fn, *args, **kwargs)

    def submit_priority(self, priority: WorkerPriority | int | str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        if isinstance(priority, str):
            priority = {"interactive": WorkerPriority.INTERACTIVE, "background": WorkerPriority.BACKGROUND}.get(priority.casefold(), WorkerPriority.NORMAL)
        value = int(priority)
        with self._lock:
            if self._shutdown:
                raise RuntimeError("WorkerPool has been shut down.")
        future: Future = Future()
        try:
            self._queue.put_nowait((value, next(self._seq), (future, fn, args, kwargs)))
        except queue.Full:
            future.set_exception(RuntimeError("Worker queue is full; try again after current background work finishes."))
        return future

    def set_active_limit(self, value: int) -> int:
        """Limit concurrently executing tasks without recreating worker threads."""
        with self._gate:
            self._active_limit = max(1, min(self.max_workers, int(value)))
            self._gate.notify_all()
            return self._active_limit

    def stats(self) -> dict[str, int]:
        with self._lock:
            active = self._active
            active_limit = self._active_limit
        return {"workers": self.max_workers, "limit": active_limit, "active": active, "pending": self._queue.qsize(), "capacity": self.max_pending}

    def shutdown(self, wait: bool = True, cancel_futures: bool = True) -> None:
        with self._gate:
            if self._shutdown:
                return
            self._shutdown = True
            self._gate.notify_all()
        if cancel_futures:
            while True:
                try:
                    _, _, payload = self._queue.get_nowait()
                except queue.Empty:
                    break
                if payload is not None:
                    payload[0].cancel()
                self._queue.task_done()
        for _ in self._threads:
            self._queue.put((10**9, next(self._seq), None))
        if wait:
            for thread in self._threads:
                thread.join(timeout=5.0)

    def _worker(self) -> None:
        while True:
            _, _, payload = self._queue.get()
            try:
                if payload is None:
                    return
                future, fn, args, kwargs = payload
                if not future.set_running_or_notify_cancel():
                    continue
                with self._gate:
                    while not self._shutdown and self._active >= self._active_limit:
                        self._gate.wait(timeout=0.25)
                    if self._shutdown:
                        future.set_exception(RuntimeError("WorkerPool shut down before this task could run."))
                        continue
                    self._active += 1
                try:
                    future.set_result(fn(*args, **kwargs))
                except BaseException as exc:
                    future.set_exception(exc)
                finally:
                    with self._gate:
                        self._active = max(0, self._active - 1)
                        self._gate.notify_all()
            finally:
                self._queue.task_done()

from __future__ import annotations

import shutil
import threading
import time
from concurrent.futures import Future
from pathlib import Path
from uuid import uuid4

from domain.batch import BatchStatus
from domain.batch_errors import BatchCancelled, BatchLocked
from domain.batch_item import BatchItemStatus
from domain.batch_stage import BatchStage
try:
    from workers.cancellation import CancellationToken
except ImportError:  # pragma: no cover - test/minimal runtime fallback
    class CancellationToken:
        def __init__(self): self._cancel = False
        def cancel(self): self._cancel = True
        @property
        def is_cancelled(self): return self._cancel


_TERMINAL_ITEMS = {
    BatchItemStatus.COMPLETED.value,
    BatchItemStatus.FAILED.value,
    BatchItemStatus.CANCELLED.value,
    BatchItemStatus.SKIPPED.value,
    BatchItemStatus.NEEDS_REVIEW.value,
    BatchItemStatus.OUTPUT_MISSING.value,
}


class BatchScheduler:
    """Single-owner local Batch coordinator using the application's WorkerPool.

    The coordinator itself is a lightweight thread. Actual stage work is submitted
    to the existing WorkerPool, so Phase 26 does not introduce another heavy-job
    queue. Per-stage buckets enforce conservative resource limits; render and TTS
    remain one-at-a-time by default.
    """

    def __init__(self, batch_service, batches, items, worker, worker_pool, *, logger=None, performance_profile="balanced"):
        self.service = batch_service
        self.batches = batches
        self.items = items
        self.worker = worker
        self.pool = worker_pool
        self.logger = logger
        self.owner = f"batch-scheduler-{uuid4()}"
        self.performance_profile = performance_profile
        self._future: Future | None = None
        self._coord_thread: threading.Thread | None = None
        self._token: CancellationToken | None = None
        self._stop = threading.Event()
        self._active_batch = ""
        self.limits = self._limits(performance_profile)

    def start(self, batch_id: str) -> Future:
        if self._future and not self._future.done():
            raise BatchLocked("Another Batch is already active in this application.")
        if not self.batches.acquire_lock(batch_id, self.owner):
            raise BatchLocked()
        self._active_batch = batch_id
        self._token = CancellationToken()
        self._stop.clear()
        self.service.resume(batch_id)
        future: Future = Future()
        self._future = future

        def coordinate() -> None:
            try:
                self._run_loop(batch_id)
            except BaseException as exc:  # Future must observe coordinator failures.
                if not future.done():
                    future.set_exception(exc)
            else:
                if not future.done():
                    future.set_result(None)

        self._coord_thread = threading.Thread(target=coordinate, name=f"BatchScheduler-{batch_id[:8]}", daemon=True)
        self._coord_thread.start()
        return future

    def run_until_idle(self, batch_id: str, *, max_cycles: int = 100000) -> None:
        if not self.batches.acquire_lock(batch_id, self.owner):
            raise BatchLocked()
        self._active_batch = batch_id
        self._token = CancellationToken()
        self._stop.clear()
        self.service.resume(batch_id)
        self._run_loop(batch_id, max_cycles=max_cycles)

    def pause(self, batch_id: str) -> None:
        # Existing atomic TTS/render work may need to finish. The loop observes
        # PAUSED and does not start another stage.
        self.service.pause(batch_id, "User requested pause")

    def resume(self, batch_id: str) -> Future:
        return self.start(batch_id)

    def cancel(self, batch_id: str, *, include_current: bool = False) -> None:
        if include_current and self._token:
            self._token.cancel()
        self.service.cancel_pending(batch_id)
        self._stop.set()

    def shutdown(self) -> None:
        if self._token:
            self._token.cancel()
        self._stop.set()

    def _run_loop(self, batch_id: str, max_cycles: int = 100000) -> None:
        cycles = 0
        active: dict[Future, tuple[str, str]] = {}
        bucket_counts = {name: 0 for name in self.limits}
        try:
            while cycles < max_cycles:
                cycles += 1
                self._reap(active, bucket_counts)
                batch = self.batches.get(batch_id)
                if batch is None:
                    return
                self.batches.heartbeat(batch_id, self.owner)

                # Cancellation may leave already-running atomic jobs. Do not
                # schedule new ones; settle their futures before releasing lock.
                if self._stop.is_set() or batch.status_code == BatchStatus.CANCELLED.value:
                    if active:
                        self._wait_tick(active, bucket_counts)
                        continue
                    return

                if batch.status_code == BatchStatus.PAUSED.value:
                    if active:
                        self._wait_tick(active, bucket_counts)
                        continue
                    return
                if batch.status_code in {BatchStatus.COMPLETED.value, BatchStatus.COMPLETED_WITH_ERRORS.value, BatchStatus.FAILED.value}:
                    if active:
                        self._wait_tick(active, bucket_counts)
                    return

                if not self._disk_ok(batch):
                    self.service.pause(batch_id, "low_disk_space")
                    if active:
                        self._wait_tick(active, bucket_counts)
                        continue
                    return

                all_items = self.items.list_for_batch(batch_id)
                active_ids = {item_id for item_id, _ in active.values()}
                candidates = [x for x in all_items if x.status_code not in _TERMINAL_ITEMS and x.id not in active_ids]

                if not candidates and not active:
                    self._finish(batch_id)
                    return

                scheduled = False
                # Fill available stage buckets. Underlying WorkerPool capacity is
                # still authoritative and may serialize more aggressively.
                while candidates:
                    item = self._pick_schedulable(candidates, batch, bucket_counts)
                    if item is None:
                        break
                    stage = self.worker.execution.next_stage(item, batch)
                    if stage is None:
                        # Finalization is cheap and checkpoint-only.
                        self.worker.execution.finalize_if_done(item, batch)
                        candidates = [x for x in candidates if x.id != item.id]
                        self.service.refresh_counts(batch_id)
                        scheduled = True
                        continue
                    bucket = self._bucket(stage)
                    future = self.pool.submit(
                        self.worker.run_item,
                        batch,
                        item,
                        cancellation=self._token,
                        max_stages=1,
                    )
                    active[future] = (item.id, bucket)
                    bucket_counts[bucket] += 1
                    candidates = [x for x in candidates if x.id != item.id]
                    scheduled = True

                if active:
                    if not scheduled or all(bucket_counts[k] >= self.limits[k] for k in bucket_counts):
                        self._wait_tick(active, bucket_counts)
                    else:
                        time.sleep(0.002)
                elif not scheduled:
                    # Nothing was runnable (for example all items failed during
                    # resolution between refreshes). Re-evaluate and finish.
                    self.service.refresh_counts(batch_id)
                    time.sleep(0.002)

                self.service.refresh_counts(batch_id)
        finally:
            # On coordinator exit, never abandon in-process futures while still
            # claiming the DB scheduler lease.
            while active:
                self._wait_tick(active, bucket_counts)
            self.batches.release_lock(batch_id, self.owner)
            if self._active_batch == batch_id:
                self._active_batch = ""

    def _reap(self, active: dict[Future, tuple[str, str]], bucket_counts: dict[str, int]) -> None:
        for future, (_, bucket) in list(active.items()):
            if not future.done():
                continue
            try:
                future.result()
            except BatchCancelled:
                self._stop.set()
            except Exception:
                # BatchExecutionService has already persisted the item/stage error.
                pass
            bucket_counts[bucket] = max(0, bucket_counts[bucket] - 1)
            active.pop(future, None)

    def _wait_tick(self, active: dict[Future, tuple[str, str]], bucket_counts: dict[str, int]) -> None:
        time.sleep(0.01)
        self._reap(active, bucket_counts)

    def _finish(self, batch_id: str) -> None:
        b = self.service.refresh_counts(batch_id)
        items = self.items.list_for_batch(batch_id)
        if any(x.status_code in {BatchItemStatus.FAILED.value, BatchItemStatus.OUTPUT_MISSING.value, BatchItemStatus.INTERRUPTED.value} for x in items):
            b.status = BatchStatus.COMPLETED_WITH_ERRORS.value
        elif all(x.status_code in {BatchItemStatus.COMPLETED.value, BatchItemStatus.SKIPPED.value, BatchItemStatus.CANCELLED.value} for x in items):
            b.status = BatchStatus.COMPLETED.value
        self.batches.save(b)

    def _pick_schedulable(self, items, batch, bucket_counts):
        ranked = sorted(items, key=lambda item: self._item_key(item, batch))
        for item in ranked:
            stage = self.worker.execution.next_stage(item, batch)
            if stage is None:
                return item
            bucket = self._bucket(stage)
            if bucket_counts[bucket] < self._effective_limit(batch, bucket):
                return item
        return None

    def _item_key(self, item, batch):
        # Group compatible model work to reduce engine/language/voice switching,
        # while row/output identity remains untouched.
        stage = self.worker.execution.next_stage(item, batch) or "zz"
        return (
            stage,
            str(item.resolved_data.get("language") or ""),
            str(item.resolved_data.get("voice") or item.resolved_data.get("voice_id") or ""),
            item.row_index,
            item.item_key,
        )

    def _effective_limit(self, batch, bucket: str) -> int:
        raw = batch.settings.get("concurrency") if isinstance(batch.settings, dict) else None
        if isinstance(raw, dict):
            try:
                requested = int(raw.get(bucket, self.limits[bucket]))
            except (TypeError, ValueError):
                requested = self.limits[bucket]
            # Render/TTS are intentionally capped at one in Phase 26 even if a
            # malformed setup asks for unbounded heavy work.
            safe_cap = 1 if bucket in {"render", "tts"} else max(1, self.limits[bucket])
            return max(1, min(requested, safe_cap))
        return self.limits[bucket]

    def _disk_ok(self, batch) -> bool:
        try:
            free = shutil.disk_usage(Path(batch.output_directory)).free
        except OSError:
            return True
        reserve = int(batch.settings.get("disk_reserve_bytes") or 512 * 1024 * 1024)
        return free > reserve

    @staticmethod
    def _bucket(stage: str | None) -> str:
        if stage == BatchStage.GENERATE_TTS.value:
            return "tts"
        if stage == BatchStage.TRANSLATE.value:
            return "translation"
        if stage in {BatchStage.RENDER.value, BatchStage.EXPORT.value}:
            return "render"
        if stage == BatchStage.CREATE_PROJECT.value:
            return "project"
        return "light"

    @staticmethod
    def _limits(profile: str):
        if profile == "low_memory":
            return {"project": 1, "light": 1, "translation": 1, "tts": 1, "render": 1}
        if profile == "maximum_throughput":
            return {"project": 3, "light": 4, "translation": 2, "tts": 1, "render": 1}
        if profile == "auto":
            return {"project": 2, "light": 3, "translation": 1, "tts": 1, "render": 1}
        return {"project": 2, "light": 2, "translation": 1, "tts": 1, "render": 1}

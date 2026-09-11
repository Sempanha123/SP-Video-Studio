from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import Future
from workers.worker_pool import WorkerPriority


@dataclass(frozen=True, slots=True)
class ThumbnailRequest:
    request_id: int
    owner: str
    key: str
    future: Future


class ThumbnailRequestService:
    """Deduplicates thumbnail jobs and lets UI ignore stale/off-screen results."""
    def __init__(self, thumbnail_service, worker_pool, max_inflight: int = 128):
        self.thumbnail_service = thumbnail_service
        self.worker_pool = worker_pool
        self.max_inflight = max(8, int(max_inflight))
        self._lock = threading.RLock()
        self._inflight: dict[str, Future] = {}
        self._owner_version: dict[str, int] = {}

    def request(self, owner: str, media_type: str, source: str | Path, destination: str | Path, *, duration_ms=None, priority="normal") -> ThumbnailRequest:
        src = Path(source)
        dst = Path(destination)
        try:
            stat = src.stat(); fingerprint = f"{src.resolve(strict=False)}|{stat.st_size}|{stat.st_mtime_ns}"
        except OSError:
            fingerprint = str(src.resolve(strict=False))
        key = f"{media_type}|{fingerprint}|{dst.resolve(strict=False)}"
        with self._lock:
            version = self._owner_version.get(owner, 0) + 1
            self._owner_version[owner] = version
            future = self._inflight.get(key)
            if future is None or future.done():
                p = {"interactive": WorkerPriority.INTERACTIVE, "background": WorkerPriority.BACKGROUND}.get(str(priority), WorkerPriority.NORMAL)
                submit = getattr(self.worker_pool, "submit_priority", None)
                if submit:
                    future = submit(p, self.thumbnail_service.generate, media_type, src, dst, duration_ms=duration_ms)
                else:
                    future = self.worker_pool.submit(self.thumbnail_service.generate, media_type, src, dst, duration_ms=duration_ms)
                self._inflight[key] = future
                future.add_done_callback(lambda f, k=key: self._forget(k, f))
            return ThumbnailRequest(version, owner, key, future)

    def is_current(self, request: ThumbnailRequest) -> bool:
        with self._lock:
            return self._owner_version.get(request.owner, 0) == request.request_id

    def cancel_owner(self, owner: str) -> None:
        with self._lock:
            self._owner_version[owner] = self._owner_version.get(owner, 0) + 1

    def _forget(self, key: str, future: Future) -> None:
        with self._lock:
            if self._inflight.get(key) is future:
                self._inflight.pop(key, None)

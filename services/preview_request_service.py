from __future__ import annotations

import threading
from dataclasses import dataclass
from concurrent.futures import Future
from workers.worker_pool import WorkerPriority


@dataclass(frozen=True, slots=True)
class PreviewRequest:
    scope: str
    version: int
    future: Future


class PreviewRequestService:
    """Versioned preview jobs; late results can never replace newer scene state."""
    def __init__(self, worker_pool):
        self.pool = worker_pool
        self._lock = threading.Lock()
        self._versions: dict[str, int] = {}

    def request(self, scope: str, fn, *args, **kwargs) -> PreviewRequest:
        with self._lock:
            version = self._versions.get(scope, 0) + 1
            self._versions[scope] = version
        submit = getattr(self.pool, "submit_priority", None)
        future = submit(WorkerPriority.INTERACTIVE, fn, *args, **kwargs) if submit else self.pool.submit(fn, *args, **kwargs)
        return PreviewRequest(scope, version, future)

    def is_current(self, request: PreviewRequest) -> bool:
        with self._lock:
            return self._versions.get(request.scope, 0) == request.version

    def invalidate(self, scope: str) -> None:
        with self._lock:
            self._versions[scope] = self._versions.get(scope, 0) + 1

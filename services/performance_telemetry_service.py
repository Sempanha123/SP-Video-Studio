from __future__ import annotations

import os
import threading
from domain.performance import PerformanceSnapshot

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


class PerformanceTelemetryService:
    """Local-only lightweight telemetry. No upload or persistence."""
    def __init__(self, worker_pool=None, profile_service=None, active_model_provider=None):
        self.worker_pool = worker_pool
        self.profile_service = profile_service
        self.active_model_provider = active_model_provider or (lambda: "")

    def snapshot(self) -> PerformanceSnapshot:
        ram = available = 0
        try:
            if psutil:
                proc = psutil.Process(os.getpid())
                ram = int(proc.memory_info().rss)
                available = int(psutil.virtual_memory().available)
        except Exception:
            pass
        stats = self.worker_pool.stats() if self.worker_pool and hasattr(self.worker_pool, "stats") else {}
        return PerformanceSnapshot(
            process_ram_bytes=ram,
            system_available_bytes=available,
            thread_count=threading.active_count(),
            active_workers=int(stats.get("active", 0)),
            pending_workers=int(stats.get("pending", 0)),
            active_model=str(self.active_model_provider() or ""),
            preview_mode=str(getattr(self.profile_service, "preview_quality", "auto")),
        )

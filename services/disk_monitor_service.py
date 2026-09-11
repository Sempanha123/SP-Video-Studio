from __future__ import annotations
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Any
from domain.cache_errors import DiskSpaceCritical
from domain.storage_usage import readable_size


class DiskState(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    CRITICAL = "critical"


@dataclass(slots=True)
class DiskStatus:
    path: str
    state: DiskState
    total_bytes: int
    free_bytes: int
    free_percent: float
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "state": self.state.value, "totalBytes": self.total_bytes, "freeBytes": self.free_bytes, "freeDisplay": readable_size(self.free_bytes), "freePercent": self.free_percent, "label": self.label}


class DiskMonitorService:
    def __init__(self, *, low_bytes: int = 10 * 1024**3, critical_bytes: int = 3 * 1024**3, low_percent: float = 10.0, critical_percent: float = 3.0, disk_usage=shutil.disk_usage, logger=None) -> None:
        self.low_bytes = int(low_bytes); self.critical_bytes = int(critical_bytes)
        self.low_percent = float(low_percent); self.critical_percent = float(critical_percent)
        self.disk_usage = disk_usage; self.logger = logger

    def check(self, path: str | Path, *, estimated_bytes: int = 0, label: str = "") -> DiskStatus:
        target = self._existing_parent(Path(path))
        usage = self.disk_usage(target)
        free = max(0, int(usage.free) - max(0, int(estimated_bytes)))
        total = max(1, int(usage.total))
        percent = free * 100.0 / total
        if free < self.critical_bytes or percent < self.critical_percent:
            state = DiskState.CRITICAL
        elif free < self.low_bytes or percent < self.low_percent:
            state = DiskState.LOW
        else:
            state = DiskState.NORMAL
        return DiskStatus(str(target), state, total, free, percent, label)

    def check_many(self, roots: Iterable[tuple[str, str | Path]]) -> list[DiskStatus]:
        results: list[DiskStatus] = []
        seen: set[str] = set()
        for label, path in roots:
            try: status = self.check(path, label=label)
            except OSError: continue
            key = str(Path(status.path).anchor or status.path).casefold()
            if key in seen: continue
            seen.add(key); results.append(status)
        return results

    def can_start_heavy(self, path: str | Path, *, estimated_bytes: int = 0) -> bool:
        try: return self.check(path, estimated_bytes=estimated_bytes).state != DiskState.CRITICAL
        except OSError: return True

    def require_space(self, path: str | Path, *, estimated_bytes: int = 0, operation: str = "operation") -> DiskStatus:
        status = self.check(path, estimated_bytes=estimated_bytes)
        if status.state == DiskState.CRITICAL:
            if self.logger: self.logger.warning("Critical disk space blocked %s at %s", operation, status.path)
            raise DiskSpaceCritical("Storage is almost full. Free space before rendering.")
        return status

    @staticmethod
    def _existing_parent(path: Path) -> Path:
        current = path.expanduser().resolve(strict=False)
        while not current.exists() and current != current.parent:
            current = current.parent
        return current

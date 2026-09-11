from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import StrEnum


class PerformanceProfile(StrEnum):
    AUTO = "auto"
    LOW_MEMORY = "low_memory"
    BALANCED = "balanced"
    MAXIMUM_QUALITY = "maximum_quality"


class PreviewQuality(StrEnum):
    AUTO = "auto"
    PERFORMANCE = "performance"
    QUALITY = "quality"


@dataclass(frozen=True, slots=True)
class PreviewPolicy:
    mode: str
    proxy_height: int
    expensive_preview_effects: bool
    thumbnail_density: str
    max_decoders: int

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    process_ram_bytes: int = 0
    system_available_bytes: int = 0
    thread_count: int = 0
    active_workers: int = 0
    pending_workers: int = 0
    active_model: str = ""
    preview_mode: str = "auto"

    def to_dict(self):
        return asdict(self)

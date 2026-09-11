from __future__ import annotations
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from .cache_entry import CacheEntry
from .storage_category import StorageCategory


@dataclass(slots=True)
class CleanupPolicy:
    maximum_cache_bytes: int = 25 * 1024**3
    automatic_cleanup: str = "balanced"  # off | conservative | balanced
    cleanup_stale_temp: bool = True
    log_retention_days: int = 14
    stale_age_seconds: dict[StorageCategory, int] = field(default_factory=lambda: {
        StorageCategory.RENDER_TEMP: int(timedelta(hours=24).total_seconds()),
        StorageCategory.TRANSCRIPTION_TEMP: int(timedelta(hours=24).total_seconds()),
        StorageCategory.BATCH_INTERMEDIATE: int(timedelta(hours=24).total_seconds()),
        StorageCategory.TEMPLATE_CACHE: int(timedelta(days=2).total_seconds()),
        StorageCategory.PREVIEW_CACHE: int(timedelta(days=7).total_seconds()),
        StorageCategory.THUMBNAIL_CACHE: int(timedelta(days=30).total_seconds()),
        StorageCategory.ASSET_THUMBNAIL_CACHE: int(timedelta(days=30).total_seconds()),
        StorageCategory.TRANSLATION_CACHE: int(timedelta(days=14).total_seconds()),
        StorageCategory.GENERATED_AUDIO: int(timedelta(days=7).total_seconds()),
        StorageCategory.LOGS: int(timedelta(days=14).total_seconds()),
    })

    def stale_seconds(self, category: StorageCategory) -> int:
        return max(0, int(self.stale_age_seconds.get(category, 7 * 24 * 3600)))


@dataclass(slots=True)
class CleanupPlan:
    entries: list[CacheEntry] = field(default_factory=list)
    estimated_bytes: int = 0
    skipped_protected: list[str] = field(default_factory=list)
    skipped_active: list[str] = field(default_factory=list)
    skipped_unsafe: list[str] = field(default_factory=list)
    reason: str = "manual"

    def add(self, entry: CacheEntry) -> None:
        self.entries.append(entry)
        self.estimated_bytes += max(0, int(entry.size_bytes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [str(x.path) for x in self.entries],
            "entryCount": len(self.entries),
            "estimatedBytes": self.estimated_bytes,
            "skippedProtected": list(self.skipped_protected),
            "skippedActive": list(self.skipped_active),
            "skippedUnsafe": list(self.skipped_unsafe),
            "reason": self.reason,
        }


@dataclass(slots=True)
class CleanupResult:
    freed_bytes: int = 0
    deleted: list[str] = field(default_factory=list)
    skipped_active: list[str] = field(default_factory=list)
    skipped_protected: list[str] = field(default_factory=list)
    skipped_unsafe: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "freedBytes": self.freed_bytes,
            "deleted": list(self.deleted),
            "deletedCount": len(self.deleted),
            "skippedActive": list(self.skipped_active),
            "skippedProtected": list(self.skipped_protected),
            "skippedUnsafe": list(self.skipped_unsafe),
            "failed": list(self.failed),
        }

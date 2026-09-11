from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .storage_category import StorageCategory, StorageSafety, definition


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class CacheEntry:
    path: Path
    category: StorageCategory
    project_id: str = ""
    size_bytes: int = 0
    created_at: str = ""
    last_accessed_at: str = ""
    regeneratable: bool = False
    protected: bool = False
    origin: str = "scan"
    owner_id: str = ""
    source_fingerprint: str = ""
    cache_version: str = "1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if not isinstance(self.category, StorageCategory):
            self.category = StorageCategory(str(self.category))
        self.size_bytes = max(0, int(self.size_bytes or 0))
        rule = definition(self.category)
        if rule.safety == StorageSafety.REGENERATABLE:
            self.regeneratable = True
        if rule.safety in {StorageSafety.PROTECTED, StorageSafety.USER_DATA, StorageSafety.EXTERNAL}:
            self.protected = True
        if not self.created_at:
            self.created_at = utc_iso()
        if not self.last_accessed_at:
            self.last_accessed_at = self.created_at

    @property
    def safety(self) -> StorageSafety:
        return definition(self.category).safety

    @property
    def safe_to_clear(self) -> bool:
        return not self.protected and self.safety in {StorageSafety.SAFE_TO_CLEAR, StorageSafety.REGENERATABLE}

    def to_manifest(self) -> dict[str, Any]:
        return {
            "path": self.path.name,
            "category": self.category.value,
            "projectId": self.project_id,
            "ownerId": self.owner_id,
            "sizeBytes": self.size_bytes,
            "createdAt": self.created_at,
            "lastUsed": self.last_accessed_at,
            "safeToDelete": self.safe_to_clear,
            "regeneratable": self.regeneratable,
            "protected": self.protected,
            "origin": self.origin,
            "sourceFingerprint": self.source_fingerprint,
            "cacheVersion": self.cache_version,
            "metadata": dict(self.metadata),
        }

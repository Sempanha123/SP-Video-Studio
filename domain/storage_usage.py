from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .storage_category import StorageCategory, StorageSafety, definition


def readable_size(value: int) -> str:
    size = max(0, int(value or 0))
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(size)
    index = 0
    while amount >= 1024 and index < len(units) - 1:
        amount /= 1024.0
        index += 1
    if index == 0:
        return f"{int(amount)} B"
    digits = 0 if amount >= 100 else (1 if amount >= 10 else 2)
    return f"{amount:.{digits}f} {units[index]}"


@dataclass(slots=True)
class StorageUsage:
    category: StorageCategory
    size_bytes: int = 0
    item_count: int = 0
    external_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return definition(self.category).label

    @property
    def safety(self) -> StorageSafety:
        return definition(self.category).safety

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "label": self.label,
            "safety": self.safety.value,
            "sizeBytes": int(self.size_bytes),
            "sizeDisplay": readable_size(self.size_bytes),
            "itemCount": int(self.item_count),
            "externalBytes": int(self.external_bytes),
            "externalDisplay": readable_size(self.external_bytes),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ProjectStorageUsage:
    project_id: str
    name: str
    root: str
    project_data_bytes: int = 0
    media_bytes: int = 0
    generated_audio_bytes: int = 0
    cache_bytes: int = 0
    exports_bytes: int = 0

    @property
    def total_bytes(self) -> int:
        return self.project_data_bytes + self.media_bytes + self.generated_audio_bytes + self.cache_bytes + self.exports_bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "projectId": self.project_id,
            "name": self.name,
            "root": self.root,
            "projectDataBytes": self.project_data_bytes,
            "projectDataDisplay": readable_size(self.project_data_bytes),
            "mediaBytes": self.media_bytes,
            "mediaDisplay": readable_size(self.media_bytes),
            "generatedAudioBytes": self.generated_audio_bytes,
            "generatedAudioDisplay": readable_size(self.generated_audio_bytes),
            "cacheBytes": self.cache_bytes,
            "cacheDisplay": readable_size(self.cache_bytes),
            "exportsBytes": self.exports_bytes,
            "exportsDisplay": readable_size(self.exports_bytes),
            "totalBytes": self.total_bytes,
            "totalDisplay": readable_size(self.total_bytes),
        }

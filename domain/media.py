from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


class MediaType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class MediaStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    MISSING = "missing"
    INVALID = "invalid"
    FAILED = "failed"


def media_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_value(value: str | StrEnum) -> str:
    return value.value if isinstance(value, StrEnum) else str(value)


@dataclass(slots=True)
class MediaAsset:
    project_id: str
    media_type: str | MediaType
    name: str
    original_path: str
    project_path: str
    file_size: int
    asset_id: str = field(default_factory=lambda: str(uuid4()))
    thumbnail_path: str | None = None
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec: str | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    mime_type: str | None = None
    extension: str = ""
    created_at: str = field(default_factory=media_utc_now_iso)
    imported_at: str = field(default_factory=media_utc_now_iso)
    status: str | MediaStatus = MediaStatus.READY
    metadata_json: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.asset_id

    @property
    def type(self) -> str:
        return _enum_value(self.media_type)

    @property
    def path(self) -> Path:
        """Compatibility alias for the project-managed copy."""
        return Path(self.project_path)

    def validate(self) -> None:
        if not self.asset_id:
            raise ValueError("Media ID is required.")
        if not self.project_id:
            raise ValueError("Project ID is required.")
        if self.type not in {item.value for item in MediaType}:
            raise ValueError("Unsupported media type.")
        if _enum_value(self.status) not in {item.value for item in MediaStatus}:
            raise ValueError("Unsupported media status.")
        if not self.name:
            raise ValueError("Media display name is required.")
        if not self.project_path:
            raise ValueError("Project media path is required.")
        if self.file_size < 0:
            raise ValueError("Media file size cannot be negative.")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("Media duration cannot be negative.")
        if self.width is not None and self.width <= 0:
            raise ValueError("Media width must be positive.")
        if self.height is not None and self.height <= 0:
            raise ValueError("Media height must be positive.")
        if self.fps is not None and self.fps < 0:
            raise ValueError("Media FPS cannot be negative.")

    def with_status(self, status: str | MediaStatus) -> "MediaAsset":
        updated = replace(self, status=status)
        updated.validate()
        return updated

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.asset_id,
            "project_id": self.project_id,
            "type": self.type,
            "name": self.name,
            "original_path": self.original_path,
            "project_path": self.project_path,
            "thumbnail_path": self.thumbnail_path,
            "duration_ms": self.duration_ms,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "codec": self.codec,
            "audio_codec": self.audio_codec,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "extension": self.extension,
            "created_at": self.created_at,
            "imported_at": self.imported_at,
            "status": _enum_value(self.status),
            "metadata_json": dict(self.metadata_json),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "MediaAsset":
        import json

        raw_metadata = record["metadata_json"] if "metadata_json" in record.keys() else None
        if raw_metadata:
            try:
                metadata = json.loads(str(raw_metadata))
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = {}
        return cls(
            asset_id=str(record["id"]),
            project_id=str(record["project_id"]),
            media_type=str(record["type"]),
            name=str(record["name"]),
            original_path=str(record["original_path"] or ""),
            project_path=str(record["project_path"]),
            thumbnail_path=str(record["thumbnail_path"]) if record["thumbnail_path"] else None,
            duration_ms=int(record["duration_ms"]) if record["duration_ms"] is not None else None,
            width=int(record["width"]) if record["width"] is not None else None,
            height=int(record["height"]) if record["height"] is not None else None,
            fps=float(record["fps"]) if record["fps"] is not None else None,
            codec=str(record["codec"]) if record["codec"] else None,
            audio_codec=str(record["audio_codec"]) if record["audio_codec"] else None,
            sample_rate=int(record["sample_rate"]) if record["sample_rate"] is not None else None,
            channels=int(record["channels"]) if record["channels"] is not None else None,
            file_size=int(record["file_size"]),
            mime_type=str(record["mime_type"]) if record["mime_type"] else None,
            extension=str(record["extension"] or ""),
            created_at=str(record["created_at"]),
            imported_at=str(record["imported_at"]),
            status=str(record["status"]),
            metadata_json=metadata if isinstance(metadata, dict) else {},
        )

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class SubtitleTrackType(StrEnum):
    TRANSCRIPT = "transcript"
    TRANSLATION = "translation"
    MANUAL = "manual"
    BILINGUAL = "bilingual"


class SubtitleTrackStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    OUTDATED = "outdated"
    FAILED = "failed"
    SOURCE_MISSING = "source_missing"


@dataclass(slots=True)
class SubtitleTrack:
    project_id: str
    name: str
    language: str
    track_type: str | SubtitleTrackType = SubtitleTrackType.MANUAL
    source_type: str = "manual"
    source_id: str = ""
    source_language: str = ""
    status: str | SubtitleTrackStatus = SubtitleTrackStatus.DRAFT
    style_id: str = ""
    is_default: bool = False
    is_bilingual: bool = False
    secondary_language: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    track_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.track_id

    @property
    def track_type_code(self) -> str:
        return self.track_type.value if isinstance(self.track_type, StrEnum) else str(self.track_type)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.track_id or not self.project_id:
            raise ValueError("Subtitle track identity and project are required.")
        if not self.name.strip():
            raise ValueError("Subtitle track name is required.")
        if not self.language:
            raise ValueError("Subtitle language is required.")
        if self.track_type_code not in {item.value for item in SubtitleTrackType}:
            raise ValueError("Unsupported subtitle track type.")
        if self.status_code not in {item.value for item in SubtitleTrackStatus}:
            raise ValueError("Unsupported subtitle track status.")
        if self.is_bilingual and not self.secondary_language:
            raise ValueError("Bilingual subtitle tracks require a secondary language.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.track_id,
            "project_id": self.project_id,
            "name": self.name,
            "language": self.language,
            "track_type": self.track_type_code,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_language": self.source_language,
            "status": self.status_code,
            "style_id": self.style_id,
            "is_default": self.is_default,
            "is_bilingual": self.is_bilingual,
            "secondary_language": self.secondary_language,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "SubtitleTrack":
        try:
            metadata = json.loads(record["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            track_id=str(record["id"]), project_id=str(record["project_id"]), name=str(record["name"]),
            language=str(record["language"]), track_type=str(record["track_type"]),
            source_type=str(record["source_type"]), source_id=str(record["source_id"] or ""),
            source_language=str(record["source_language"] or ""), status=str(record["status"]),
            style_id=str(record["style_id"] or ""), is_default=bool(record["is_default"]),
            is_bilingual=bool(record["is_bilingual"]), secondary_language=str(record["secondary_language"] or ""),
            metadata=metadata if isinstance(metadata, dict) else {}, created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )


def subtitle_source_fingerprint(parts: list[tuple[str, str, int | None, int | None]]) -> str:
    digest = hashlib.sha256()
    for source_id, text, start_ms, end_ms in parts:
        digest.update(f"{source_id}\0{start_ms}\0{end_ms}\0{text}\n".encode("utf-8"))
    return digest.hexdigest()

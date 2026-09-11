from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from domain.language import supported_language_codes
from domain.project import utc_now_iso
from domain.short_style import SHORT_STYLES


class ShortSourceType(StrEnum):
    VIDEO = "video"
    TRANSCRIPT = "transcript"
    SCRIPT = "script"
    SCENES = "scenes"
    NEWS = "news"
    STORY = "story"
    DUB = "dub"
    MANUAL = "manual"


class ShortProjectStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    READY = "ready"
    OUTDATED = "outdated"


SHORT_ASPECTS = {"9:16", "1:1", "16:9"}
TARGET_DURATION_CHOICES = (15_000, 30_000, 45_000, 60_000, 90_000)


@dataclass(slots=True)
class ShortProject:
    project_id: str
    source_type: str | ShortSourceType = ShortSourceType.MANUAL
    source_id: str = ""
    target_duration_ms: int = 30_000
    target_aspect_ratio: str = "9:16"
    language: str = "en"
    platform: str = "generic"
    style: str = "creator"
    status: str | ShortProjectStatus = ShortProjectStatus.DRAFT
    source_project_id: str = ""
    source_entity_ids: list[str] = field(default_factory=list)
    source_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    @property
    def source_type_code(self) -> str:
        return self.source_type.value if isinstance(self.source_type, StrEnum) else str(self.source_type)

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("Shorts metadata requires a project.")
        if self.source_type_code not in {x.value for x in ShortSourceType}:
            raise ValueError("Unsupported Short source type.")
        if int(self.target_duration_ms) <= 0:
            raise ValueError("Target duration must be greater than zero.")
        if self.target_aspect_ratio not in SHORT_ASPECTS:
            raise ValueError("Unsupported Short aspect ratio.")
        if self.language not in set(supported_language_codes()):
            raise ValueError("Unsupported Short language.")
        if not self.platform.strip():
            raise ValueError("Short platform is required.")
        if self.style not in SHORT_STYLES:
            raise ValueError("Unsupported Short style.")
        if self.status_code not in {x.value for x in ShortProjectStatus}:
            raise ValueError("Unsupported Shorts status.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "projectId": self.project_id,
            "sourceType": self.source_type_code,
            "sourceId": self.source_id,
            "targetDurationMs": self.target_duration_ms,
            "targetAspectRatio": self.target_aspect_ratio,
            "language": self.language,
            "platform": self.platform,
            "style": self.style,
            "status": self.status_code,
            "sourceProjectId": self.source_project_id,
            "sourceEntityIds": list(self.source_entity_ids),
            "sourceFingerprint": self.source_fingerprint,
            "metadata": dict(self.metadata),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "ShortProject":
        def decode(key: str, fallback):
            try:
                value = json.loads(row[key] or "null")
                return value if value is not None else fallback
            except Exception:
                return fallback
        return cls(
            project_id=str(row["project_id"]), source_type=str(row["source_type"]), source_id=str(row["source_id"] or ""),
            target_duration_ms=int(row["target_duration_ms"]), target_aspect_ratio=str(row["target_aspect_ratio"]),
            language=str(row["language"]), platform=str(row["platform"]), style=str(row["style"]), status=str(row["status"]),
            source_project_id=str(row["source_project_id"] or ""), source_entity_ids=list(decode("source_entity_ids_json", [])),
            source_fingerprint=str(row["source_fingerprint"] or ""), metadata=dict(decode("metadata_json", {})),
            created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
        )

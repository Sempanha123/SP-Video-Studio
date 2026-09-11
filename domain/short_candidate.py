from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso
from domain.short_project import ShortSourceType


class ShortCandidateStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    RENDERED = "rendered"
    OUTDATED = "outdated"


_FORBIDDEN_SCORE_KEYS = {"viral", "viral_score", "engagement", "engagement_score", "retention_score", "prediction"}


@dataclass(slots=True)
class ShortCandidate:
    project_id: str
    source_type: str | ShortSourceType
    source_id: str
    title: str
    start_ms: int
    end_ms: int
    language: str = "en"
    hook: str = ""
    status: str | ShortCandidateStatus = ShortCandidateStatus.DRAFT
    source_project_id: str = ""
    source_entity_ids: list[str] = field(default_factory=list)
    source_fingerprint: str = ""
    score_metadata: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    candidate_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def id(self) -> str:
        return self.candidate_id

    @property
    def duration_ms(self) -> int:
        return max(0, int(self.end_ms) - int(self.start_ms))

    @property
    def source_type_code(self) -> str:
        return self.source_type.value if isinstance(self.source_type, StrEnum) else str(self.source_type)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.project_id or not self.source_id:
            raise ValueError("Short candidate requires project and source identity.")
        if self.source_type_code not in {x.value for x in ShortSourceType}:
            raise ValueError("Unsupported Short candidate source.")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Set an Out point after the In point.")
        if self.status_code not in {x.value for x in ShortCandidateStatus}:
            raise ValueError("Unsupported Short candidate status.")
        if not self.title.strip():
            raise ValueError("Short candidate title is required.")
        lowered = {str(k).lower() for k in self.score_metadata}
        if lowered & _FORBIDDEN_SCORE_KEYS:
            raise ValueError("Shorts Maker does not store fake viral/engagement predictions.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "id": self.id, "projectId": self.project_id, "sourceType": self.source_type_code, "sourceId": self.source_id,
            "title": self.title, "hook": self.hook, "startMs": self.start_ms, "endMs": self.end_ms,
            "durationMs": self.duration_ms, "language": self.language, "status": self.status_code,
            "sourceProjectId": self.source_project_id, "sourceEntityIds": list(self.source_entity_ids),
            "sourceFingerprint": self.source_fingerprint, "scoreMetadata": dict(self.score_metadata),
            "metadata": dict(self.metadata), "createdAt": self.created_at, "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "ShortCandidate":
        def decode(key: str, fallback):
            try:
                value = json.loads(row[key] or "null")
                return value if value is not None else fallback
            except Exception:
                return fallback
        return cls(
            candidate_id=str(row["id"]), project_id=str(row["project_id"]), source_type=str(row["source_type"]),
            source_id=str(row["source_id"]), title=str(row["title"]), hook=str(row["hook"] or ""),
            start_ms=int(row["start_ms"]), end_ms=int(row["end_ms"]), language=str(row["language"]), status=str(row["status"]),
            source_project_id=str(row["source_project_id"] or ""), source_entity_ids=list(decode("source_entity_ids_json", [])),
            source_fingerprint=str(row["source_fingerprint"] or ""), score_metadata=dict(decode("score_metadata_json", {})),
            metadata=dict(decode("metadata_json", {})), created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
        )

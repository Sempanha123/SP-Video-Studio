from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from domain.project import utc_now_iso


class NewsProjectStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    READY = "ready"
    OUTDATED = "outdated"


@dataclass(slots=True)
class NewsProjectMetadata:
    project_id: str
    topic: str = ""
    angle: str = "general_update"
    region: str = ""
    language: str = "en"
    target_audience: str = "general"
    target_duration_ms: int = 60_000
    platform: str = "generic"
    status: str | NewsProjectStatus = NewsProjectStatus.DRAFT
    source_fingerprint: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("Project ID is required.")
        if self.language not in {"en", "km"}:
            raise ValueError("News Studio currently supports English and Khmer project languages.")
        if self.target_duration_ms <= 0:
            raise ValueError("Target duration must be positive.")
        if self.status_code not in {item.value for item in NewsProjectStatus}:
            raise ValueError("Unsupported News project status.")

    def to_dict(self) -> dict[str, object]:
        return {
            "projectId": self.project_id,
            "topic": self.topic,
            "angle": self.angle,
            "region": self.region,
            "language": self.language,
            "targetAudience": self.target_audience,
            "targetDurationMs": self.target_duration_ms,
            "platform": self.platform,
            "status": self.status_code,
            "sourceFingerprint": self.source_fingerprint,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsProjectMetadata":
        return cls(
            project_id=str(row["project_id"]), topic=str(row["topic"] or ""),
            angle=str(row["angle"] or "general_update"), region=str(row["region"] or ""),
            language=str(row["language"] or "en"), target_audience=str(row["target_audience"] or "general"),
            target_duration_ms=int(row["target_duration_ms"] or 60_000), platform=str(row["platform"] or "generic"),
            status=str(row["status"] or "draft"), source_fingerprint=str(row["source_fingerprint"] or ""),
            created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
            metadata=json.loads(str(row["metadata_json"] or "{}")),
        )

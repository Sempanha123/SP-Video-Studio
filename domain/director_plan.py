from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.director_profile import PLATFORM_PROFILES, SUPPORTED_AUDIENCES, SUPPORTED_PACES, SUPPORTED_STYLES, SUPPORTED_TONES, WORKFLOW_PROFILES
from domain.director_recommendation import DirectorRecommendation
from domain.project import SUPPORTED_ASPECT_RATIOS, SUPPORTED_LANGUAGES, utc_now_iso

DIRECTOR_SCHEMA_VERSION = 1
DIRECTOR_RULE_ENGINE_VERSION = "1.0"


class DirectorPlanStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    APPLIED = "applied"
    OUTDATED = "outdated"


class DirectorSourceType(StrEnum):
    IDEA = "idea"
    SCRIPT = "script"
    TRANSCRIPT = "transcript"
    TRANSLATION = "translation"
    SCENES = "scenes"


@dataclass(slots=True)
class DirectorRequest:
    project_id: str
    workflow: str
    content_source_type: str = DirectorSourceType.IDEA.value
    content_source_id: str = ""
    content_text: str = ""
    language: str = "en"
    platform: str = "generic"
    target_duration_ms: int = 60_000
    audience: str = "general"
    style: str = "modern"
    pace: str = "balanced"
    tone: str = "neutral"
    aspect_ratio_mode: str = "auto"
    voice_preference: str = ""
    subtitle_preference: str = ""
    visual_preference: str = ""
    music_preference: str = ""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.request_id

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("Director request requires a project.")
        if self.workflow not in WORKFLOW_PROFILES:
            raise ValueError("Unsupported Director workflow.")
        if self.content_source_type not in {item.value for item in DirectorSourceType}:
            raise ValueError("Unsupported Director content source.")
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported Director language.")
        if self.platform not in PLATFORM_PROFILES:
            raise ValueError("Unsupported Director platform.")
        if self.target_duration_ms <= 0:
            raise ValueError("Target duration must be greater than zero.")
        if self.audience not in SUPPORTED_AUDIENCES:
            raise ValueError("Unsupported Director audience.")
        if self.style not in SUPPORTED_STYLES:
            raise ValueError("Unsupported Director style.")
        if self.pace not in SUPPORTED_PACES:
            raise ValueError("Unsupported Director pace.")
        if self.tone not in SUPPORTED_TONES:
            raise ValueError("Unsupported Director tone.")
        if self.aspect_ratio_mode not in {"auto", *SUPPORTED_ASPECT_RATIOS}:
            raise ValueError("Unsupported Director aspect-ratio mode.")
        if self.content_source_type == DirectorSourceType.IDEA.value and not self.content_text.strip():
            raise ValueError("Describe the video idea first.")
        if self.content_source_type != DirectorSourceType.IDEA.value and not self.content_source_id:
            raise ValueError("Choose a Director source.")


@dataclass(slots=True)
class DirectorPlan:
    project_id: str
    request_id: str
    workflow: str
    platform: str
    language: str
    target_duration_ms: int
    aspect_ratio: str
    source_type: str
    source_id: str = ""
    status: str | DirectorPlanStatus = DirectorPlanStatus.REVIEW
    version: int = 1
    source_fingerprint: str = ""
    recommendations: list[DirectorRecommendation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = DIRECTOR_SCHEMA_VERSION
    rule_engine_version: str = DIRECTOR_RULE_ENGINE_VERSION
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def id(self) -> str:
        return self.plan_id

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.project_id or not self.plan_id:
            raise ValueError("Director plan identity is required.")
        if self.workflow not in WORKFLOW_PROFILES:
            raise ValueError("Unsupported Director workflow.")
        if self.platform not in PLATFORM_PROFILES:
            raise ValueError("Unsupported Director platform.")
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported Director language.")
        if self.target_duration_ms <= 0:
            raise ValueError("Director target duration must be greater than zero.")
        if self.aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            raise ValueError("Unsupported Director aspect ratio.")
        if self.status_code not in {item.value for item in DirectorPlanStatus}:
            raise ValueError("Unsupported Director status.")
        if self.schema_version != DIRECTOR_SCHEMA_VERSION:
            raise ValueError("Unsupported Director plan schema version.")

    def recommendation(self, category: str) -> DirectorRecommendation | None:
        return next((item for item in self.recommendations if item.category == category), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "requestId": self.request_id,
            "workflow": self.workflow,
            "platform": self.platform,
            "language": self.language,
            "targetDurationMs": self.target_duration_ms,
            "aspectRatio": self.aspect_ratio,
            "sourceType": self.source_type,
            "sourceId": self.source_id,
            "status": self.status_code,
            "version": self.version,
            "schemaVersion": self.schema_version,
            "ruleEngineVersion": self.rule_engine_version,
            "sourceFingerprint": self.source_fingerprint,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "metadata": dict(self.metadata),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "DirectorPlan":
        def decode(key: str, default):
            try:
                value = json.loads(record[key] or "")
                return value
            except Exception:
                return default
        recs = [DirectorRecommendation.from_dict(item) for item in decode("recommendations_json", []) if isinstance(item, dict)]
        return cls(
            plan_id=str(record["id"]),
            project_id=str(record["project_id"]),
            request_id=str(record["request_id"]),
            workflow=str(record["workflow"]),
            platform=str(record["platform"]),
            language=str(record["language"]),
            target_duration_ms=int(record["target_duration_ms"]),
            aspect_ratio=str(record["aspect_ratio"]),
            source_type=str(record["source_type"]),
            source_id=str(record["source_id"] or ""),
            status=str(record["status"]),
            version=int(record["plan_version"]),
            schema_version=int(record["schema_version"]),
            rule_engine_version=str(record["rule_engine_version"]),
            source_fingerprint=str(record["source_fingerprint"] or ""),
            recommendations=recs,
            metadata=dict(decode("metadata_json", {})),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )

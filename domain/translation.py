from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.language import supported_language_codes
from domain.project import utc_now_iso


class TranslationSourceType(StrEnum):
    TRANSCRIPT = "transcript"
    SCRIPT = "script"
    MANUAL_TEXT = "manual_text"


class TranslationStatus(StrEnum):
    DRAFT = "draft"
    TRANSLATING = "translating"
    REVIEW = "review"
    APPROVED = "approved"
    OUTDATED = "outdated"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Translation:
    project_id: str
    source_type: str | TranslationSourceType
    source_id: str
    source_language: str
    target_language: str
    engine_id: str
    model_id: str = ""
    status: str | TranslationStatus = TranslationStatus.DRAFT
    source_fingerprint: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    translation_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.translation_id

    @property
    def source_type_code(self) -> str:
        return self.source_type.value if isinstance(self.source_type, StrEnum) else str(self.source_type)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.translation_id or not self.project_id:
            raise ValueError("Translation identity and project are required.")
        if self.source_type_code not in {item.value for item in TranslationSourceType}:
            raise ValueError("Unsupported translation source type.")
        if not self.source_id:
            raise ValueError("Translation source ID is required.")
        if self.source_language not in supported_language_codes() or self.target_language not in supported_language_codes():
            raise ValueError("Unsupported translation language.")
        if self.source_language == self.target_language:
            raise ValueError("Source and target languages must differ.")
        if not self.engine_id:
            raise ValueError("Translation engine is required.")
        if self.status_code not in {item.value for item in TranslationStatus}:
            raise ValueError("Unsupported translation status.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.translation_id,
            "project_id": self.project_id,
            "source_type": self.source_type_code,
            "source_id": self.source_id,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "engine_id": self.engine_id,
            "model_id": self.model_id,
            "status": self.status_code,
            "source_fingerprint": self.source_fingerprint,
            "settings": dict(self.settings),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Translation":
        def decode(key: str) -> dict[str, Any]:
            try:
                value = json.loads(record[key] or "{}")
                return value if isinstance(value, dict) else {}
            except (TypeError, json.JSONDecodeError):
                return {}

        return cls(
            translation_id=str(record["id"]),
            project_id=str(record["project_id"]),
            source_type=str(record["source_type"]),
            source_id=str(record["source_id"]),
            source_language=str(record["source_language"]),
            target_language=str(record["target_language"]),
            engine_id=str(record["engine_id"]),
            model_id=str(record["model_id"] or ""),
            status=str(record["status"]),
            source_fingerprint=str(record["source_fingerprint"] or ""),
            settings=decode("settings_json"),
            metadata=decode("metadata_json"),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )

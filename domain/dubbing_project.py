from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from domain.project import SUPPORTED_LANGUAGES, utc_now_iso


class DubbingProjectStatus(StrEnum):
    SETUP = "setup"
    TRANSCRIBING = "transcribing"
    TRANSCRIPT_REVIEW = "transcript_review"
    TRANSLATING = "translating"
    TRANSLATION_REVIEW = "translation_review"
    GENERATING_VOICE = "generating_voice"
    ALIGNING = "aligning"
    REVIEW = "review"
    READY = "ready"
    OUTDATED = "outdated"
    FAILED = "failed"


@dataclass(slots=True)
class DubbingProject:
    project_id: str
    source_media_id: str = ""
    source_language: str = "auto"
    target_language: str = "km"
    transcript_id: str = ""
    translation_id: str = ""
    target_voice_id: str = ""
    subtitle_track_id: str = ""
    status: str | DubbingProjectStatus = DubbingProjectStatus.SETUP
    settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("Project ID is required.")
        if self.source_language not in {*SUPPORTED_LANGUAGES, "auto"}:
            raise ValueError("Unsupported source language.")
        if self.target_language not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported target language.")
        if self.source_language != "auto" and self.source_language == self.target_language:
            raise ValueError("Source and target languages must differ.")
        if self.status_code not in {item.value for item in DubbingProjectStatus}:
            raise ValueError("Unsupported dubbing project status.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "projectId": self.project_id,
            "sourceMediaId": self.source_media_id,
            "sourceLanguage": self.source_language,
            "targetLanguage": self.target_language,
            "transcriptId": self.transcript_id,
            "translationId": self.translation_id,
            "targetVoiceId": self.target_voice_id,
            "subtitleTrackId": self.subtitle_track_id,
            "status": self.status_code,
            "settings": dict(self.settings),
            "metadata": dict(self.metadata),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "DubbingProject":
        def load(name: str) -> dict[str, Any]:
            try:
                value = json.loads(str(row[name] or "{}"))
                return value if isinstance(value, dict) else {}
            except (TypeError, json.JSONDecodeError):
                return {}

        return cls(
            project_id=str(row["project_id"]),
            source_media_id=str(row["source_media_id"] or ""),
            source_language=str(row["source_language"] or "auto"),
            target_language=str(row["target_language"] or "km"),
            transcript_id=str(row["transcript_id"] or ""),
            translation_id=str(row["translation_id"] or ""),
            target_voice_id=str(row["target_voice_id"] or ""),
            subtitle_track_id=str(row["subtitle_track_id"] or ""),
            status=str(row["status"] or "setup"),
            settings=load("settings_json"),
            metadata=load("metadata_json"),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

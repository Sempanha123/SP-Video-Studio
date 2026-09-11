from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.language import supported_language_codes
from domain.project import utc_now_iso


class TranscriptStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OUTDATED = "outdated"


@dataclass(slots=True)
class Transcript:
    project_id: str
    media_id: str
    engine: str
    model_id: str
    language_mode: str = "auto"
    detected_language: str | None = None
    language_probability: float | None = None
    device: str = "cpu"
    compute_type: str = "int8"
    duration_ms: int = 0
    status: str | TranscriptStatus = TranscriptStatus.PROCESSING
    source_fingerprint: str = ""
    model_version: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    active: bool = False
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    transcript_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.transcript_id

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, TranscriptStatus) else str(self.status)

    def validate(self) -> None:
        if not self.transcript_id or not self.project_id or not self.media_id:
            raise ValueError("Transcript identity and ownership are required.")
        if self.language_mode != "auto" and self.language_mode not in supported_language_codes():
            raise ValueError("Unsupported transcript language mode.")
        if self.detected_language and self.detected_language not in supported_language_codes(enabled_only=False):
            # Whisper can detect a language not yet enabled by the application catalog.
            self.metadata.setdefault("unregisteredDetectedLanguage", self.detected_language)
        if self.status_code not in {item.value for item in TranscriptStatus}:
            raise ValueError("Unsupported transcript status.")
        if self.duration_ms < 0:
            raise ValueError("Transcript duration cannot be negative.")
        if self.language_probability is not None and not 0 <= self.language_probability <= 1:
            raise ValueError("Language probability must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.transcript_id,
            "project_id": self.project_id,
            "media_id": self.media_id,
            "engine": self.engine,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "language_mode": self.language_mode,
            "detected_language": self.detected_language,
            "language_probability": self.language_probability,
            "device": self.device,
            "compute_type": self.compute_type,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status_code,
            "source_fingerprint": self.source_fingerprint,
            "settings": dict(self.settings),
            "metadata": dict(self.metadata),
            "active": self.active,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Transcript":
        def decode(key: str) -> dict[str, Any]:
            try:
                value = json.loads(record[key] or "{}")
                return value if isinstance(value, dict) else {}
            except (TypeError, json.JSONDecodeError):
                return {}

        return cls(
            transcript_id=str(record["id"]),
            project_id=str(record["project_id"]),
            media_id=str(record["media_id"]),
            engine=str(record["engine"]),
            model_id=str(record["model_id"]),
            model_version=str(record["model_version"] or ""),
            language_mode=str(record["language_mode"]),
            detected_language=str(record["detected_language"]) if record["detected_language"] else None,
            language_probability=(float(record["language_probability"]) if record["language_probability"] is not None else None),
            device=str(record["device"]),
            compute_type=str(record["compute_type"]),
            duration_ms=int(record["duration_ms"] or 0),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
            status=str(record["status"]),
            source_fingerprint=str(record["source_fingerprint"] or ""),
            settings=decode("settings_json"), metadata=decode("metadata_json"), active=bool(record["active"]),
        )


def source_fingerprint(media_id: str, file_size: int, mtime_ns: int) -> str:
    payload = f"{media_id}\0{int(file_size)}\0{int(mtime_ns)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

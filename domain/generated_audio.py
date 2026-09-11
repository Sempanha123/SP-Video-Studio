from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class GeneratedAudioStatus(StrEnum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class GeneratedAudio:
    project_id: str
    engine: str
    model_id: str
    language: str
    voice_mode: str
    text_hash: str
    file_path: str
    script_id: str | None = None
    section_id: str | None = None
    duration_ms: int = 0
    sample_rate: int = 0
    channels: int = 1
    status: str | GeneratedAudioStatus = GeneratedAudioStatus.COMPLETED
    active: bool = False
    generated_audio_id: str = field(default_factory=lambda: str(uuid4()))
    voice_config: dict[str, Any] = field(default_factory=dict)
    generation_settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    @property
    def id(self) -> str:
        return self.generated_audio_id

    @property
    def status_code(self) -> str:
        return str(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.generated_audio_id,
            "projectId": self.project_id,
            "scriptId": self.script_id or "",
            "sectionId": self.section_id or "",
            "engine": self.engine,
            "modelId": self.model_id,
            "language": self.language,
            "voiceMode": self.voice_mode,
            "voiceConfig": dict(self.voice_config),
            "textHash": self.text_hash,
            "filePath": self.file_path,
            "durationMs": self.duration_ms,
            "sampleRate": self.sample_rate,
            "channels": self.channels,
            "createdAt": self.created_at,
            "generationSettings": dict(self.generation_settings),
            "status": self.status_code,
            "active": self.active,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "GeneratedAudio":
        def load_json(name: str) -> dict[str, Any]:
            raw = record[name] if name in record.keys() else None
            try:
                value = json.loads(raw or "{}")
            except (TypeError, json.JSONDecodeError):
                value = {}
            return dict(value) if isinstance(value, dict) else {}

        return cls(
            generated_audio_id=str(record["id"]),
            project_id=str(record["project_id"]),
            script_id=str(record["script_id"]) if record["script_id"] else None,
            section_id=str(record["section_id"]) if record["section_id"] else None,
            engine=str(record["engine"]),
            model_id=str(record["model_id"]),
            language=str(record["language"]),
            voice_mode=str(record["voice_mode"]),
            voice_config=load_json("voice_config_json"),
            text_hash=str(record["text_hash"]),
            file_path=str(record["file_path"]),
            duration_ms=int(record["duration_ms"] or 0),
            sample_rate=int(record["sample_rate"] or 0),
            channels=int(record["channels"] or 1),
            created_at=str(record["created_at"]),
            generation_settings=load_json("generation_settings_json"),
            status=str(record["status"]),
            active=bool(record["active"]),
            metadata=load_json("metadata_json"),
        )

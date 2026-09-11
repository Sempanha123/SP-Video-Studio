from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import SUPPORTED_LANGUAGES, utc_now_iso


class VoiceType(StrEnum):
    PRESET = "preset"
    DESIGNED = "designed"
    REFERENCE = "reference"


@dataclass(slots=True)
class VoiceProfile:
    name: str
    voice_type: str | VoiceType
    language: str
    category: str
    engine_id: str = "voxcpm2"
    voice_description: str = ""
    style_tags: list[str] = field(default_factory=list)
    description: str = ""
    reference_audio_path: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    favorite: bool = False
    last_used_at: str | None = None
    usage_count: int = 0
    validated: bool = False
    duration_ms: int = 0
    is_builtin: bool = False
    voice_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def id(self) -> str:
        return self.voice_id

    @property
    def type_code(self) -> str:
        return self.voice_type.value if isinstance(self.voice_type, StrEnum) else str(self.voice_type)

    def validate(self) -> None:
        if not self.voice_id.strip():
            raise ValueError("Voice ID is required.")
        if not self.name.strip():
            raise ValueError("Voice name is required.")
        if self.type_code not in {item.value for item in VoiceType}:
            raise ValueError("Unsupported voice type.")
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError("Choose English or Khmer.")
        if not self.category.strip():
            raise ValueError("Voice category is required.")
        if self.type_code == VoiceType.DESIGNED.value and not self.voice_description.strip():
            raise ValueError("Voice description is required for a designed voice.")
        if self.type_code == VoiceType.REFERENCE.value and not self.reference_audio_path:
            raise ValueError("Reference audio is required for a reference voice.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.voice_id,
            "name": self.name,
            "voiceType": self.type_code,
            "language": self.language,
            "languageName": "Khmer" if self.language == "km" else "English",
            "category": self.category,
            "engineId": self.engine_id,
            "engineName": "VoxCPM2" if self.engine_id == "voxcpm2" else self.engine_id,
            "voiceDescription": self.voice_description,
            "styleTags": list(self.style_tags),
            "description": self.description,
            "referenceAudioPath": self.reference_audio_path,
            "settings": dict(self.settings),
            "notes": self.notes,
            "favorite": bool(self.favorite),
            "lastUsedAt": self.last_used_at or "",
            "usageCount": int(self.usage_count),
            "validated": bool(self.validated),
            "durationMs": int(self.duration_ms),
            "isBuiltin": bool(self.is_builtin),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "VoiceProfile":
        def parse_json(key: str, default):
            raw = record[key] if key in record.keys() else None
            if not raw:
                return default
            try:
                return json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                return default

        return cls(
            voice_id=str(record["id"]),
            name=str(record["name"]),
            voice_type=str(record["voice_type"]),
            language=str(record["language"]),
            category=str(record["category"]),
            engine_id=str(record["engine_id"]),
            voice_description=str(record["voice_description"] or ""),
            style_tags=[str(v) for v in parse_json("style_tags_json", [])],
            description=str(record["description"] or ""),
            reference_audio_path=str(record["reference_audio_path"] or ""),
            settings=dict(parse_json("settings_json", {})),
            notes=str(record["notes"] or ""),
            validated=bool(record["validated"]),
            duration_ms=int(record["duration_ms"] or 0),
            is_builtin=False,
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )

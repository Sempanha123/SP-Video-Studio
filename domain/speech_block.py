from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.language import supported_language_codes
from domain.project import utc_now_iso
from domain.phase22_errors import SpeechBlockInvalid


class SpeechSourceType(StrEnum):
    TTS = "tts"
    SOURCE_AUDIO = "source_audio"
    IMPORTED_AUDIO = "imported_audio"
    NONE = "none"


@dataclass(slots=True)
class SpeechBlock:
    script_section_id: str
    order: int
    text: str
    language: str = "en"
    speaker_id: str = ""
    voice_override_id: str = ""
    speech_source_type: str | SpeechSourceType = SpeechSourceType.TTS
    pause_before_ms: int = 0
    pause_after_ms: int = 180
    scene_id: str = ""
    start_offset_ms: int | None = None
    audio_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    block_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.block_id

    @property
    def source_type_code(self) -> str:
        return self.speech_source_type.value if isinstance(self.speech_source_type, StrEnum) else str(self.speech_source_type)

    def validate(self) -> None:
        if not self.block_id or not self.script_section_id:
            raise SpeechBlockInvalid("Speech block identity and script section are required.")
        if self.order < 0:
            raise SpeechBlockInvalid("Speech block order cannot be negative.")
        if self.language not in supported_language_codes():
            raise SpeechBlockInvalid("Unsupported speech-block language.")
        if self.source_type_code not in {item.value for item in SpeechSourceType}:
            raise SpeechBlockInvalid("Unsupported speech source type.")
        if self.pause_before_ms < 0 or self.pause_after_ms < 0:
            raise SpeechBlockInvalid("Speech pauses cannot be negative.")
        if self.start_offset_ms is not None and self.start_offset_ms < 0:
            raise SpeechBlockInvalid("Speech block start cannot be negative.")
        if self.source_type_code == SpeechSourceType.TTS.value and not self.text.strip():
            raise SpeechBlockInvalid("TTS speech text is required.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "id": self.id, "scriptSectionId": self.script_section_id, "order": self.order,
            "speakerId": self.speaker_id, "text": self.text, "language": self.language,
            "voiceOverrideId": self.voice_override_id, "speechSourceType": self.source_type_code,
            "pauseBeforeMs": self.pause_before_ms, "pauseAfterMs": self.pause_after_ms,
            "sceneId": self.scene_id, "startOffsetMs": self.start_offset_ms, "audioId": self.audio_id,
            "metadata": dict(self.metadata), "createdAt": self.created_at, "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "SpeechBlock":
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except Exception:
            metadata = {}
        return cls(
            block_id=str(row["id"]), script_section_id=str(row["script_section_id"]), order=int(row["block_order"]),
            speaker_id=str(row["speaker_id"] or ""), text=str(row["text"] or ""), language=str(row["language"]),
            voice_override_id=str(row["voice_override_id"] or ""), speech_source_type=str(row["speech_source_type"]),
            pause_before_ms=int(row["pause_before_ms"] or 0), pause_after_ms=int(row["pause_after_ms"] or 0),
            scene_id=str(row["scene_id"] or ""), start_offset_ms=(int(row["start_offset_ms"]) if row["start_offset_ms"] is not None else None),
            audio_id=str(row["audio_id"] or ""), metadata=metadata if isinstance(metadata, dict) else {},
            created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
        )

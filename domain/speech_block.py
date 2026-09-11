from __future__ import annotations

import hashlib
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


class SpeechAudioStatus(StrEnum):
    NOT_GENERATED = "not_generated"
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    OUTDATED = "outdated"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpeechTimingStatus(StrEnum):
    NOT_GENERATED = "not_generated"
    FITS = "fits"
    SHORT = "short"
    LONG = "long"
    VERY_LONG = "very_long"
    ADJUSTED = "adjusted"
    NEEDS_REVIEW = "needs_review"


def speech_text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass(slots=True)
class SpeechBlock:
    script_section_id: str
    order: int
    text: str
    project_id: str = ""
    language: str = "en"
    speaker_id: str = ""
    voice_override_id: str = ""
    speech_source_type: str | SpeechSourceType = SpeechSourceType.TTS
    pause_before_ms: int = 0
    pause_after_ms: int = 180
    scene_id: str = ""
    # Legacy Phase 22 fields stay authoritative-compatible. New code mirrors the
    # absolute timeline/take values into these where possible.
    start_offset_ms: int | None = None
    audio_id: str = ""
    timeline_start_ms: int | None = None
    timeline_end_ms: int | None = None
    active_generated_audio_id: str = ""
    text_hash: str = ""
    audio_status: str | SpeechAudioStatus = SpeechAudioStatus.NOT_GENERATED
    timing_status: str | SpeechTimingStatus = SpeechTimingStatus.NOT_GENERATED
    user_modified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    block_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.text_hash:
            self.text_hash = speech_text_hash(self.text)
        if not self.active_generated_audio_id and self.audio_id:
            self.active_generated_audio_id = self.audio_id
        if not self.audio_id and self.active_generated_audio_id:
            self.audio_id = self.active_generated_audio_id
        if self.timeline_start_ms is None and self.start_offset_ms is not None and not self.scene_id:
            self.timeline_start_ms = int(self.start_offset_ms)

    @property
    def id(self) -> str:
        return self.block_id

    @property
    def source_type_code(self) -> str:
        return self.speech_source_type.value if isinstance(self.speech_source_type, StrEnum) else str(self.speech_source_type)

    @property
    def audio_status_code(self) -> str:
        return self.audio_status.value if isinstance(self.audio_status, StrEnum) else str(self.audio_status)

    @property
    def timing_status_code(self) -> str:
        return self.timing_status.value if isinstance(self.timing_status, StrEnum) else str(self.timing_status)

    @property
    def allocated_duration_ms(self) -> int:
        if self.timeline_start_ms is None or self.timeline_end_ms is None:
            return 0
        return max(0, int(self.timeline_end_ms) - int(self.timeline_start_ms))

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
        if self.timeline_start_ms is not None and self.timeline_start_ms < 0:
            raise SpeechBlockInvalid("Speech block timeline start cannot be negative.")
        if self.timeline_end_ms is not None:
            if self.timeline_end_ms < 0:
                raise SpeechBlockInvalid("Speech block timeline end cannot be negative.")
            if self.timeline_start_ms is None or self.timeline_end_ms <= self.timeline_start_ms:
                raise SpeechBlockInvalid("Speech block end must be after its start.")
        if self.audio_status_code not in {item.value for item in SpeechAudioStatus}:
            raise SpeechBlockInvalid("Unsupported speech audio status.")
        if self.timing_status_code not in {item.value for item in SpeechTimingStatus}:
            raise SpeechBlockInvalid("Unsupported speech timing status.")
        if self.source_type_code == SpeechSourceType.TTS.value and not self.text.strip():
            raise SpeechBlockInvalid("TTS speech text is required.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "projectId": self.project_id,
            "scriptSectionId": self.script_section_id,
            "order": self.order,
            "speakerId": self.speaker_id,
            "text": self.text,
            "language": self.language,
            "voiceOverrideId": self.voice_override_id,
            "speechSourceType": self.source_type_code,
            "pauseBeforeMs": self.pause_before_ms,
            "pauseAfterMs": self.pause_after_ms,
            "sceneId": self.scene_id,
            "startOffsetMs": self.start_offset_ms,
            "audioId": self.audio_id,
            "timelineStartMs": self.timeline_start_ms,
            "timelineEndMs": self.timeline_end_ms,
            "activeGeneratedAudioId": self.active_generated_audio_id,
            "textHash": self.text_hash,
            "audioStatus": self.audio_status_code,
            "timingStatus": self.timing_status_code,
            "userModified": self.user_modified,
            "metadata": dict(self.metadata),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "SpeechBlock":
        keys = set(row.keys())
        def get(name: str, default=None):
            return row[name] if name in keys else default
        try:
            metadata = json.loads(str(get("metadata_json", "{}") or "{}"))
        except Exception:
            metadata = {}
        audio_id = str(get("audio_id", "") or "")
        active = str(get("active_generated_audio_id", "") or "") or audio_id
        text = str(get("text", "") or "")
        return cls(
            block_id=str(get("id", "")),
            project_id=str(get("project_id", "") or ""),
            script_section_id=str(get("script_section_id", "")),
            order=int(get("block_order", 0) or 0),
            speaker_id=str(get("speaker_id", "") or ""),
            text=text,
            language=str(get("language", "en") or "en"),
            voice_override_id=str(get("voice_override_id", "") or ""),
            speech_source_type=str(get("speech_source_type", "tts") or "tts"),
            pause_before_ms=int(get("pause_before_ms", 0) or 0),
            pause_after_ms=int(get("pause_after_ms", 0) or 0),
            scene_id=str(get("scene_id", "") or ""),
            start_offset_ms=(int(get("start_offset_ms")) if get("start_offset_ms") is not None else None),
            audio_id=audio_id,
            timeline_start_ms=(int(get("timeline_start_ms")) if get("timeline_start_ms") is not None else None),
            timeline_end_ms=(int(get("timeline_end_ms")) if get("timeline_end_ms") is not None else None),
            active_generated_audio_id=active,
            text_hash=str(get("text_hash", "") or speech_text_hash(text)),
            audio_status=str(get("audio_status", "ready" if active else "not_generated") or "not_generated"),
            timing_status=str(get("timing_status", "not_generated") or "not_generated"),
            user_modified=bool(get("user_modified", 0)),
            metadata=metadata if isinstance(metadata, dict) else {},
            created_at=str(get("created_at", utc_now_iso())),
            updated_at=str(get("updated_at", utc_now_iso())),
        )

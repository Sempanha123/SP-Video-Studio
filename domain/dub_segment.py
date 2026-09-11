from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class DubTimingMode(StrEnum):
    NATURAL = "natural"
    FIT_SEGMENT = "fit_segment"
    EXTEND_SEGMENT = "extend_segment"


class DubTimingStatus(StrEnum):
    NOT_GENERATED = "not_generated"
    FITS = "fits"
    SHORT = "short"
    LONG = "long"
    VERY_LONG = "very_long"
    ADJUSTED = "adjusted"
    NEEDS_REVIEW = "needs_review"


class DubAudioStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    OUTDATED = "outdated"
    FAILED = "failed"
    CANCELLED = "cancelled"


def dub_text_hash(text: str, voice_config: object, model_version: str, settings: object) -> str:
    payload = {
        "text": text.strip(),
        "voice": voice_config,
        "modelVersion": model_version or "",
        "settings": settings,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class DubSegment:
    project_id: str
    source_transcript_segment_id: str
    translation_segment_id: str
    order: int
    source_start_ms: int
    source_end_ms: int
    target_text: str
    voice_id: str = ""
    generated_audio_id: str = ""
    generated_audio_path: str = ""
    generated_duration_ms: int = 0
    timing_mode: str | DubTimingMode = DubTimingMode.NATURAL
    timing_status: str | DubTimingStatus = DubTimingStatus.NOT_GENERATED
    audio_status: str | DubAudioStatus = DubAudioStatus.PENDING
    start_offset_ms: int = 0
    stretch_factor: float = 1.0
    locked: bool = False
    user_modified: bool = False
    speaker_label: str = ""
    source_hash: str = ""
    generation_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    segment_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.segment_id

    @property
    def target_duration_ms(self) -> int:
        return max(0, self.source_end_ms - self.source_start_ms)

    @property
    def effective_start_ms(self) -> int:
        return max(0, self.source_start_ms + self.start_offset_ms)

    @property
    def effective_duration_ms(self) -> int:
        if self.generated_duration_ms <= 0:
            return 0
        factor = self.stretch_factor if self.stretch_factor > 0 else 1.0
        return max(1, round(self.generated_duration_ms / factor))

    @property
    def effective_end_ms(self) -> int:
        return self.effective_start_ms + self.effective_duration_ms

    @property
    def timing_mode_code(self) -> str:
        return self.timing_mode.value if isinstance(self.timing_mode, StrEnum) else str(self.timing_mode)

    @property
    def timing_status_code(self) -> str:
        return self.timing_status.value if isinstance(self.timing_status, StrEnum) else str(self.timing_status)

    @property
    def audio_status_code(self) -> str:
        return self.audio_status.value if isinstance(self.audio_status, StrEnum) else str(self.audio_status)

    def validate(self) -> None:
        if not self.segment_id or not self.project_id:
            raise ValueError("Dub segment identity is required.")
        if self.order < 0:
            raise ValueError("Dub segment order cannot be negative.")
        if self.source_start_ms < 0 or self.source_end_ms < self.source_start_ms:
            raise ValueError("Dub segment source timing is invalid.")
        if self.effective_start_ms < 0:
            raise ValueError("Dub segment cannot begin before zero.")
        if self.stretch_factor <= 0:
            raise ValueError("Stretch factor must be positive.")
        if self.timing_mode_code not in {item.value for item in DubTimingMode}:
            raise ValueError("Unsupported dub timing mode.")
        if self.timing_status_code not in {item.value for item in DubTimingStatus}:
            raise ValueError("Unsupported dub timing status.")
        if self.audio_status_code not in {item.value for item in DubAudioStatus}:
            raise ValueError("Unsupported dub audio status.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "projectId": self.project_id,
            "sourceTranscriptSegmentId": self.source_transcript_segment_id,
            "translationSegmentId": self.translation_segment_id, "order": self.order,
            "sourceStartMs": self.source_start_ms, "sourceEndMs": self.source_end_ms,
            "targetDurationMs": self.target_duration_ms, "targetText": self.target_text,
            "voiceId": self.voice_id, "generatedAudioId": self.generated_audio_id,
            "generatedAudioPath": self.generated_audio_path,
            "generatedDurationMs": self.generated_duration_ms, "timingMode": self.timing_mode_code,
            "timingStatus": self.timing_status_code, "audioStatus": self.audio_status_code,
            "startOffsetMs": self.start_offset_ms, "stretchFactor": self.stretch_factor,
            "locked": self.locked, "userModified": self.user_modified, "speakerLabel": self.speaker_label,
            "sourceHash": self.source_hash, "generationHash": self.generation_hash,
            "metadata": dict(self.metadata), "createdAt": self.created_at, "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "DubSegment":
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            segment_id=str(row["id"]), project_id=str(row["project_id"]),
            source_transcript_segment_id=str(row["source_transcript_segment_id"] or ""),
            translation_segment_id=str(row["translation_segment_id"] or ""), order=int(row["segment_order"]),
            source_start_ms=int(row["source_start_ms"]), source_end_ms=int(row["source_end_ms"]),
            target_text=str(row["target_text"] or ""), voice_id=str(row["voice_id"] or ""),
            generated_audio_id=str(row["generated_audio_id"] or ""),
            generated_audio_path=str(row["generated_audio_path"] or ""),
            generated_duration_ms=int(row["generated_duration_ms"] or 0),
            timing_mode=str(row["timing_mode"]), timing_status=str(row["timing_status"]),
            audio_status=str(row["audio_status"]), start_offset_ms=int(row["start_offset_ms"] or 0),
            stretch_factor=float(row["stretch_factor"] or 1.0), locked=bool(row["locked"]),
            user_modified=bool(row["user_modified"]), speaker_label=str(row["speaker_label"] or ""),
            source_hash=str(row["source_hash"] or ""), generation_hash=str(row["generation_hash"] or ""),
            metadata=metadata if isinstance(metadata, dict) else {}, created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

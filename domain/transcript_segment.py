from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso
from domain.transcript_word import TranscriptWord


@dataclass(slots=True)
class TranscriptSegment:
    transcript_id: str
    order: int
    start_ms: int
    end_ms: int
    text: str
    original_text: str = ""
    confidence: float | None = None
    no_speech_probability: float | None = None
    temperature: float | None = None
    edited: bool = False
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    segment_id: str = field(default_factory=lambda: str(uuid4()))
    words: list[TranscriptWord] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.segment_id

    def __post_init__(self) -> None:
        if not self.original_text:
            self.original_text = self.text

    def validate(self) -> None:
        if not self.segment_id or not self.transcript_id:
            raise ValueError("Transcript segment identity is required.")
        if self.order < 0:
            raise ValueError("Transcript segment order cannot be negative.")
        if self.start_ms < 0 or self.end_ms < self.start_ms:
            raise ValueError("Transcript segment timestamps are invalid.")
        for word in self.words:
            word.validate()
            if word.start_ms < self.start_ms - 100 or word.end_ms > self.end_ms + 100:
                raise ValueError("Transcript word timestamps fall outside the segment range.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.segment_id,
            "transcript_id": self.transcript_id,
            "order": self.order,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text": self.text,
            "original_text": self.original_text,
            "confidence": self.confidence,
            "no_speech_probability": self.no_speech_probability,
            "temperature": self.temperature,
            "edited": self.edited,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
            "words": [word.to_dict() for word in self.words],
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "TranscriptSegment":
        try:
            metadata = json.loads(record["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            segment_id=str(record["id"]),
            transcript_id=str(record["transcript_id"]),
            order=int(record["segment_order"]),
            start_ms=int(record["start_ms"]),
            end_ms=int(record["end_ms"]),
            text=str(record["text"] or ""),
            original_text=str(record["original_text"] or ""),
            confidence=float(record["confidence"]) if record["confidence"] is not None else None,
            no_speech_probability=(
                float(record["no_speech_probability"]) if record["no_speech_probability"] is not None else None
            ),
            temperature=float(record["temperature"]) if record["temperature"] is not None else None,
            edited=bool(record["edited"]),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
            metadata=metadata if isinstance(metadata, dict) else {},
        )

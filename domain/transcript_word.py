from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4


@dataclass(slots=True)
class TranscriptWord:
    segment_id: str
    order: int
    start_ms: int
    end_ms: int
    text: str
    probability: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    word_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.word_id

    def validate(self) -> None:
        if not self.word_id or not self.segment_id:
            raise ValueError("Transcript word identity is required.")
        if self.order < 0:
            raise ValueError("Transcript word order cannot be negative.")
        if self.start_ms < 0 or self.end_ms < self.start_ms:
            raise ValueError("Transcript word timestamps are invalid.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.word_id,
            "segment_id": self.segment_id,
            "order": self.order,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text": self.text,
            "probability": self.probability,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "TranscriptWord":
        try:
            metadata = json.loads(record["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            word_id=str(record["id"]),
            segment_id=str(record["segment_id"]),
            order=int(record["word_order"]),
            start_ms=int(record["start_ms"]),
            end_ms=int(record["end_ms"]),
            text=str(record["text"] or ""),
            probability=float(record["probability"]) if record["probability"] is not None else None,
            metadata=metadata if isinstance(metadata, dict) else {},
        )

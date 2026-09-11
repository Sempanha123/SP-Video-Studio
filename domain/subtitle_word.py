from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4


@dataclass(slots=True)
class SubtitleWord:
    cue_id: str
    order: int
    text: str
    start_ms: int
    end_ms: int
    probability: float | None = None
    highlight_group: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    word_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.word_id

    def validate(self) -> None:
        if not self.word_id or not self.cue_id:
            raise ValueError("Subtitle word identity is required.")
        if self.order < 0 or self.start_ms < 0 or self.end_ms < self.start_ms:
            raise ValueError("Subtitle word timing is invalid.")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.word_id, "cue_id": self.cue_id, "order": self.order, "text": self.text,
                "start_ms": self.start_ms, "end_ms": self.end_ms, "probability": self.probability,
                "highlight_group": self.highlight_group, "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "SubtitleWord":
        try:
            metadata = json.loads(record["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(word_id=str(record["id"]), cue_id=str(record["cue_id"]), order=int(record["word_order"]),
                   text=str(record["text"] or ""), start_ms=int(record["start_ms"]), end_ms=int(record["end_ms"]),
                   probability=float(record["probability"]) if record["probability"] is not None else None,
                   highlight_group=int(record["highlight_group"]) if record["highlight_group"] is not None else None,
                   metadata=metadata if isinstance(metadata, dict) else {})

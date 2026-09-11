from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4


@dataclass(slots=True)
class ShortSegment:
    candidate_id: str
    order: int
    source_start_ms: int
    source_end_ms: int
    source_entity_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    segment_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.segment_id

    @property
    def duration_ms(self) -> int:
        return max(0, int(self.source_end_ms) - int(self.source_start_ms))

    def validate(self) -> None:
        if not self.candidate_id:
            raise ValueError("Short segment requires a candidate.")
        if self.order < 0:
            raise ValueError("Short segment order cannot be negative.")
        if self.source_start_ms < 0 or self.source_end_ms <= self.source_start_ms:
            raise ValueError("Short segment source range is invalid.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "candidateId": self.candidate_id,
            "order": self.order,
            "sourceStartMs": self.source_start_ms,
            "sourceEndMs": self.source_end_ms,
            "durationMs": self.duration_ms,
            "sourceEntityId": self.source_entity_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "ShortSegment":
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except Exception:
            metadata = {}
        return cls(
            segment_id=str(row["id"]),
            candidate_id=str(row["candidate_id"]),
            order=int(row["segment_order"]),
            source_start_ms=int(row["source_start_ms"]),
            source_end_ms=int(row["source_end_ms"]),
            source_entity_id=str(row["source_entity_id"] or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
        )

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso
from domain.subtitle_word import SubtitleWord


@dataclass(slots=True)
class SubtitleCue:
    track_id: str
    order: int
    start_ms: int
    end_ms: int
    text: str = ""
    secondary_text: str = ""
    position: str = "bottom"
    alignment: str = "center"
    style_override: dict[str, Any] = field(default_factory=dict)
    edited: bool = False
    locked: bool = False
    source_segment_id: str = ""
    source_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    cue_id: str = field(default_factory=lambda: str(uuid4()))
    words: list[SubtitleWord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_hash and self.source_segment_id:
            self.source_hash = subtitle_cue_source_hash(self.source_segment_id, self.text, self.start_ms, self.end_ms)

    @property
    def id(self) -> str:
        return self.cue_id

    def validate(self) -> None:
        if not self.cue_id or not self.track_id:
            raise ValueError("Subtitle cue identity is required.")
        if self.order < 0:
            raise ValueError("Subtitle cue order cannot be negative.")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Subtitle cue timing is invalid.")
        if self.position not in {"top", "middle", "bottom"}:
            raise ValueError("Unsupported subtitle position.")
        if self.alignment not in {"left", "center", "right"}:
            raise ValueError("Unsupported subtitle alignment.")
        for word in self.words:
            word.validate()
            if word.start_ms < self.start_ms - 100 or word.end_ms > self.end_ms + 100:
                raise ValueError("Subtitle word timing is outside its cue.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.cue_id, "track_id": self.track_id, "order": self.order, "start_ms": self.start_ms,
            "end_ms": self.end_ms, "text": self.text, "secondary_text": self.secondary_text,
            "position": self.position, "alignment": self.alignment, "style_override": dict(self.style_override),
            "edited": self.edited, "locked": self.locked, "source_segment_id": self.source_segment_id,
            "source_hash": self.source_hash, "metadata": dict(self.metadata), "created_at": self.created_at,
            "updated_at": self.updated_at, "words": [word.to_dict() for word in self.words],
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "SubtitleCue":
        def decode(key: str) -> dict[str, Any]:
            try:
                value = json.loads(record[key] or "{}")
                return value if isinstance(value, dict) else {}
            except (TypeError, json.JSONDecodeError):
                return {}
        return cls(
            cue_id=str(record["id"]), track_id=str(record["track_id"]), order=int(record["cue_order"]),
            start_ms=int(record["start_ms"]), end_ms=int(record["end_ms"]), text=str(record["text"] or ""),
            secondary_text=str(record["secondary_text"] or ""), position=str(record["position"] or "bottom"),
            alignment=str(record["alignment"] or "center"), style_override=decode("style_override_json"),
            edited=bool(record["edited"]), locked=bool(record["locked"]),
            source_segment_id=str(record["source_segment_id"] or ""), source_hash=str(record["source_hash"] or ""),
            metadata=decode("metadata_json"), created_at=str(record["created_at"]), updated_at=str(record["updated_at"]),
        )


def subtitle_cue_source_hash(source_segment_id: str, text: str, start_ms: int | None, end_ms: int | None) -> str:
    return hashlib.sha256(f"{source_segment_id}\0{start_ms}\0{end_ms}\0{text}".encode("utf-8")).hexdigest()

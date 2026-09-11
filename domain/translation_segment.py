from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class TranslationSegmentStatus(StrEnum):
    PENDING = "pending"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    NEEDS_ATTENTION = "needs_attention"
    FAILED = "failed"
    ORPHANED = "orphaned"


@dataclass(slots=True)
class TranslationSegment:
    translation_id: str
    order: int
    source_text: str
    source_segment_id: str = ""
    start_ms: int | None = None
    end_ms: int | None = None
    machine_translation: str = ""
    translated_text: str = ""
    status: str | TranslationSegmentStatus = TranslationSegmentStatus.PENDING
    edited: bool = False
    reviewed: bool = False
    locked: bool = False
    confidence: float | None = None
    notes: str = ""
    source_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    segment_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.source_hash:
            self.source_hash = translation_source_hash(self.source_text, self.start_ms, self.end_ms)

    @property
    def id(self) -> str:
        return self.segment_id

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    @property
    def display_status(self) -> str:
        if self.locked:
            return "Locked"
        if self.reviewed:
            return "Reviewed"
        if self.edited:
            return "Edited"
        return self.status_code.replace("_", " ").title()

    def validate(self) -> None:
        if not self.segment_id or not self.translation_id:
            raise ValueError("Translation segment identity is required.")
        if self.order < 0:
            raise ValueError("Translation segment order cannot be negative.")
        if self.start_ms is not None and self.start_ms < 0:
            raise ValueError("Translation segment start cannot be negative.")
        if self.end_ms is not None:
            if self.start_ms is None or self.end_ms < self.start_ms:
                raise ValueError("Translation segment timestamps are invalid.")
        if self.status_code not in {item.value for item in TranslationSegmentStatus}:
            raise ValueError("Unsupported translation segment status.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.segment_id,
            "translation_id": self.translation_id,
            "source_segment_id": self.source_segment_id,
            "order": self.order,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "source_text": self.source_text,
            "machine_translation": self.machine_translation,
            "translated_text": self.translated_text,
            "status": self.status_code,
            "edited": self.edited,
            "reviewed": self.reviewed,
            "locked": self.locked,
            "confidence": self.confidence,
            "notes": self.notes,
            "source_hash": self.source_hash,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "TranslationSegment":
        try:
            metadata = json.loads(record["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            segment_id=str(record["id"]),
            translation_id=str(record["translation_id"]),
            source_segment_id=str(record["source_segment_id"] or ""),
            order=int(record["segment_order"]),
            start_ms=int(record["start_ms"]) if record["start_ms"] is not None else None,
            end_ms=int(record["end_ms"]) if record["end_ms"] is not None else None,
            source_text=str(record["source_text"] or ""),
            machine_translation=str(record["machine_translation"] or ""),
            translated_text=str(record["translated_text"] or ""),
            status=str(record["status"]),
            edited=bool(record["edited"]),
            reviewed=bool(record["reviewed"]),
            locked=bool(record["locked"]),
            confidence=float(record["confidence"]) if record["confidence"] is not None else None,
            notes=str(record["notes"] or ""),
            source_hash=str(record["source_hash"] or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )


def translation_source_hash(text: str, start_ms: int | None = None, end_ms: int | None = None) -> str:
    payload = f"{start_ms if start_ms is not None else ''}\0{end_ms if end_ms is not None else ''}\0{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

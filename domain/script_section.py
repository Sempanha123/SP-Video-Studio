from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class ScriptSectionType(StrEnum):
    HOOK = "hook"
    BODY = "body"
    OUTRO = "outro"
    CUSTOM = "custom"


@dataclass(slots=True)
class ScriptSection:
    script_id: str
    order: int
    section_type: str | ScriptSectionType
    title: str
    content: str = ""
    notes: str = ""
    enabled: bool = True
    section_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.section_id

    @property
    def type(self) -> str:
        return self.section_type.value if isinstance(self.section_type, StrEnum) else str(self.section_type)

    def validate(self) -> None:
        if not self.script_id:
            raise ValueError("Script ID is required.")
        if self.order < 0:
            raise ValueError("Section order cannot be negative.")
        if self.type not in {item.value for item in ScriptSectionType}:
            raise ValueError("Unsupported script section type.")
        if not self.title.strip():
            raise ValueError("Section title is required.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.section_id,
            "script_id": self.script_id,
            "order": self.order,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "notes": self.notes,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "ScriptSection":
        raw_meta = record["metadata_json"] if "metadata_json" in record.keys() else None
        try:
            metadata = json.loads(raw_meta) if raw_meta else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            section_id=str(record["id"]),
            script_id=str(record["script_id"]),
            order=int(record["section_order"]),
            section_type=str(record["section_type"]),
            title=str(record["title"]),
            content=str(record["content"] or ""),
            notes=str(record["notes"] or ""),
            enabled=bool(record["enabled"]),
            metadata=metadata,
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )

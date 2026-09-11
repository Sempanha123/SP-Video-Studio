from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import SUPPORTED_LANGUAGES, utc_now_iso

SCRIPT_VERSION = 1


class ScriptStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    READY = "ready"


class ScriptPace(StrEnum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


@dataclass(slots=True)
class Script:
    project_id: str
    title: str
    language: str = "en"
    status: str | ScriptStatus = ScriptStatus.DRAFT
    pace: str | ScriptPace = ScriptPace.NORMAL
    notes: str = ""
    script_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    version: int = SCRIPT_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.script_id

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("Project ID is required.")
        if not self.title.strip():
            raise ValueError("Script title is required.")
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported script language.")
        if str(self.status) not in {item.value for item in ScriptStatus}:
            raise ValueError("Unsupported script status.")
        if str(self.pace) not in {item.value for item in ScriptPace}:
            raise ValueError("Unsupported narration pace.")
        if self.version != SCRIPT_VERSION:
            raise ValueError("Unsupported script version.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.script_id,
            "project_id": self.project_id,
            "title": self.title,
            "language": self.language,
            "status": str(self.status),
            "pace": str(self.pace),
            "notes": self.notes,
            "version": self.version,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Script":
        raw_meta = record["metadata_json"] if "metadata_json" in record.keys() else None
        try:
            metadata = json.loads(raw_meta) if raw_meta else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            script_id=str(record["id"]),
            project_id=str(record["project_id"]),
            title=str(record["title"]),
            language=str(record["language"]),
            status=str(record["status"]),
            pace=str(record["pace"]),
            notes=str(record["notes"] or ""),
            version=int(record["version"]),
            metadata=metadata,
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )

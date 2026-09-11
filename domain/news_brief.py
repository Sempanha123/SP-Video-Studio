from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


@dataclass(slots=True)
class NewsBrief:
    project_id: str
    title: str = "News Brief"
    summary: str = ""
    status: str = "draft"
    source_fingerprint: str = ""
    brief_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.brief_id

    def validate(self) -> None:
        if self.status not in {"draft", "review", "approved", "outdated"}:
            raise ValueError("Unsupported brief status.")

    def to_dict(self) -> dict[str, object]:
        return {"id": self.brief_id, "projectId": self.project_id, "title": self.title, "summary": self.summary,
                "status": self.status, "sourceFingerprint": self.source_fingerprint,
                "createdAt": self.created_at, "updatedAt": self.updated_at, "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsBrief":
        return cls(brief_id=str(row["id"]), project_id=str(row["project_id"]), title=str(row["title"] or "News Brief"),
                   summary=str(row["summary"] or ""), status=str(row["status"] or "draft"),
                   source_fingerprint=str(row["source_fingerprint"] or ""), created_at=str(row["created_at"]),
                   updated_at=str(row["updated_at"]), metadata=json.loads(str(row["metadata_json"] or "{}")))


@dataclass(slots=True)
class NewsBriefItem:
    brief_id: str
    section_key: str
    claim_id: str | None = None
    editor_note: str = ""
    order: int = 0
    item_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.item_id

    def to_dict(self) -> dict[str, object]:
        return {"id": self.item_id, "briefId": self.brief_id, "section": self.section_key,
                "claimId": self.claim_id or "", "editorNote": self.editor_note, "order": self.order,
                "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsBriefItem":
        return cls(item_id=str(row["id"]), brief_id=str(row["brief_id"]), section_key=str(row["section_key"]),
                   claim_id=row["claim_id"], editor_note=str(row["editor_note"] or ""), order=int(row["item_order"]),
                   metadata=json.loads(str(row["metadata_json"] or "{}")))

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


@dataclass(slots=True)
class NewsScriptMapping:
    project_id: str
    script_id: str
    script_section_id: str
    text_snapshot: str
    claim_ids: list[str] = field(default_factory=list)
    sentence_key: str = ""
    mapping_type: str = "factual"
    status: str = "grounded"
    mapping_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.mapping_id

    def to_dict(self) -> dict[str, object]:
        return {"id": self.mapping_id, "projectId": self.project_id, "scriptId": self.script_id,
                "scriptSectionId": self.script_section_id, "sentenceKey": self.sentence_key,
                "textSnapshot": self.text_snapshot, "claimIds": list(self.claim_ids),
                "mappingType": self.mapping_type, "status": self.status,
                "createdAt": self.created_at, "updatedAt": self.updated_at, "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsScriptMapping":
        return cls(mapping_id=str(row["id"]), project_id=str(row["project_id"]), script_id=str(row["script_id"]),
                   script_section_id=str(row["script_section_id"]), sentence_key=str(row["sentence_key"] or ""),
                   text_snapshot=str(row["text_snapshot"] or ""), claim_ids=json.loads(str(row["claim_ids_json"] or "[]")),
                   mapping_type=str(row["mapping_type"] or "factual"), status=str(row["status"] or "grounded"),
                   created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
                   metadata=json.loads(str(row["metadata_json"] or "{}")))

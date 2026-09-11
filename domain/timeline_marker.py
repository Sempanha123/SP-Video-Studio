from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


@dataclass(slots=True)
class TimelineMarker:
    project_id: str
    time_ms: int
    label: str = "Marker"
    color: str = ""
    marker_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def id(self) -> str: return self.marker_id
    def validate(self) -> None:
        if not self.project_id: raise ValueError("Timeline marker requires a project.")
        if self.time_ms < 0: raise ValueError("Timeline marker time cannot be negative.")
        if not self.label.strip(): self.label = "Marker"

    def to_dict(self) -> dict[str, Any]:
        self.validate(); return {"id":self.id,"projectId":self.project_id,"timeMs":self.time_ms,"label":self.label,"color":self.color,"metadata":dict(self.metadata),"createdAt":self.created_at,"updatedAt":self.updated_at}

    @classmethod
    def from_record(cls,row:Mapping[str,Any])->"TimelineMarker":
        try: metadata=json.loads(row["metadata_json"] or "{}")
        except Exception: metadata={}
        return cls(marker_id=str(row["id"]),project_id=str(row["project_id"]),time_ms=int(row["time_ms"]),label=str(row["label"]),color=str(row["color"] or ""),metadata=metadata if isinstance(metadata,dict) else {},created_at=str(row["created_at"]),updated_at=str(row["updated_at"]))

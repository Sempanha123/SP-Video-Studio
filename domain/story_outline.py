from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso

OUTLINE_STATUSES={"draft","review","approved","outdated"}

@dataclass(slots=True)
class StoryOutline:
    project_id:str
    title:str="Story Outline"
    summary:str=""
    status:str="draft"
    version:int=1
    source_fingerprint:str=""
    outline_id:str=field(default_factory=lambda:str(uuid4()))
    created_at:str=field(default_factory=utc_now_iso)
    updated_at:str=field(default_factory=utc_now_iso)
    metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def id(self)->str:return self.outline_id
    def validate(self)->None:
        if not self.project_id:raise ValueError("Story outline requires a project.")
        if not self.title.strip():raise ValueError("Story outline title is required.")
        if self.status not in OUTLINE_STATUSES:raise ValueError("Unsupported Story outline status.")
        if self.version<1:raise ValueError("Outline version must be positive.")
    def to_dict(self)->dict[str,Any]:
        return {"id":self.id,"projectId":self.project_id,"title":self.title,"summary":self.summary,"status":self.status,
                "version":self.version,"sourceFingerprint":self.source_fingerprint,"createdAt":self.created_at,
                "updatedAt":self.updated_at,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->"StoryOutline":
        return cls(outline_id=str(row["id"]),project_id=str(row["project_id"]),title=str(row["title"]),summary=str(row["summary"] or ""),
                   status=str(row["status"]),version=int(row["outline_version"]),source_fingerprint=str(row["source_fingerprint"] or ""),
                   created_at=str(row["created_at"]),updated_at=str(row["updated_at"]),metadata=json.loads(str(row["metadata_json"] or "{}")))

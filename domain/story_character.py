from __future__ import annotations
import json
from dataclasses import dataclass,field
from typing import Any,Mapping
from uuid import uuid4
from domain.project import utc_now_iso

CHARACTER_ROLES={"narrator","main_character","supporting_character","expert","host","other"}
@dataclass(slots=True)
class StoryCharacter:
    project_id:str
    name:str
    role:str="other"
    description:str=""
    voice_id:str=""
    notes:str=""
    character_id:str=field(default_factory=lambda:str(uuid4()))
    created_at:str=field(default_factory=utc_now_iso)
    updated_at:str=field(default_factory=utc_now_iso)
    metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def id(self)->str:return self.character_id
    def validate(self)->None:
        if not self.project_id:raise ValueError("Character requires a project.")
        if not self.name.strip():raise ValueError("Character name is required.")
        if self.role not in CHARACTER_ROLES:raise ValueError("Unsupported character role.")
    def to_dict(self)->dict[str,Any]:return {"id":self.id,"projectId":self.project_id,"name":self.name,"role":self.role,"description":self.description,"voiceId":self.voice_id,"notes":self.notes,"createdAt":self.created_at,"updatedAt":self.updated_at,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->"StoryCharacter":
        return cls(character_id=str(row["id"]),project_id=str(row["project_id"]),name=str(row["name"]),role=str(row["role"]),description=str(row["description"] or ""),voice_id=str(row["voice_id"] or ""),notes=str(row["notes"] or ""),created_at=str(row["created_at"]),updated_at=str(row["updated_at"]),metadata=json.loads(str(row["metadata_json"] or "{}")))

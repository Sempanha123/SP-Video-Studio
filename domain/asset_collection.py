from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso

@dataclass(slots=True)
class AssetCollection:
    name:str
    description:str=""
    collection_id:str=field(default_factory=lambda:str(uuid4()))
    created_at:str=field(default_factory=utc_now_iso)
    updated_at:str=field(default_factory=utc_now_iso)
    metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def id(self): return self.collection_id
    def validate(self):
        if not self.name.strip(): raise ValueError("Collection name is required.")
    def to_dict(self): return {"id":self.id,"name":self.name,"description":self.description,"createdAt":self.created_at,"updatedAt":self.updated_at,"metadata":dict(self.metadata)}

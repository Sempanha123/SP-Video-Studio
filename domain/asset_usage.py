from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4
from domain.project import utc_now_iso

USAGE_TYPES={"scene","timeline","template","logo","background","presenter","broll","audio","other"}
@dataclass(slots=True)
class AssetUsage:
    asset_id:str
    project_id:str
    project_media_id:str
    usage_type:str="other"
    used_at:str=field(default_factory=utc_now_iso)
    metadata:dict[str,Any]=field(default_factory=dict)
    usage_id:str=field(default_factory=lambda:str(uuid4()))
    @property
    def id(self):return self.usage_id
    def validate(self):
        if self.usage_type not in USAGE_TYPES: raise ValueError("Unsupported asset usage type.")
        if not self.asset_id or not self.project_id or not self.project_media_id: raise ValueError("Asset usage identity is incomplete.")
    def to_dict(self):return {"id":self.id,"assetId":self.asset_id,"projectId":self.project_id,"projectMediaId":self.project_media_id,"usageType":self.usage_type,"usedAt":self.used_at,"metadata":dict(self.metadata)}

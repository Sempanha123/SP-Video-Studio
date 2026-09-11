from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso

@dataclass(slots=True)
class NewsVisualElement:
    project_id:str; scene_id:str; scene_overlay_id:str; graphic_type:str; claim_id:str=""; source_id:str=""; quote_type:str=""; follow_theme:bool=True; status:str="current"; source_hash:str=""; element_id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=utc_now_iso); updated_at:str=field(default_factory=utc_now_iso); metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def id(self):return self.element_id
    def to_dict(self):return {"id":self.id,"projectId":self.project_id,"sceneId":self.scene_id,"sceneOverlayId":self.scene_overlay_id,"graphicType":self.graphic_type,"claimId":self.claim_id,"sourceId":self.source_id,"quoteType":self.quote_type,"followTheme":self.follow_theme,"status":self.status,"sourceHash":self.source_hash,"createdAt":self.created_at,"updatedAt":self.updated_at,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,r:Mapping[str,Any]):return cls(str(r["project_id"]),str(r["scene_id"]),str(r["scene_overlay_id"]),str(r["graphic_type"]),str(r["claim_id"] or ""),str(r["source_id"] or ""),str(r["quote_type"] or ""),bool(r["follow_theme"]),str(r["status"]),str(r["source_hash"] or ""),str(r["id"]),str(r["created_at"]),str(r["updated_at"]),json.loads(str(r["metadata_json"] or "{}")))

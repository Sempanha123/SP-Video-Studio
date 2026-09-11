from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso

@dataclass(frozen=True, slots=True)
class NewsSceneLayoutPreset:
    preset_id:str; name:str; role:str; version:int=1; description:str=""
    def to_dict(self): return {"id":self.preset_id,"name":self.name,"role":self.role,"version":self.version,"description":self.description}

BUILTIN_LAYOUTS=(
 NewsSceneLayoutPreset("headline_focus","Headline Focus","headline"),NewsSceneLayoutPreset("media_headline","Media + Headline","headline"),NewsSceneLayoutPreset("media_lower_third","Media + Lower Third","lower_third"),NewsSceneLayoutPreset("fact_focus","Fact Focus","fact"),NewsSceneLayoutPreset("quote_focus","Quote Focus","quote"),NewsSceneLayoutPreset("number_focus","Number Focus","number"),NewsSceneLayoutPreset("source_focus","Source Focus","source"),NewsSceneLayoutPreset("split_visual","Split Visual","context"),NewsSceneLayoutPreset("full_media","Full Media","media"),NewsSceneLayoutPreset("intro","Intro","intro"),NewsSceneLayoutPreset("outro","Outro","outro"),)
LAYOUT_BY_ID={x.preset_id:x for x in BUILTIN_LAYOUTS}

@dataclass(slots=True)
class NewsSceneLayoutInstance:
    project_id:str; scene_id:str; preset_id:str; theme_id:str=""; preset_version:int=1; status:str="current"; customized:bool=False; layout_id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=utc_now_iso); updated_at:str=field(default_factory=utc_now_iso); metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def id(self):return self.layout_id
    def to_dict(self):return {"id":self.id,"projectId":self.project_id,"sceneId":self.scene_id,"presetId":self.preset_id,"presetVersion":self.preset_version,"themeId":self.theme_id,"status":self.status,"customized":self.customized,"createdAt":self.created_at,"updatedAt":self.updated_at,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,r:Mapping[str,Any]):return cls(str(r["project_id"]),str(r["scene_id"]),str(r["preset_id"]),str(r["theme_id"] or ""),int(r["preset_version"]),str(r["status"]),bool(r["customized"]),str(r["id"]),str(r["created_at"]),str(r["updated_at"]),json.loads(str(r["metadata_json"] or "{}")))

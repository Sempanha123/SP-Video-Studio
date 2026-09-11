from __future__ import annotations
import hashlib,json
from dataclasses import dataclass,field
from typing import Any,Mapping
from uuid import uuid4
from domain.project import utc_now_iso

BEAT_TYPES={"hook","setup","context","character","development","conflict","discovery","turning_point","climax","resolution","lesson","outro","problem","struggle","explanation","example","current_state","closing","custom"}
BEAT_EMOTIONS={"neutral","warm","tense","hopeful","sad","excited","calm"}

@dataclass(slots=True)
class StoryBeat:
    outline_id:str
    order:int
    beat_type:str
    title:str
    description:str=""
    target_duration_ms:int=5000
    emotion:str="neutral"
    visual_direction:str=""
    script_section_id:str=""
    locked:bool=False
    user_modified:bool=False
    chapter_title:str=""
    character_id:str=""
    voice_override_id:str=""
    notes:str=""
    beat_id:str=field(default_factory=lambda:str(uuid4()))
    created_at:str=field(default_factory=utc_now_iso)
    updated_at:str=field(default_factory=utc_now_iso)
    metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def id(self)->str:return self.beat_id
    def validate(self)->None:
        if not self.outline_id:raise ValueError("Beat requires an outline.")
        if self.order<0:raise ValueError("Beat order cannot be negative.")
        if self.beat_type not in BEAT_TYPES:raise ValueError("Unsupported Story beat type.")
        if not self.title.strip():raise ValueError("Beat title is required.")
        if self.target_duration_ms<=0:raise ValueError("Beat duration must be positive.")
        if self.emotion not in BEAT_EMOTIONS:raise ValueError("Unsupported beat emotion.")
    def source_hash(self)->str:
        payload=[self.beat_type,self.title.strip(),self.description.strip(),int(self.target_duration_ms),self.emotion,self.visual_direction.strip(),self.character_id,self.voice_override_id]
        return hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(",",":"),sort_keys=False).encode("utf-8")).hexdigest()
    def to_dict(self)->dict[str,Any]:
        return {"id":self.id,"outlineId":self.outline_id,"order":self.order,"type":self.beat_type,"title":self.title,"description":self.description,
                "targetDurationMs":self.target_duration_ms,"emotion":self.emotion,"visualDirection":self.visual_direction,"scriptSectionId":self.script_section_id,
                "locked":self.locked,"userModified":self.user_modified,"chapterTitle":self.chapter_title,"characterId":self.character_id,"voiceOverrideId":self.voice_override_id,
                "notes":self.notes,"sourceHash":self.source_hash(),"createdAt":self.created_at,"updatedAt":self.updated_at,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->"StoryBeat":
        return cls(beat_id=str(row["id"]),outline_id=str(row["outline_id"]),order=int(row["beat_order"]),beat_type=str(row["beat_type"]),title=str(row["title"]),
                   description=str(row["description"] or ""),target_duration_ms=int(row["target_duration_ms"]),emotion=str(row["emotion"] or "neutral"),
                   visual_direction=str(row["visual_direction"] or ""),script_section_id=str(row["script_section_id"] or ""),locked=bool(row["locked"]),
                   user_modified=bool(row["user_modified"]),chapter_title=str(row["chapter_title"] or ""),character_id=str(row["character_id"] or ""),
                   voice_override_id=str(row["voice_override_id"] or ""),notes=str(row["notes"] or ""),created_at=str(row["created_at"]),updated_at=str(row["updated_at"]),
                   metadata=json.loads(str(row["metadata_json"] or "{}")))

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


@dataclass(slots=True)
class ManualAudioClip:
    project_id: str
    media_id: str
    start_ms: int
    duration_ms: int
    scene_id: str = ""
    source_in_ms: int = 0
    volume: float = 1.0
    muted: bool = False
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    clip_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str: return self.clip_id

    def validate(self) -> None:
        if not self.project_id or not self.media_id: raise ValueError("Audio clip project and media are required.")
        if self.start_ms < 0 or self.duration_ms <= 0 or self.source_in_ms < 0: raise ValueError("Audio clip timing is invalid.")
        self.volume=max(0.0,min(2.0,float(self.volume))); self.fade_in_ms=max(0,int(self.fade_in_ms)); self.fade_out_ms=max(0,int(self.fade_out_ms))
        if self.fade_in_ms+self.fade_out_ms>self.duration_ms: raise ValueError("Audio fades exceed clip duration.")

    def to_dict(self)->dict[str,Any]:
        self.validate(); return {"id":self.id,"projectId":self.project_id,"sceneId":self.scene_id,"mediaId":self.media_id,"startMs":self.start_ms,"durationMs":self.duration_ms,"sourceInMs":self.source_in_ms,"volume":self.volume,"muted":self.muted,"fadeInMs":self.fade_in_ms,"fadeOutMs":self.fade_out_ms,"metadata":dict(self.metadata)}

    @classmethod
    def from_record(cls,r:Mapping[str,Any])->"ManualAudioClip":
        try: meta=json.loads(str(r["metadata_json"] or "{}"))
        except Exception: meta={}
        return cls(clip_id=str(r["id"]),project_id=str(r["project_id"]),scene_id=str(r["scene_id"] or ""),media_id=str(r["media_id"]),start_ms=int(r["start_ms"]),duration_ms=int(r["duration_ms"]),source_in_ms=int(r["source_in_ms"]),volume=float(r["volume"]),muted=bool(r["muted"]),fade_in_ms=int(r["fade_in_ms"]),fade_out_ms=int(r["fade_out_ms"]),metadata=meta if isinstance(meta,dict) else {},created_at=str(r["created_at"]),updated_at=str(r["updated_at"]))

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from domain.render_settings import RenderSettings

RENDER_SPEC_SCHEMA_VERSION=1


@dataclass(slots=True)
class RenderPlan:
    project_id: str
    output_path: str
    settings: RenderSettings
    scenes: list[dict[str,Any]]
    expected_duration_ms: int
    temp_directory: str
    subtitle_track_id: str=""
    renderer_version: str="phase15-1"
    ffmpeg_version: str=""
    plan_id: str=field(default_factory=lambda:str(uuid4()))
    metadata: dict[str,Any]=field(default_factory=dict)
    schema_version: int=RENDER_SPEC_SCHEMA_VERSION

    @property
    def id(self)->str: return self.plan_id

    def validate(self)->None:
        self.settings.validate()
        if not self.project_id: raise ValueError("Render plan requires a project.")
        if not self.output_path: raise ValueError("Render plan requires an output path.")
        if not self.scenes: raise ValueError("Render plan requires at least one scene.")
        if self.expected_duration_ms<=0: raise ValueError("Render duration must be positive.")
        for item in self.scenes:
            if int(item.get("durationMs",0) or 0)<=0: raise ValueError("Every render scene requires a positive duration.")

    def snapshot(self)->dict[str,Any]:
        return {"schemaVersion":self.schema_version,"rendererVersion":self.renderer_version,"projectId":self.project_id,"outputPath":self.output_path,"settings":self.settings.to_dict(),"expectedDurationMs":self.expected_duration_ms,"subtitleTrackId":self.subtitle_track_id,"ffmpegVersion":self.ffmpeg_version,"scenes":self.scenes,"metadata":dict(self.metadata)}


def expected_sequence_duration_ms(scenes:list[dict[str,Any]])->int:
    total=sum(int(s.get("durationMs",0) or 0) for s in scenes)
    for scene in scenes[:-1]:
        t=scene.get("transitionOut",{}) or {}; kind=str(t.get("type","cut")); d=max(0,int(t.get("durationMs",0) or 0))
        if kind in {"crossfade","slide"}: total-=min(d,int(scene.get("durationMs",0) or 0))
    return max(0,total)


def project_time_map(scenes:list[dict[str,Any]])->list[dict[str,int|str]]:
    cursor=0; result=[]
    for i,scene in enumerate(scenes):
        dur=int(scene.get("durationMs",0) or 0); result.append({"sceneId":str(scene.get("sceneId","")),"startMs":cursor,"endMs":cursor+dur,"durationMs":dur})
        if i<len(scenes)-1:
            t=scene.get("transitionOut",{}) or {}; overlap=int(t.get("durationMs",0) or 0) if str(t.get("type","cut")) in {"crossfade","slide"} else 0
            cursor+=dur-max(0,min(overlap,dur))
        else: cursor+=dur
    return result

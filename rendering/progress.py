from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderProgressState:
    stage: str
    stage_progress: float
    overall_progress: float
    scene_index: int=0
    scene_count: int=0
    out_time_ms: int=0
    speed: float=0.0


class RenderProgressMapper:
    """Deterministic stage weights: scenes 70%, combine 15%, final 15%."""
    def __init__(self, scene_count:int) -> None: self.scene_count=max(1,int(scene_count))

    def scene(self,index:int,fraction:float,out_time_ms:int=0,speed:float=0)->RenderProgressState:
        f=max(0,min(1,float(fraction))); overall=.70*((index+f)/self.scene_count)
        return RenderProgressState("rendering_scene",f,overall,index,self.scene_count,out_time_ms,speed)

    def combine(self,fraction:float,out_time_ms:int=0,speed:float=0)->RenderProgressState:
        f=max(0,min(1,float(fraction))); return RenderProgressState("combining_scenes",f,.70+.15*f,self.scene_count,self.scene_count,out_time_ms,speed)

    def final(self,fraction:float,out_time_ms:int=0,speed:float=0)->RenderProgressState:
        f=max(0,min(1,float(fraction))); return RenderProgressState("finalizing",f,.85+.15*f,self.scene_count,self.scene_count,out_time_ms,speed)

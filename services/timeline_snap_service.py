from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True,slots=True)
class SnapResult:
    time_ms:int
    snapped:bool
    target_ms:int|None=None

class TimelineSnapService:
    @staticmethod
    def threshold_ms(pixels_per_second:float,pixel_threshold:float=8.0)->int:
        pps=max(1.0,float(pixels_per_second)); return max(1,int(round(float(pixel_threshold)*1000.0/pps)))
    def snap(self,value_ms:int,targets:list[int],pixels_per_second:float,pixel_threshold:float=8.0)->SnapResult:
        value=max(0,int(value_ms)); threshold=self.threshold_ms(pixels_per_second,pixel_threshold)
        if not targets:return SnapResult(value,False,None)
        target=min((max(0,int(x)) for x in targets),key=lambda x:abs(x-value))
        return SnapResult(target,True,target) if abs(target-value)<=threshold else SnapResult(value,False,None)

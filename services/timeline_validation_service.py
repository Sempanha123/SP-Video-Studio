from __future__ import annotations
from dataclasses import dataclass
from domain.timeline_clip import TimelineClip

@dataclass(frozen=True,slots=True)
class TimelineIssue:
    severity:str
    code:str
    message:str
    clip_id:str=""

class TimelineValidationService:
    def validate_clips(self,clips:list[TimelineClip],duration_ms:int)->list[TimelineIssue]:
        issues=[]
        for clip in clips:
            try: clip.validate()
            except ValueError as exc: issues.append(TimelineIssue("error","invalid_clip",str(exc),clip.id)); continue
            if clip.end_ms>duration_ms+250 and clip.source_type not in {"subtitle"}: issues.append(TimelineIssue("warning","beyond_project","Clip extends beyond the current project duration.",clip.id))
            if bool(clip.metadata.get("missing")): issues.append(TimelineIssue("warning","missing_source","The source used by this clip is missing.",clip.id))
        return issues

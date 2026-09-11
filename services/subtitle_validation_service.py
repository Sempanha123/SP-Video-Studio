from __future__ import annotations

from dataclasses import dataclass

from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle


@dataclass(frozen=True, slots=True)
class SubtitleIssue:
    severity: str
    code: str
    message: str
    cue_id: str = ""

    def to_dict(self) -> dict[str,str]:
        return {"severity":self.severity,"code":self.code,"message":self.message,"cueId":self.cue_id}


class SubtitleValidationService:
    MIN_DURATION_MS=300
    LONG_DURATION_MS=10_000
    ENGLISH_FAST_CPS=25.0
    KHMER_FAST_CPS=32.0

    def validate(self,cues:list[SubtitleCue],style:SubtitleStyle,language:str,media_duration_ms:int|None=None)->list[SubtitleIssue]:
        issues=[]; ordered=sorted(cues,key=lambda c:(c.start_ms,c.order))
        seen=set()
        for index,cue in enumerate(ordered):
            if cue.cue_id in seen: issues.append(SubtitleIssue("error","duplicate_id","Duplicate cue ID.",cue.cue_id))
            seen.add(cue.cue_id)
            if cue.start_ms<0 or cue.end_ms<=cue.start_ms: issues.append(SubtitleIssue("error","invalid_timing","Cue ends before it starts or has a negative time.",cue.cue_id)); continue
            duration=cue.end_ms-cue.start_ms
            if media_duration_ms and cue.end_ms>media_duration_ms+1000: issues.append(SubtitleIssue("warning","past_media_end","Cue extends beyond the source media duration.",cue.cue_id))
            if duration<self.MIN_DURATION_MS: issues.append(SubtitleIssue("warning","too_short","Cue duration is very short.",cue.cue_id))
            if duration>self.LONG_DURATION_MS: issues.append(SubtitleIssue("warning","too_long","Cue duration is unusually long.",cue.cue_id))
            lines=max(1,len(cue.text.splitlines()))+(len(cue.secondary_text.splitlines()) if cue.secondary_text else 0)
            if lines>style.max_lines*(2 if cue.secondary_text else 1): issues.append(SubtitleIssue("warning","too_many_lines","Cue uses more lines than the selected style recommends.",cue.cue_id))
            chars=len("".join(ch for ch in cue.text if not ch.isspace()))
            cps=chars/max(duration/1000,0.001); limit=self.KHMER_FAST_CPS if language=="km" else self.ENGLISH_FAST_CPS
            if chars>=8 and cps>limit: issues.append(SubtitleIssue("warning","reading_too_fast","Subtitle reading speed may be too fast.",cue.cue_id))
            if index+1<len(ordered) and cue.end_ms>ordered[index+1].start_ms: issues.append(SubtitleIssue("warning","overlap","Cue overlaps the next cue.",cue.cue_id))
        if style.vertical_margin<0 or style.vertical_margin>=0.5 or style.horizontal_margin<0 or style.horizontal_margin>=0.5:
            issues.append(SubtitleIssue("error","unsafe_margin","Subtitle position is outside the normalized safe canvas."))
        if style.vertical_position=="bottom" and style.vertical_margin<0.04:
            issues.append(SubtitleIssue("warning","safe_area","Bottom captions may be too close to platform UI/screen edge."))
        return issues

    @staticmethod
    def counts(issues:list[SubtitleIssue])->tuple[int,int]:
        return sum(i.severity=="error" for i in issues),sum(i.severity=="warning" for i in issues)

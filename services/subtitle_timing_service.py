from __future__ import annotations

import re
from copy import deepcopy
from uuid import uuid4

from domain.subtitle_cue import SubtitleCue
from domain.subtitle_word import SubtitleWord

_TIME_RE=re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})$")


class SubtitleTimingService:
    @staticmethod
    def parse_timestamp(value:str)->int:
        match=_TIME_RE.match(value.strip())
        if not match: raise ValueError("Use HH:MM:SS.mmm time format.")
        hours=int(match.group(1) or 0); minutes=int(match.group(2)); seconds=int(match.group(3)); millis=int(match.group(4))
        if minutes>=60 or seconds>=60: raise ValueError("Subtitle timestamp is invalid.")
        return ((hours*60+minutes)*60+seconds)*1000+millis

    @staticmethod
    def format_timestamp(ms:int)->str:
        value=max(0,int(ms)); h,rem=divmod(value,3_600_000); m,rem=divmod(rem,60_000); s,x=divmod(rem,1000); return f"{h:02d}:{m:02d}:{s:02d}.{x:03d}"

    @staticmethod
    def shift(cues:list[SubtitleCue],delta_ms:int,selected_ids:set[str]|None=None)->list[SubtitleCue]:
        selected_ids=selected_ids or set(); result=deepcopy(cues)
        targets=[q for q in result if not selected_ids or q.cue_id in selected_ids]
        if targets and min(q.start_ms+delta_ms for q in targets)<0: raise ValueError("Timing shift would create a negative subtitle start.")
        for cue in targets:
            cue.start_ms+=delta_ms; cue.end_ms+=delta_ms
            for word in cue.words: word.start_ms+=delta_ms; word.end_ms+=delta_ms
        return SubtitleTimingService.normalize(result)

    @staticmethod
    def split(cue:SubtitleCue,split_ms:int,text_before:str,text_after:str)->tuple[SubtitleCue,SubtitleCue]:
        if not cue.start_ms<split_ms<cue.end_ms: raise ValueError("Split time must fall inside the cue.")
        if not text_before.strip() and not text_after.strip(): raise ValueError("Split cues cannot both be empty.")
        first=deepcopy(cue); first.end_ms=split_ms; first.text=text_before; first.edited=True; first.words=[]
        second=deepcopy(cue); second.cue_id=str(uuid4()); second.start_ms=split_ms; second.text=text_after; second.edited=True; second.words=[]
        for word in cue.words:
            target=first if word.end_ms<=split_ms else second if word.start_ms>=split_ms else None
            if target is not None:
                target.words.append(SubtitleWord(cue_id=target.cue_id,order=len(target.words),text=word.text,start_ms=word.start_ms,end_ms=word.end_ms,probability=word.probability,highlight_group=word.highlight_group,metadata=dict(word.metadata)))
        return first,second

    @staticmethod
    def merge(first:SubtitleCue,second:SubtitleCue)->SubtitleCue:
        if first.track_id!=second.track_id: raise ValueError("Only cues from the same track can be merged.")
        merged=deepcopy(first); merged.end_ms=max(first.end_ms,second.end_ms)
        merged.text=SubtitleTimingService._join(first.text,second.text); merged.secondary_text=SubtitleTimingService._join(first.secondary_text,second.secondary_text); merged.edited=True
        merged.words=[]
        for item in [*first.words,*second.words]:
            merged.words.append(SubtitleWord(cue_id=merged.cue_id,order=len(merged.words),text=item.text,start_ms=item.start_ms,end_ms=item.end_ms,probability=item.probability,highlight_group=item.highlight_group,metadata=dict(item.metadata)))
        return merged

    @staticmethod
    def normalize(cues:list[SubtitleCue])->list[SubtitleCue]:
        ordered=sorted(cues,key=lambda q:(q.start_ms,q.end_ms,q.order))
        for index,cue in enumerate(ordered): cue.order=index
        return ordered

    @staticmethod
    def _join(a:str,b:str)->str:
        if not a: return b
        if not b: return a
        return a.rstrip()+("\n" if "\n" in a or "\n" in b else " ")+b.lstrip()

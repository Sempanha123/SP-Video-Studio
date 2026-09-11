from __future__ import annotations

from copy import deepcopy
from uuid import uuid4


class ShortSubtitleRangeService:
    """Re-times duplicated Phase12 subtitle tracks to a derived Short sequence."""
    def __init__(self, subtitle_service) -> None:
        self.subtitles=subtitle_service

    def trim_project_tracks(self, project_id: str, segments: list) -> int:
        if not segments:return 0
        changed=0
        for track in self.subtitles.list_tracks(project_id):
            try: _,_,source_cues=self.subtitles.get(project_id,track.id)
            except Exception: continue
            result=[]; assembled=0
            for segment in sorted(segments,key=lambda x:x.order):
                a=int(segment.source_start_ms); b=int(segment.source_end_ms)
                for cue in source_cues:
                    start=max(a,int(cue.start_ms)); end=min(b,int(cue.end_ms))
                    if end<=start: continue
                    item=deepcopy(cue); item.cue_id=str(uuid4()); item.order=len(result); item.start_ms=assembled+start-a; item.end_ms=assembled+end-a
                    item.metadata=dict(item.metadata); item.metadata["shortSourceStartMs"]=start; item.metadata["shortSourceEndMs"]=end
                    words=[]
                    for word in getattr(cue,"words",[]) or []:
                        ws=max(start,int(word.start_ms)); we=min(end,int(word.end_ms))
                        if we<=ws: continue
                        w=deepcopy(word); w.word_id=str(uuid4()); w.cue_id=item.id; w.start_ms=assembled+ws-a; w.end_ms=assembled+we-a; words.append(w)
                    item.words=words; result.append(item)
                assembled+=max(0,b-a)
            if result:
                self.subtitles.repository.replace_cues(project_id,track.id,result); changed+=1
        return changed

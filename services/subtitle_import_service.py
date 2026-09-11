from __future__ import annotations

import re
from pathlib import Path

from domain.subtitle_cue import SubtitleCue
from services.subtitle_timing_service import SubtitleTimingService


class SubtitleImportError(RuntimeError): pass

class SubtitleImportService:
    _srt_time=re.compile(r"(?P<a>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<b>\d{1,2}:\d{2}:\d{2}[,.]\d{3})")
    _vtt_time=re.compile(r"(?P<a>(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3})\s*-->\s*(?P<b>(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3})")

    def parse(self,path:Path,track_id:str)->list[SubtitleCue]:
        try: text=Path(path).read_text(encoding='utf-8-sig')
        except (OSError,UnicodeDecodeError) as exc: raise SubtitleImportError("Subtitle file could not be read as UTF-8.") from exc
        suffix=Path(path).suffix.lower()
        if suffix=='.srt': return self._parse_blocks(text,track_id,self._srt_time)
        if suffix=='.vtt': return self._parse_blocks(text.replace('WEBVTT','',1),track_id,self._vtt_time)
        if suffix=='.ass': return self._parse_ass(text,track_id)
        raise SubtitleImportError("Unsupported subtitle format.")

    def _parse_blocks(self,text:str,track_id:str,time_re)->list[SubtitleCue]:
        cues=[]
        for block in re.split(r"\n\s*\n",text.replace('\r\n','\n').strip()):
            lines=[x for x in block.split('\n') if x.strip()]
            idx=next((i for i,line in enumerate(lines) if time_re.search(line)),None)
            if idx is None: continue
            m=time_re.search(lines[idx]); start=SubtitleTimingService.parse_timestamp(m.group('a').replace(',','.')); end=SubtitleTimingService.parse_timestamp(m.group('b').replace(',','.'))
            content='\n'.join(lines[idx+1:]);
            if end>start: cues.append(SubtitleCue(track_id=track_id,order=len(cues),start_ms=start,end_ms=end,text=content))
        return cues

    def _parse_ass(self,text:str,track_id:str)->list[SubtitleCue]:
        cues=[]
        for line in text.splitlines():
            if not line.startswith('Dialogue:'): continue
            parts=line[len('Dialogue:'):].split(',',9)
            if len(parts)<10: continue
            def parse_ass(v):
                h,m,rest=v.strip().split(':'); s,cs=rest.split('.'); return ((int(h)*60+int(m))*60+int(s))*1000+int(cs.ljust(2,'0')[:2])*10
            start,end=parse_ass(parts[1]),parse_ass(parts[2]); body=parts[9].replace(r'\N','\n').replace(r'\n','\n'); body=re.sub(r"\{[^{}]*\}","",body)
            if end>start: cues.append(SubtitleCue(track_id=track_id,order=len(cues),start_ms=start,end_ms=end,text=body))
        return cues

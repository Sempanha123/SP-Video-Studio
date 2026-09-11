from __future__ import annotations

from pathlib import Path

from media.subtitles.ass_exporter import escape_ass_text, format_ass_timestamp
from media.subtitles.ass_style_builder import build_ass_style
from services.subtitle_service import SubtitleService


class SubtitleRenderer:
    def __init__(self, subtitle_service: SubtitleService) -> None: self.subtitle_service=subtitle_service

    def prepare_ass(self, project_id:str, track_id:str, destination:Path, *, width:int, height:int) -> Path:
        track,style,cues=self.subtitle_service.get(project_id,track_id)
        destination.parent.mkdir(parents=True,exist_ok=True)
        header=(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
                "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
                f"Style: {build_ass_style(style,canvas_width=width,canvas_height=height)}\n\n"
                "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
        rows=[]
        for cue in sorted(cues,key=lambda q:(q.start_ms,q.order)):
            text=escape_ass_text(cue.text)
            if cue.secondary_text: text += r"\N"+escape_ass_text(cue.secondary_text)
            rows.append(f"Dialogue: 0,{format_ass_timestamp(cue.start_ms)},{format_ass_timestamp(cue.end_ms)},Default,,0,0,0,,{text}")
        destination.write_text(header+"\n".join(rows)+( "\n" if rows else ""),encoding="utf-8")
        return destination

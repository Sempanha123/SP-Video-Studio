from __future__ import annotations

from .ass_style_builder import ass_color

from domain.subtitle import SubtitleTrack
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle
from media.subtitles.ass_style_builder import build_ass_style
from media.subtitles.base import SubtitleExporter


def format_ass_timestamp(ms: int) -> str:
    value=max(0,int(ms)); hours,rem=divmod(value,3_600_000); minutes,rem=divmod(rem,60_000); seconds,ms=divmod(rem,1000); cs=round(ms/10)
    if cs>=100: seconds+=1; cs=0
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def escape_ass_text(text: str) -> str:
    text=text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
    return text.replace("\r\n", r"\N").replace("\n", r"\N").replace("\r", r"\N")


class ASSExporter(SubtitleExporter):
    extension=".ass"

    def render(self, track: SubtitleTrack, cues: list[SubtitleCue], style: SubtitleStyle) -> str:
        header=("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
                "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
                f"Style: {build_ass_style(style)}\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
        rows=[]
        for cue in sorted(cues,key=lambda item:(item.start_ms,item.order)):
            text=escape_ass_text(cue.text)
            if cue.secondary_text:
                text += r"\N" + escape_ass_text(cue.secondary_text)
            rows.append(f"Dialogue: 0,{format_ass_timestamp(cue.start_ms)},{format_ass_timestamp(cue.end_ms)},Default,,0,0,0,,{text}")
        return header+"\n".join(rows)+( "\n" if rows else "")

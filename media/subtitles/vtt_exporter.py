from __future__ import annotations

from domain.subtitle import SubtitleTrack
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle
from media.subtitles.base import SubtitleExporter, cue_lines


def format_vtt_timestamp(ms: int) -> str:
    value=max(0,int(ms)); hours,rem=divmod(value,3_600_000); minutes,rem=divmod(rem,60_000); seconds,millis=divmod(rem,1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def escape_vtt_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class VTTExporter(SubtitleExporter):
    extension = ".vtt"

    def render(self, track: SubtitleTrack, cues: list[SubtitleCue], style: SubtitleStyle) -> str:
        blocks=["WEBVTT", ""]
        for cue in sorted(cues,key=lambda item:(item.start_ms,item.order)):
            text="\n".join(escape_vtt_text(line) for line in cue_lines(cue))
            blocks.extend([f"{format_vtt_timestamp(cue.start_ms)} --> {format_vtt_timestamp(cue.end_ms)}",text,""])
        return "\n".join(blocks)

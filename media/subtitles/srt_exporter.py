from __future__ import annotations

from domain.subtitle import SubtitleTrack
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle
from media.subtitles.base import SubtitleExporter, cue_lines


def format_srt_timestamp(ms: int) -> str:
    value = max(0, int(ms))
    hours, rem = divmod(value, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


class SRTExporter(SubtitleExporter):
    extension = ".srt"

    def render(self, track: SubtitleTrack, cues: list[SubtitleCue], style: SubtitleStyle) -> str:
        blocks: list[str] = []
        for index, cue in enumerate(sorted(cues, key=lambda item: (item.start_ms, item.order)), 1):
            text = "\n".join(cue_lines(cue)).replace("\r\n", "\n").replace("\r", "\n")
            blocks.append(f"{index}\n{format_srt_timestamp(cue.start_ms)} --> {format_srt_timestamp(cue.end_ms)}\n{text}")
        return "\n\n".join(blocks) + ("\n" if blocks else "")

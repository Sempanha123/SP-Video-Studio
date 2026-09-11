from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from domain.subtitle import SubtitleTrack
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle


class SubtitleExportError(RuntimeError):
    pass


class SubtitleExporter(ABC):
    extension = ""

    @abstractmethod
    def render(self, track: SubtitleTrack, cues: list[SubtitleCue], style: SubtitleStyle) -> str:
        raise NotImplementedError

    def export(self, track: SubtitleTrack, cues: list[SubtitleCue], style: SubtitleStyle, destination: Path) -> Path:
        path = Path(destination)
        if path.suffix.lower() != self.extension:
            path = path.with_suffix(self.extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(self.render(track, cues, style), encoding="utf-8")
        except OSError as exc:
            raise SubtitleExportError("Subtitle file could not be written.") from exc
        return path


def cue_lines(cue: SubtitleCue) -> list[str]:
    lines = [cue.text]
    if cue.secondary_text:
        lines.append(cue.secondary_text)
    return lines

from dataclasses import dataclass


@dataclass(slots=True)
class SubtitleCue:
    start: float
    end: float
    text: str
    language: str = "en"
    speaker: str | None = None

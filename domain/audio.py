from dataclasses import dataclass


@dataclass(slots=True)
class AudioSettings:
    volume: float = 1.0
    muted: bool = False
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0

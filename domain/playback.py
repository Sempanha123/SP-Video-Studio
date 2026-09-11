from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PlaybackState(StrEnum):
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ENDED = "ended"
    ERROR = "error"


PLAYABLE_MEDIA_TYPES = {"video", "audio"}
PREVIEW_MEDIA_TYPES = {"video", "audio", "image"}
SEEK_STEP_MS = 5_000
LARGE_SEEK_STEP_MS = 10_000


@dataclass(slots=True)
class PlaybackSelection:
    media_id: str
    project_id: str
    media_type: str
    name: str
    path: str
    duration_ms: int = 0
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    sample_rate: int | None = None
    channels: int | None = None

    @property
    def playable(self) -> bool:
        return self.media_type in PLAYABLE_MEDIA_TYPES

    @property
    def image(self) -> bool:
        return self.media_type == "image"

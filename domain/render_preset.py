from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RenderPreset:
    preset_id: str
    name: str
    width: int
    height: int
    fps: int
    container: str = "mp4"
    video_codec: str = "h264"
    audio_codec: str = "aac"
    quality_profile: str = "balanced"
    builtin: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.preset_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "container": self.container,
            "videoCodec": self.video_codec,
            "audioCodec": self.audio_codec,
            "qualityProfile": self.quality_profile,
            "builtin": self.builtin,
            "metadata": dict(self.metadata),
        }


BUILTIN_RENDER_PRESETS: tuple[RenderPreset, ...] = (
    RenderPreset("vertical_full_hd", "Vertical Full HD", 1080, 1920, 30, metadata={"aspectRatio": "9:16"}),
    RenderPreset("landscape_full_hd", "Landscape Full HD", 1920, 1080, 30, metadata={"aspectRatio": "16:9"}),
    RenderPreset("square_full_hd", "Square Full HD", 1080, 1080, 30, metadata={"aspectRatio": "1:1"}),
)

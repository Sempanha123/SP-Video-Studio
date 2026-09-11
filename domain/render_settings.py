from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class RenderQuality(StrEnum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"


SUPPORTED_RENDER_FPS = {24, 25, 30, 50, 60}


@dataclass(slots=True)
class RenderSettings:
    width: int
    height: int
    fps: int = 30
    encoder: str = "auto"
    quality: str | RenderQuality = RenderQuality.BALANCED
    subtitle_track_id: str = ""
    output_path: str = ""
    pixel_format: str = "yuv420p"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    keep_temp: bool = False
    allow_hardware_fallback: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def quality_code(self) -> str:
        return self.quality.value if isinstance(self.quality, StrEnum) else str(self.quality)

    def validate(self) -> None:
        if self.width < 16 or self.height < 16 or self.width % 2 or self.height % 2:
            raise ValueError("Render resolution must use positive even dimensions.")
        if self.fps not in SUPPORTED_RENDER_FPS:
            raise ValueError("Unsupported render FPS.")
        if self.quality_code not in {item.value for item in RenderQuality}:
            raise ValueError("Unsupported render quality.")
        if self.encoder not in {"auto", "libx264", "h264_nvenc", "h264_qsv", "h264_amf"}:
            raise ValueError("Unsupported video encoder.")
        if not self.pixel_format:
            raise ValueError("Pixel format is required.")
        if self.output_path and Path(self.output_path).suffix.lower() != ".mp4":
            raise ValueError("Phase 15 renders MP4 output.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "encoder": self.encoder,
            "quality": self.quality_code,
            "subtitleTrackId": self.subtitle_track_id,
            "outputPath": self.output_path,
            "pixelFormat": self.pixel_format,
            "audioCodec": self.audio_codec,
            "audioBitrate": self.audio_bitrate,
            "keepTemp": self.keep_temp,
            "allowHardwareFallback": self.allow_hardware_fallback,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RenderSettings":
        return cls(
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            fps=int(data.get("fps", 30)),
            encoder=str(data.get("encoder", "auto")),
            quality=str(data.get("quality", "balanced")),
            subtitle_track_id=str(data.get("subtitleTrackId", "") or ""),
            output_path=str(data.get("outputPath", "") or ""),
            pixel_format=str(data.get("pixelFormat", "yuv420p")),
            audio_codec=str(data.get("audioCodec", "aac")),
            audio_bitrate=str(data.get("audioBitrate", "192k")),
            keep_temp=bool(data.get("keepTemp", False)),
            allow_hardware_fallback=bool(data.get("allowHardwareFallback", True)),
            metadata=dict(data.get("metadata", {}) or {}),
        )

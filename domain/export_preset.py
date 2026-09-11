from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.render_settings import SUPPORTED_RENDER_FPS

EXPORT_PRESET_SCHEMA_VERSION = 1


@dataclass(slots=True)
class ExportPreset:
    name: str
    platform: str
    description: str
    width: int
    height: int
    aspect_ratio: str
    fps: int
    container: str = "mp4"
    video_codec: str = "h264"
    audio_codec: str = "aac"
    quality_profile: str = "balanced"
    subtitle_mode: str = "none"
    recommended_max_duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    builtin: bool = False
    preset_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: int = EXPORT_PRESET_SCHEMA_VERSION

    @property
    def id(self) -> str:
        return self.preset_id

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Export preset name is required.")
        if self.width < 16 or self.height < 16 or self.width > 7680 or self.height > 7680:
            raise ValueError("Export preset resolution is outside the supported range.")
        if self.width % 2 or self.height % 2:
            raise ValueError("Export preset resolution must use even dimensions.")
        if self.fps not in SUPPORTED_RENDER_FPS:
            raise ValueError("Export preset FPS is not supported.")
        if self.container != "mp4":
            raise ValueError("Phase 16 export presets currently support MP4.")
        if self.video_codec != "h264" or self.audio_codec != "aac":
            raise ValueError("Phase 16 export presets currently use H.264/AAC.")
        if self.quality_profile not in {"fast", "balanced", "high"}:
            raise ValueError("Unsupported export quality profile.")
        if self.subtitle_mode not in {"none", "burn", "external_srt", "external_vtt", "external_ass"}:
            raise ValueError("Unsupported subtitle export mode.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "description": self.description,
            "width": self.width,
            "height": self.height,
            "aspectRatio": self.aspect_ratio,
            "fps": self.fps,
            "container": self.container,
            "videoCodec": self.video_codec,
            "audioCodec": self.audio_codec,
            "qualityProfile": self.quality_profile,
            "subtitleMode": self.subtitle_mode,
            "recommendedMaxDurationMs": self.recommended_max_duration_ms,
            "metadata": dict(self.metadata),
            "builtin": self.builtin,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, builtin: bool | None = None) -> "ExportPreset":
        item = cls(
            preset_id=str(data.get("id") or uuid4()),
            name=str(data.get("name") or "Custom Export"),
            platform=str(data.get("platform") or "generic"),
            description=str(data.get("description") or ""),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            aspect_ratio=str(data.get("aspectRatio") or data.get("aspect_ratio") or "16:9"),
            fps=int(data.get("fps", 30)),
            container=str(data.get("container") or "mp4"),
            video_codec=str(data.get("videoCodec") or data.get("video_codec") or "h264"),
            audio_codec=str(data.get("audioCodec") or data.get("audio_codec") or "aac"),
            quality_profile=str(data.get("qualityProfile") or data.get("quality_profile") or "balanced"),
            subtitle_mode=str(data.get("subtitleMode") or data.get("subtitle_mode") or "none"),
            recommended_max_duration_ms=(int(data["recommendedMaxDurationMs"]) if data.get("recommendedMaxDurationMs") not in (None, "") else None),
            metadata=dict(data.get("metadata") or {}),
            builtin=bool(data.get("builtin", False) if builtin is None else builtin),
            schema_version=int(data.get("schemaVersion", EXPORT_PRESET_SCHEMA_VERSION)),
        )
        item.validate()
        return item

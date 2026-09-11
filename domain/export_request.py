from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from domain.render_settings import SUPPORTED_RENDER_FPS


class ExportRequestError(ValueError):
    pass


@dataclass(slots=True)
class ExportRequest:
    project_id: str
    preset_id: str
    width: int
    height: int
    fps: int
    quality: str = "balanced"
    encoder: str = "auto"
    subtitle_mode: str = "none"
    subtitle_track_id: str = ""
    output_folder: str = ""
    filename: str = "video.mp4"
    overwrite_policy: str = "keep_both"
    fit_mode: str = "fill"
    audio_enabled: bool = True
    audio_quality: str = "high"
    keep_temp: bool = False
    remember_for_project: bool = True
    advanced_settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.project_id:
            raise ExportRequestError("Export request requires a project.")
        if self.width < 16 or self.height < 16 or self.width > 7680 or self.height > 7680 or self.width % 2 or self.height % 2:
            raise ExportRequestError("Export resolution must use practical positive even dimensions.")
        if self.fps not in SUPPORTED_RENDER_FPS:
            raise ExportRequestError("Unsupported export FPS.")
        if self.quality not in {"fast", "balanced", "high"}:
            raise ExportRequestError("Unsupported export quality.")
        if self.encoder not in {"auto", "libx264", "h264_nvenc", "h264_qsv", "h264_amf"}:
            raise ExportRequestError("Unsupported export encoder.")
        if self.subtitle_mode not in {"none", "burn", "external_srt", "external_vtt", "external_ass"}:
            raise ExportRequestError("Unsupported subtitle behavior.")
        if self.subtitle_mode != "none" and not self.subtitle_track_id:
            raise ExportRequestError("Select a subtitle track or choose no subtitles.")
        if self.overwrite_policy not in {"keep_both", "replace", "cancel"}:
            raise ExportRequestError("Unsupported file-conflict behavior.")
        if self.fit_mode not in {"fit", "fill", "stretch"}:
            raise ExportRequestError("Unsupported aspect-ratio conversion mode.")
        if self.audio_quality not in {"standard", "high"}:
            raise ExportRequestError("Unsupported audio quality.")
        if not str(self.output_folder).strip():
            raise ExportRequestError("Choose an export folder.")
        if not str(self.filename).strip():
            raise ExportRequestError("Choose an export filename.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "projectId": self.project_id,
            "presetId": self.preset_id,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "quality": self.quality,
            "encoder": self.encoder,
            "subtitleMode": self.subtitle_mode,
            "subtitleTrackId": self.subtitle_track_id,
            "outputFolder": self.output_folder,
            "filename": self.filename,
            "overwritePolicy": self.overwrite_policy,
            "fitMode": self.fit_mode,
            "audioEnabled": self.audio_enabled,
            "audioQuality": self.audio_quality,
            "keepTemp": self.keep_temp,
            "rememberForProject": self.remember_for_project,
            "advancedSettings": dict(self.advanced_settings),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExportRequest":
        item = cls(
            project_id=str(data.get("projectId") or data.get("project_id") or ""),
            preset_id=str(data.get("presetId") or data.get("preset_id") or ""),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            fps=int(data.get("fps", 30)),
            quality=str(data.get("quality") or "balanced"),
            encoder=str(data.get("encoder") or "auto"),
            subtitle_mode=str(data.get("subtitleMode") or data.get("subtitle_mode") or "none"),
            subtitle_track_id=str(data.get("subtitleTrackId") or data.get("subtitle_track_id") or ""),
            output_folder=str(data.get("outputFolder") or data.get("output_folder") or ""),
            filename=str(data.get("filename") or "video.mp4"),
            overwrite_policy=str(data.get("overwritePolicy") or data.get("overwrite_policy") or "keep_both"),
            fit_mode=str(data.get("fitMode") or data.get("fit_mode") or "fill"),
            audio_enabled=bool(data.get("audioEnabled", data.get("audio_enabled", True))),
            audio_quality=str(data.get("audioQuality") or data.get("audio_quality") or "high"),
            keep_temp=bool(data.get("keepTemp", data.get("keep_temp", False))),
            remember_for_project=bool(data.get("rememberForProject", data.get("remember_for_project", True))),
            advanced_settings=dict(data.get("advancedSettings") or data.get("advanced_settings") or {}),
            metadata=dict(data.get("metadata") or {}),
        )
        item.validate()
        return item

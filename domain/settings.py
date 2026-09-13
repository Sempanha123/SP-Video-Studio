from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from domain.accessibility_settings import (
    SUPPORTED_INTERFACE_TEXT_SIZES,
    SUPPORTED_REDUCE_MOTION_MODES,
)

SETTINGS_VERSION = 1
SUPPORTED_SETTING_FPS = (24, 25, 30, 50, 60)
SUPPORTED_SETTING_ASPECT_RATIOS = ("9:16", "16:9", "1:1")


class ThemeMode(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class PerformanceProfile(StrEnum):
    AUTO = "auto"
    LOW_MEMORY = "low_memory"
    BALANCED = "balanced"
    MAXIMUM_QUALITY = "maximum_quality"


class PreferredEncoder(StrEnum):
    AUTO = "auto"


PERFORMANCE_PROFILE_GUIDANCE = {
    PerformanceProfile.AUTO.value: {
        "memory": "adaptive", "concurrency": "adaptive", "caching": "adaptive", "quality": "adaptive"
    },
    PerformanceProfile.LOW_MEMORY.value: {
        "memory": "low", "concurrency": "low", "caching": "low", "quality": "efficient"
    },
    PerformanceProfile.BALANCED.value: {
        "memory": "moderate", "concurrency": "moderate", "caching": "moderate", "quality": "normal"
    },
    PerformanceProfile.MAXIMUM_QUALITY.value: {
        "memory": "high", "concurrency": "moderate", "caching": "high", "quality": "maximum"
    },
}


@dataclass(slots=True)
class AppSettings:
    settings_version: int = SETTINGS_VERSION
    language: str = "en"
    theme: str = ThemeMode.SYSTEM.value
    open_last_project: bool = False
    show_welcome_home: bool = True
    default_projects_folder: str = ""
    performance_profile: str = PerformanceProfile.AUTO.value
    default_fps: int = 30
    default_aspect_ratio: str = "16:9"
    preferred_encoder: str = PreferredEncoder.AUTO.value
    ffmpeg_mode: str = "auto"
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    debug_logging: bool = False
    show_technical_error_details: bool = False
    readiness_check_on_startup: bool = True
    # Phase 33 stores only stable command IDs -> portable key sequences.
    shortcut_overrides: dict[str, str] = field(default_factory=dict)
    # Phase 34 accessibility preferences live in the existing settings document.
    reduce_motion: str = "system"
    interface_text_size: str = "default"
    stronger_focus_indicator: bool = False

    @classmethod
    def defaults(cls, project_root: Path) -> "AppSettings":
        return cls(default_projects_folder=str(Path(project_root).expanduser()))

    def validate(self) -> None:
        if self.settings_version != SETTINGS_VERSION:
            raise ValueError("Unsupported settings version.")
        if self.language not in {"en", "km"}:
            raise ValueError("Unsupported application language.")
        if self.theme not in {item.value for item in ThemeMode}:
            raise ValueError("Unsupported theme setting.")
        if self.performance_profile not in {item.value for item in PerformanceProfile}:
            raise ValueError("Unsupported performance profile.")
        if self.default_fps not in SUPPORTED_SETTING_FPS:
            raise ValueError("Unsupported default FPS.")
        if self.default_aspect_ratio not in SUPPORTED_SETTING_ASPECT_RATIOS:
            raise ValueError("Unsupported default aspect ratio.")
        if self.preferred_encoder != PreferredEncoder.AUTO.value:
            raise ValueError("Unsupported encoder preference.")
        if self.ffmpeg_mode not in {"auto", "custom"}:
            raise ValueError("Unsupported FFmpeg discovery mode.")
        if not self.default_projects_folder.strip():
            raise ValueError("Default projects folder is required.")
        if not isinstance(self.shortcut_overrides, dict):
            raise ValueError("Keyboard shortcut overrides must be a mapping.")
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.shortcut_overrides.items()):
            raise ValueError("Keyboard shortcut overrides must use command IDs and key sequences.")
        if self.reduce_motion not in SUPPORTED_REDUCE_MOTION_MODES:
            raise ValueError("Unsupported Reduce Motion preference.")
        if self.interface_text_size not in SUPPORTED_INTERFACE_TEXT_SIZES:
            raise ValueError("Unsupported interface text size.")

    def with_changes(self, **changes: Any) -> "AppSettings":
        updated = replace(self, **changes)
        updated.validate()
        return updated

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings_version": self.settings_version,
            "general": {
                "language": self.language,
                "open_last_project": self.open_last_project,
                "show_welcome_home": self.show_welcome_home,
            },
            "appearance": {"theme": self.theme},
            "projects": {"default_projects_folder": self.default_projects_folder},
            "performance": {"profile": self.performance_profile},
            "rendering": {
                "default_fps": self.default_fps,
                "default_aspect_ratio": self.default_aspect_ratio,
                "preferred_encoder": self.preferred_encoder,
            },
            "media_tools": {
                "ffmpeg_mode": self.ffmpeg_mode,
                "ffmpeg_path": self.ffmpeg_path,
                "ffprobe_path": self.ffprobe_path,
            },
            "advanced": {
                "debug_logging": self.debug_logging,
                "show_technical_error_details": self.show_technical_error_details,
                "readiness_check_on_startup": self.readiness_check_on_startup,
            },
            "keyboard_shortcuts": {
                "overrides": dict(self.shortcut_overrides),
            },
            "accessibility": {
                "reduce_motion": self.reduce_motion,
                "interface_text_size": self.interface_text_size,
                "stronger_focus_indicator": self.stronger_focus_indicator,
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], default_project_root: Path) -> "AppSettings":
        general = _mapping(payload.get("general"))
        appearance = _mapping(payload.get("appearance"))
        projects = _mapping(payload.get("projects"))
        performance = _mapping(payload.get("performance"))
        rendering = _mapping(payload.get("rendering"))
        media_tools = _mapping(payload.get("media_tools"))
        advanced = _mapping(payload.get("advanced"))
        keyboard_shortcuts = _mapping(payload.get("keyboard_shortcuts"))
        accessibility = _mapping(payload.get("accessibility"))
        raw_overrides = _mapping(keyboard_shortcuts.get("overrides"))
        settings = cls(
            settings_version=int(payload.get("settings_version", SETTINGS_VERSION)),
            language=str(general.get("language", "en")),
            theme=str(appearance.get("theme", ThemeMode.SYSTEM.value)),
            open_last_project=bool(general.get("open_last_project", False)),
            show_welcome_home=bool(general.get("show_welcome_home", True)),
            default_projects_folder=str(
                projects.get("default_projects_folder", str(default_project_root))
            ),
            performance_profile=str(
                performance.get("profile", PerformanceProfile.AUTO.value)
            ),
            default_fps=int(rendering.get("default_fps", 30)),
            default_aspect_ratio=str(rendering.get("default_aspect_ratio", "16:9")),
            preferred_encoder=str(rendering.get("preferred_encoder", "auto")),
            ffmpeg_mode=str(media_tools.get("ffmpeg_mode", "auto")),
            ffmpeg_path=str(media_tools.get("ffmpeg_path", "")),
            ffprobe_path=str(media_tools.get("ffprobe_path", "")),
            debug_logging=bool(advanced.get("debug_logging", False)),
            show_technical_error_details=bool(
                advanced.get("show_technical_error_details", False)
            ),
            readiness_check_on_startup=bool(
                advanced.get("readiness_check_on_startup", True)
            ),
            shortcut_overrides={
                str(key): str(value)
                for key, value in raw_overrides.items()
                if str(key).strip()
            },
            reduce_motion=str(accessibility.get("reduce_motion", "system")),
            interface_text_size=str(accessibility.get("interface_text_size", "default")),
            stronger_focus_indicator=bool(accessibility.get("stronger_focus_indicator", False)),
        )
        settings.validate()
        return settings


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}

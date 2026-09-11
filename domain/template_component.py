from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
import re

_LOCAL_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,79}$")


class TemplateComponentType(StrEnum):
    PROJECT_SETTINGS = "project_settings"
    SCENE_STRUCTURE = "scene_structure"
    SCENE_LAYOUT = "scene_layout"
    VISUAL_THEME = "visual_theme"
    SUBTITLE_STYLE = "subtitle_style"
    TRANSITION_STYLE = "transition_style"
    SPEAKER_STRUCTURE = "speaker_structure"
    SPEECH_BLOCK_STRUCTURE = "speech_block_structure"
    TIMELINE_TRACKS = "timeline_tracks"
    EXPORT_RECOMMENDATION = "export_recommendation"
    NEWS_VISUAL_THEME = "news_visual_theme"
    STORY_STRUCTURE = "story_structure"
    SHORT_STYLE = "short_style"


@dataclass(slots=True)
class TemplateComponent:
    local_id: str
    component_type: str | TemplateComponentType
    data: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def type_code(self) -> str:
        return self.component_type.value if isinstance(self.component_type, StrEnum) else str(self.component_type)

    def validate(self) -> None:
        if not _LOCAL_ID_RE.fullmatch(self.local_id):
            raise ValueError("Template component local ID is invalid.")
        if self.type_code not in {item.value for item in TemplateComponentType}:
            raise ValueError(f"Unsupported template component type: {self.type_code}")
        if not isinstance(self.data, dict):
            raise ValueError("Template component data must be an object.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"localId":self.local_id,"type":self.type_code,"enabled":self.enabled,"data":dict(self.data),"metadata":dict(self.metadata)}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "TemplateComponent":
        item=cls(str(raw.get("localId") or raw.get("local_id") or ""),str(raw.get("type") or raw.get("component_type") or ""),dict(raw.get("data") or {}),bool(raw.get("enabled",True)),dict(raw.get("metadata") or {}))
        item.validate(); return item

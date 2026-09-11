from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso

@dataclass(slots=True)
class NewsVisualTheme:
    project_id: str
    name: str = "Clean News"
    primary_color: str = "#18212B"
    secondary_color: str = "#253241"
    accent_color: str = "#D8A84E"
    background_color: str = "#0F141A"
    surface_color: str = "#D9161D24"
    text_primary: str = "#FFFFFFFF"
    text_secondary: str = "#D9E2ECFF"
    font_heading: str = "Noto Sans Khmer"
    font_body: str = "Noto Sans Khmer"
    font_numbers: str = "Noto Sans Khmer"
    corner_radius: float = 10.0
    spacing_scale: float = 1.0
    logo_media_id: str = ""
    default_animation_style: str = "none"
    theme_id: str = field(default_factory=lambda: str(uuid4()))
    preset_id: str = "clean_news"
    active: bool = True
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str: return self.theme_id
    def validate(self) -> None:
        if not self.project_id: raise ValueError("News visual theme requires a project.")
        if not self.name.strip(): raise ValueError("Theme name is required.")
        for value in (self.primary_color,self.secondary_color,self.accent_color,self.background_color,self.surface_color,self.text_primary,self.text_secondary):
            if not isinstance(value,str) or not value.startswith("#") or len(value) not in {7,9}: raise ValueError("Theme colors must use #RRGGBB or #RRGGBBAA.")
        self.corner_radius=max(0.0,min(64.0,float(self.corner_radius))); self.spacing_scale=max(.5,min(2.0,float(self.spacing_scale)))
    def to_dict(self)->dict[str,Any]:
        return {"id":self.id,"projectId":self.project_id,"name":self.name,"presetId":self.preset_id,"active":self.active,"primaryColor":self.primary_color,"secondaryColor":self.secondary_color,"accentColor":self.accent_color,"backgroundColor":self.background_color,"surfaceColor":self.surface_color,"textPrimary":self.text_primary,"textSecondary":self.text_secondary,"fontHeading":self.font_heading,"fontBody":self.font_body,"fontNumbers":self.font_numbers,"cornerRadius":self.corner_radius,"spacingScale":self.spacing_scale,"logoMediaId":self.logo_media_id,"defaultAnimationStyle":self.default_animation_style,"createdAt":self.created_at,"updatedAt":self.updated_at,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->"NewsVisualTheme":
        return cls(project_id=str(row["project_id"]),name=str(row["name"]),primary_color=str(row["primary_color"]),secondary_color=str(row["secondary_color"]),accent_color=str(row["accent_color"]),background_color=str(row["background_color"]),surface_color=str(row["surface_color"]),text_primary=str(row["text_primary"]),text_secondary=str(row["text_secondary"]),font_heading=str(row["font_heading"]),font_body=str(row["font_body"]),font_numbers=str(row["font_numbers"]),corner_radius=float(row["corner_radius"]),spacing_scale=float(row["spacing_scale"]),logo_media_id=str(row["logo_media_id"] or ""),default_animation_style=str(row["default_animation_style"] or "none"),theme_id=str(row["id"]),preset_id=str(row["preset_id"] or "clean_news"),active=bool(row["active"]),created_at=str(row["created_at"]),updated_at=str(row["updated_at"]),metadata=json.loads(str(row["metadata_json"] or "{}")))

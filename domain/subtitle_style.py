from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso

_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")


@dataclass(slots=True)
class SubtitleStyle:
    project_id: str
    name: str = "Clean"
    font_family: str = "Noto Sans Khmer"
    font_size: float = 48.0
    font_weight: int = 600
    italic: bool = False
    text_color: str = "#FFFFFF"
    secondary_text_color: str = "#E5E7EB"
    outline_color: str = "#000000"
    outline_width: float = 2.0
    shadow_enabled: bool = True
    shadow_offset: float = 2.0
    background_enabled: bool = False
    background_color: str = "#000000"
    background_opacity: float = 0.55
    alignment: str = "center"
    vertical_position: str = "bottom"
    horizontal_margin: float = 0.06
    vertical_margin: float = 0.08
    max_lines: int = 2
    max_chars_per_line: int = 42
    line_spacing: float = 1.0
    highlight_color: str = "#FDE047"
    highlight_text_color: str = "#111827"
    secondary_scale: float = 0.82
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    style_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.style_id

    def validate(self) -> None:
        if not self.style_id or not self.project_id or not self.name.strip():
            raise ValueError("Subtitle style identity, project and name are required.")
        if self.font_size <= 0 or not 100 <= self.font_weight <= 900:
            raise ValueError("Subtitle font settings are invalid.")
        for value in (self.text_color, self.secondary_text_color, self.outline_color, self.background_color,
                      self.highlight_color, self.highlight_text_color):
            if not _COLOR_RE.match(value):
                raise ValueError("Subtitle colors must use #RRGGBB or #RRGGBBAA.")
        if self.alignment not in {"left", "center", "right"} or self.vertical_position not in {"top", "middle", "bottom"}:
            raise ValueError("Subtitle alignment or position is invalid.")
        if not 0 <= self.background_opacity <= 1 or self.max_lines < 1 or self.max_chars_per_line < 8:
            raise ValueError("Subtitle style limits are invalid.")
        if not 0 <= self.horizontal_margin < 0.5 or not 0 <= self.vertical_margin < 0.5:
            raise ValueError("Subtitle margins are outside the normalized canvas.")
        if self.secondary_scale <= 0:
            raise ValueError("Secondary subtitle scale must be positive.")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["id"] = data.pop("style_id")
        return data

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "SubtitleStyle":
        try:
            metadata = json.loads(record["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            style_id=str(record["id"]), project_id=str(record["project_id"]), name=str(record["name"]),
            font_family=str(record["font_family"]), font_size=float(record["font_size"]), font_weight=int(record["font_weight"]),
            italic=bool(record["italic"]), text_color=str(record["text_color"]), secondary_text_color=str(record["secondary_text_color"]),
            outline_color=str(record["outline_color"]), outline_width=float(record["outline_width"]), shadow_enabled=bool(record["shadow_enabled"]),
            shadow_offset=float(record["shadow_offset"]), background_enabled=bool(record["background_enabled"]), background_color=str(record["background_color"]),
            background_opacity=float(record["background_opacity"]), alignment=str(record["alignment"]), vertical_position=str(record["vertical_position"]),
            horizontal_margin=float(record["horizontal_margin"]), vertical_margin=float(record["vertical_margin"]), max_lines=int(record["max_lines"]),
            max_chars_per_line=int(record["max_chars_per_line"]), line_spacing=float(record["line_spacing"]), highlight_color=str(record["highlight_color"]),
            highlight_text_color=str(record["highlight_text_color"]), secondary_scale=float(record["secondary_scale"]),
            metadata=metadata if isinstance(metadata, dict) else {}, created_at=str(record["created_at"]), updated_at=str(record["updated_at"]),
        )

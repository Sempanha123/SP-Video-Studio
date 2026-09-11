from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4


class SceneOverlayType(StrEnum):
    HEADLINE = "headline"
    BODY_TEXT = "body_text"
    LOWER_THIRD = "lower_third"
    LABEL = "label"
    LOGO = "logo"


DEFAULT_TEXT_STYLE = {"fontFamily":"Noto Sans","fontSize":48.0,"fontWeight":600,"color":"#FFFFFFFF","alignment":"center"}


@dataclass(slots=True)
class SceneOverlay:
    scene_id: str
    order: int
    overlay_type: str | SceneOverlayType
    text: str = ""
    secondary_text: str = ""
    asset_id: str = ""
    x: float = 0.1
    y: float = 0.1
    width: float = 0.8
    height: float = 0.2
    opacity: float = 1.0
    rotation: float = 0.0
    visible: bool = True
    start_offset_ms: int = 0
    end_offset_ms: int | None = None
    overlay_id: str = field(default_factory=lambda: str(uuid4()))
    style: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_TEXT_STYLE))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str: return self.overlay_id
    @property
    def type_code(self) -> str: return self.overlay_type.value if isinstance(self.overlay_type, StrEnum) else str(self.overlay_type)

    def validate(self, scene_duration_ms: int | None = None) -> None:
        if not self.scene_id: raise ValueError("Scene overlay requires a scene.")
        if self.order < 0: raise ValueError("Overlay order cannot be negative.")
        if self.type_code not in {item.value for item in SceneOverlayType}: raise ValueError("Unsupported overlay type.")
        for name, value in (("x",self.x),("y",self.y),("width",self.width),("height",self.height)):
            if not 0.0 <= float(value) <= 1.0: raise ValueError(f"Overlay {name} must use normalized coordinates.")
        if self.width <= 0 or self.height <= 0: raise ValueError("Overlay size must be positive.")
        self.opacity=max(0.0,min(1.0,float(self.opacity)))
        if self.start_offset_ms < 0: raise ValueError("Overlay start cannot be negative.")
        if self.end_offset_ms is not None:
            if self.end_offset_ms <= self.start_offset_ms: raise ValueError("Overlay end must be after start.")
            if scene_duration_ms is not None and self.end_offset_ms > scene_duration_ms: raise ValueError("Overlay timing exceeds scene duration.")
        if scene_duration_ms is not None and self.start_offset_ms >= scene_duration_ms: raise ValueError("Overlay starts after the scene ends.")

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"sceneId":self.scene_id,"order":self.order,"type":self.type_code,"text":self.text,"secondaryText":self.secondary_text,"assetId":self.asset_id,"x":self.x,"y":self.y,"width":self.width,"height":self.height,"opacity":self.opacity,"rotation":self.rotation,"visible":self.visible,"startOffsetMs":self.start_offset_ms,"endOffsetMs":self.end_offset_ms if self.end_offset_ms is not None else -1,"style":dict(self.style),"metadata":dict(self.metadata)}

    @classmethod
    def from_record(cls, r: Mapping[str, Any]) -> "SceneOverlay":
        def decode(name:str):
            try: value=json.loads(r[name] or "{}")
            except Exception: value={}
            return value if isinstance(value,dict) else {}
        return cls(scene_id=str(r["scene_id"]),order=int(r["overlay_order"]),overlay_type=str(r["overlay_type"]),text=str(r["text"] or ""),secondary_text=str(r["secondary_text"] or ""),asset_id=str(r["asset_id"] or ""),x=float(r["x"]),y=float(r["y"]),width=float(r["width"]),height=float(r["height"]),opacity=float(r["opacity"]),rotation=float(r["rotation"]),visible=bool(r["visible"]),start_offset_ms=int(r["start_offset_ms"]),end_offset_ms=int(r["end_offset_ms"]) if r["end_offset_ms"] is not None else None,overlay_id=str(r["id"]),style=decode("style_json"),metadata=decode("metadata_json"))

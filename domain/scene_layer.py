from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4


class SceneLayerType(StrEnum):
    MEDIA = "media"
    TEXT = "text"
    LOGO = "logo"


@dataclass(slots=True)
class SceneLayer:
    scene_id: str
    order: int
    layer_type: str | SceneLayerType
    asset_id: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    opacity: float = 1.0
    rotation: float = 0.0
    visible: bool = True
    layer_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str: return self.layer_id
    @property
    def type_code(self) -> str: return self.layer_type.value if isinstance(self.layer_type, StrEnum) else str(self.layer_type)

    def validate(self) -> None:
        if not self.scene_id: raise ValueError("Scene layer requires a scene.")
        if self.order < 0: raise ValueError("Layer order cannot be negative.")
        if self.type_code not in {item.value for item in SceneLayerType}: raise ValueError("Unsupported scene layer type.")
        for name, value in (("x", self.x), ("y", self.y), ("width", self.width), ("height", self.height)):
            if not 0.0 <= float(value) <= 1.0: raise ValueError(f"Layer {name} must use normalized coordinates.")
        if self.width <= 0 or self.height <= 0: raise ValueError("Layer size must be positive.")
        self.opacity = max(0.0, min(1.0, float(self.opacity)))

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"id":self.id,"sceneId":self.scene_id,"order":self.order,"type":self.type_code,"assetId":self.asset_id,"x":self.x,"y":self.y,"width":self.width,"height":self.height,"opacity":self.opacity,"rotation":self.rotation,"visible":self.visible,"metadata":dict(self.metadata)}

    @classmethod
    def from_record(cls, r: Mapping[str, Any]) -> "SceneLayer":
        try: meta=json.loads(r["metadata_json"] or "{}")
        except Exception: meta={}
        return cls(scene_id=str(r["scene_id"]),order=int(r["layer_order"]),layer_type=str(r["layer_type"]),asset_id=str(r["asset_id"] or ""),x=float(r["x"]),y=float(r["y"]),width=float(r["width"]),height=float(r["height"]),opacity=float(r["opacity"]),rotation=float(r["rotation"]),visible=bool(r["visible"]),layer_id=str(r["id"]),metadata=meta if isinstance(meta,dict) else {})

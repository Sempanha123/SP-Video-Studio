from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.chroma_key import ChromaKeySettings
from domain.phase22_errors import VisualLayerInvalid


class SceneLayerType(StrEnum):
    MEDIA = "media"
    TEXT = "text"
    LOGO = "logo"


class VisualLayerRole(StrEnum):
    PRIMARY = "primary"
    BROLL = "broll"
    OVERLAY_VIDEO = "overlay_video"
    PRESENTER = "presenter"
    REPORTER = "reporter"
    INTERVIEW_GUEST = "interview_guest"
    HOST = "host"
    CHARACTER = "character"
    IMAGE_OVERLAY = "image_overlay"
    CUSTOM = "custom"


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
    def type_code(self) -> str:
        return self.layer_type.value if isinstance(self.layer_type, StrEnum) else str(self.layer_type)

    @property
    def role(self) -> str:
        return str(self.metadata.get("role", VisualLayerRole.CUSTOM.value))

    @property
    def z_order(self) -> int:
        return int(self.metadata.get("zOrder", self.order) or 0)

    @property
    def start_ms(self) -> int:
        return max(0, int(self.metadata.get("startMs", 0) or 0))

    @property
    def duration_ms(self) -> int:
        return max(0, int(self.metadata.get("durationMs", 0) or 0))

    @property
    def source_in_ms(self) -> int:
        return max(0, int(self.metadata.get("sourceInMs", 0) or 0))

    @property
    def source_out_ms(self) -> int | None:
        raw = self.metadata.get("sourceOutMs")
        return None if raw in (None, "", -1) else max(0, int(raw))

    @property
    def fit_mode(self) -> str:
        return str(self.metadata.get("fitMode", "contain"))

    @property
    def crop(self) -> dict[str, float]:
        raw = dict(self.metadata.get("crop") or {})
        return {key: max(0.0, min(0.95, float(raw.get(key, 0.0) or 0.0))) for key in ("left", "top", "right", "bottom")}

    @property
    def chroma_key(self) -> ChromaKeySettings:
        return ChromaKeySettings.from_dict(self.metadata.get("chromaKey") or {})

    def validate(self) -> None:
        if not self.scene_id:
            raise VisualLayerInvalid("Scene layer requires a scene.")
        if self.order < 0:
            raise VisualLayerInvalid("Layer order cannot be negative.")
        if self.type_code not in {item.value for item in SceneLayerType}:
            raise VisualLayerInvalid("Unsupported scene layer type.")
        for name, value in (("x", self.x), ("y", self.y), ("width", self.width), ("height", self.height)):
            if not 0.0 <= float(value) <= 1.0:
                raise VisualLayerInvalid(f"Layer {name} must use normalized coordinates.")
        if self.width <= 0 or self.height <= 0:
            raise VisualLayerInvalid("Layer size must be positive.")
        crop = self.crop
        if crop["left"] + crop["right"] >= 1 or crop["top"] + crop["bottom"] >= 1:
            raise VisualLayerInvalid("Layer crop removes the whole image.")
        if self.source_out_ms is not None and self.source_out_ms <= self.source_in_ms:
            raise VisualLayerInvalid("Layer source-out must be after source-in.")
        self.opacity = max(0.0, min(1.0, float(self.opacity)))
        self.chroma_key.validate()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        crop = self.crop
        chroma = self.chroma_key.to_dict()
        return {
            "id": self.id, "sceneId": self.scene_id, "order": self.order, "type": self.type_code,
            "assetId": self.asset_id, "x": self.x, "y": self.y, "width": self.width, "height": self.height,
            "opacity": self.opacity, "rotation": self.rotation, "visible": self.visible,
            "role": self.role, "zOrder": self.z_order, "startMs": self.start_ms, "durationMs": self.duration_ms,
            "sourceInMs": self.source_in_ms, "sourceOutMs": self.source_out_ms, "fitMode": self.fit_mode,
            "cropLeft": crop["left"], "cropTop": crop["top"], "cropRight": crop["right"], "cropBottom": crop["bottom"],
            "flipHorizontal": bool(self.metadata.get("flipHorizontal", False)),
            "flipVertical": bool(self.metadata.get("flipVertical", False)),
            "aspectLocked": bool(self.metadata.get("aspectLocked", True)),
            "locked": bool(self.metadata.get("locked", False)),
            "speakerId": str(self.metadata.get("speakerId", "")),
            "useAudio": bool(self.metadata.get("useAudio", False)),
            "audioVolume": max(0.0, min(1.0, float(self.metadata.get("audioVolume", 1.0) or 0.0))),
            "fadeInMs": max(0, int(self.metadata.get("fadeInMs", 0) or 0)),
            "fadeOutMs": max(0, int(self.metadata.get("fadeOutMs", 0) or 0)),
            "chromaKey": chroma,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, r: Mapping[str, Any]) -> "SceneLayer":
        try: meta = json.loads(r["metadata_json"] or "{}")
        except Exception: meta = {}
        return cls(
            scene_id=str(r["scene_id"]), order=int(r["layer_order"]), layer_type=str(r["layer_type"]),
            asset_id=str(r["asset_id"] or ""), x=float(r["x"]), y=float(r["y"]), width=float(r["width"]),
            height=float(r["height"]), opacity=float(r["opacity"]), rotation=float(r["rotation"]),
            visible=bool(r["visible"]), layer_id=str(r["id"]), metadata=meta if isinstance(meta, dict) else {},
        )

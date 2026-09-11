from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from domain.chroma_key import ChromaKeySettings, PRESET_KEY_COLORS
from domain.phase22_errors import VisualLayerInvalid
from domain.scene_layer import SceneLayer, SceneLayerType, VisualLayerRole
from storage.repositories.media_repository import MediaRepository
from storage.repositories.scene_repository import SceneRepository


PIP_PRESETS: dict[str, tuple[float, float, float, float]] = {
    "top_left": (0.04, 0.04, 0.30, 0.30),
    "top_right": (0.66, 0.04, 0.30, 0.30),
    "bottom_left": (0.04, 0.66, 0.30, 0.30),
    "bottom_right": (0.66, 0.66, 0.30, 0.30),
    "center": (0.30, 0.25, 0.40, 0.50),
}

SPLIT_PRESETS: dict[str, tuple[tuple[float,float,float,float], tuple[float,float,float,float]]] = {
    "left_right": ((0.0,0.0,0.5,1.0),(0.5,0.0,0.5,1.0)),
    "top_bottom": ((0.0,0.0,1.0,0.5),(0.0,0.5,1.0,0.5)),
}


class VisualLayerService:
    def __init__(self, scenes: SceneRepository, media: MediaRepository) -> None:
        self.scenes = scenes
        self.media = media

    def list_layers(self, project_id: str, scene_id: str) -> list[SceneLayer]:
        self._scene(project_id, scene_id)
        return sorted(self.scenes.layers(scene_id), key=lambda item: (item.z_order, item.order, item.id))

    def add_media_layer(
        self, project_id: str, scene_id: str, media_id: str, *, role: str = VisualLayerRole.OVERLAY_VIDEO.value,
        start_ms: int = 0, duration_ms: int | None = None, source_in_ms: int = 0,
        pip_preset: str | None = None, speaker_id: str = "",
    ) -> SceneLayer:
        scene = self._scene(project_id, scene_id)
        asset = self.media.get_by_id(media_id)
        if asset is None or asset.project_id != project_id or asset.type not in {"video", "image"}:
            raise VisualLayerInvalid("Choose a project video or image for this visual layer.")
        layers = self.scenes.layers(scene_id)
        order = len(layers)
        x,y,w,h = PIP_PRESETS.get(pip_preset or "", (0.0,0.0,1.0,1.0))
        resolved_duration = int(duration_ms or min(scene.duration_ms, asset.duration_ms or scene.duration_ms))
        use_audio = bool(asset.type == "video" and role in {"interview_guest", "host"})
        item = SceneLayer(
            scene_id=scene_id, order=order, layer_type=SceneLayerType.MEDIA, asset_id=asset.id,
            x=x, y=y, width=w, height=h,
            metadata={
                "role": role, "zOrder": order + 1, "startMs": max(0,int(start_ms)),
                "durationMs": max(1,resolved_duration), "sourceInMs": max(0,int(source_in_ms)),
                "sourceOutMs": None, "fitMode": "contain" if pip_preset else "fill",
                "crop": {"left":0.0,"top":0.0,"right":0.0,"bottom":0.0},
                "chromaKey": ChromaKeySettings().to_dict(), "aspectLocked": True,
                "speakerId": speaker_id, "useAudio": use_audio, "audioVolume": 1.0,
                "flipHorizontal": False, "flipVertical": False, "locked": False,
            },
        )
        item.validate(); layers.append(item); self._replace(project_id, scene_id, layers); return item

    def update_layer(self, project_id: str, scene_id: str, layer_id: str, updates: dict[str, object]) -> SceneLayer:
        layers = self.scenes.layers(scene_id); item = next((x for x in layers if x.id == layer_id), None)
        if item is None:
            raise VisualLayerInvalid("Visual layer could not be found.")
        aliases = {"zOrder":"zOrder","startMs":"startMs","durationMs":"durationMs","sourceInMs":"sourceInMs",
                   "sourceOutMs":"sourceOutMs","fitMode":"fitMode","speakerId":"speakerId","useAudio":"useAudio",
                   "audioVolume":"audioVolume","flipHorizontal":"flipHorizontal","flipVertical":"flipVertical",
                   "aspectLocked":"aspectLocked","fadeInMs":"fadeInMs","fadeOutMs":"fadeOutMs","locked":"locked"}
        for key, value in updates.items():
            if key in {"x","y","width","height","opacity","rotation","visible"}:
                setattr(item, key, value)
            elif key in aliases:
                item.metadata[aliases[key]] = value
            elif key in {"cropLeft","cropTop","cropRight","cropBottom"}:
                crop = dict(item.metadata.get("crop") or {})
                crop[key[4:].lower()] = float(value)
                item.metadata["crop"] = crop
            elif key == "role":
                item.metadata["role"] = str(value)
        item.validate(); self._replace(project_id, scene_id, layers); return item

    def reset_transform(self, project_id: str, scene_id: str, layer_id: str) -> SceneLayer:
        return self.update_layer(project_id, scene_id, layer_id, {
            "x":0.0,"y":0.0,"width":1.0,"height":1.0,"opacity":1.0,"rotation":0.0,
            "cropLeft":0.0,"cropTop":0.0,"cropRight":0.0,"cropBottom":0.0,
            "flipHorizontal":False,"flipVertical":False,
        })

    def set_chroma_key(self, project_id: str, scene_id: str, layer_id: str, settings: ChromaKeySettings) -> SceneLayer:
        settings.validate(); layers=self.scenes.layers(scene_id); item=next((x for x in layers if x.id==layer_id),None)
        if item is None: raise VisualLayerInvalid("Visual layer could not be found.")
        item.metadata["chromaKey"] = settings.to_dict(); item.validate(); self._replace(project_id,scene_id,layers); return item

    def apply_chroma_preset(self, project_id: str, scene_id: str, layer_id: str, preset: str) -> SceneLayer:
        color = PRESET_KEY_COLORS.get(preset.lower())
        if not color: raise VisualLayerInvalid("Unknown chroma-key preset.")
        return self.set_chroma_key(project_id,scene_id,layer_id,ChromaKeySettings(enabled=True,key_color=color))

    def apply_pip(self, project_id: str, scene_id: str, layer_id: str, preset: str) -> SceneLayer:
        try: x,y,w,h=PIP_PRESETS[preset]
        except KeyError as exc: raise VisualLayerInvalid("Unknown picture-in-picture preset.") from exc
        return self.update_layer(project_id,scene_id,layer_id,{"x":x,"y":y,"width":w,"height":h,"fitMode":"contain"})

    def apply_split_screen(self, project_id: str, scene_id: str, first_id: str, second_id: str, preset: str="left_right") -> tuple[SceneLayer,SceneLayer]:
        try: first_rect,second_rect=SPLIT_PRESETS[preset]
        except KeyError as exc: raise VisualLayerInvalid("Unknown split-screen preset.") from exc
        a=self.update_layer(project_id,scene_id,first_id,{"x":first_rect[0],"y":first_rect[1],"width":first_rect[2],"height":first_rect[3],"fitMode":"fill"})
        b=self.update_layer(project_id,scene_id,second_id,{"x":second_rect[0],"y":second_rect[1],"width":second_rect[2],"height":second_rect[3],"fitMode":"fill"})
        return a,b

    def move_z(self, project_id: str, scene_id: str, layer_id: str, delta: int) -> list[SceneLayer]:
        layers=sorted(self.scenes.layers(scene_id),key=lambda x:(x.z_order,x.order)); idx=next((i for i,x in enumerate(layers) if x.id==layer_id),None)
        if idx is None: raise VisualLayerInvalid("Visual layer could not be found.")
        target=max(0,min(idx+int(delta),len(layers)-1)); item=layers.pop(idx); layers.insert(target,item)
        for order,layer in enumerate(layers): layer.order=order; layer.metadata["zOrder"]=order
        self._replace(project_id,scene_id,layers); return layers

    def duplicate_layer(self, project_id: str, scene_id: str, layer_id: str) -> SceneLayer:
        layers=self.scenes.layers(scene_id); source=next((x for x in layers if x.id==layer_id),None)
        if source is None: raise VisualLayerInvalid("Visual layer could not be found.")
        clone=deepcopy(source); clone.layer_id=str(uuid4()); clone.order=len(layers); clone.metadata["zOrder"]=clone.order
        layers.append(clone); self._replace(project_id,scene_id,layers); return clone

    def delete_layer(self, project_id: str, scene_id: str, layer_id: str) -> None:
        # Only the relationship is removed. MediaAsset remains project-owned and untouched.
        layers=[x for x in self.scenes.layers(scene_id) if x.id!=layer_id]
        if len(layers)==len(self.scenes.layers(scene_id)): raise VisualLayerInvalid("Visual layer could not be found.")
        for order,layer in enumerate(layers): layer.order=order; layer.metadata["zOrder"]=order
        self._replace(project_id,scene_id,layers)

    def _replace(self, project_id: str, scene_id: str, layers: list[SceneLayer]) -> None:
        self._scene(project_id,scene_id); self.scenes.replace_layers(project_id,scene_id,layers)

    def _scene(self, project_id: str, scene_id: str):
        scene=self.scenes.get(scene_id)
        if scene is None or scene.project_id!=project_id: raise VisualLayerInvalid("Scene could not be found in this project.")
        return scene

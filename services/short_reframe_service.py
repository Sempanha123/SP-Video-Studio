from __future__ import annotations

from domain.shorts_errors import ShortReframeInvalid
from storage.repositories.scene_repository import SceneRepository


REFRAME_PRESETS: dict[str, tuple[float,float]] = {
    "center": (0.0,0.0),
    "left": (-1.0,0.0),
    "right": (1.0,0.0),
    "top": (0.0,-1.0),
    "bottom": (0.0,1.0),
}


class ShortReframeService:
    """Stores manual reframe settings on canonical Scene metadata.

    The renderer consumes the same crop/fit vocabulary used by Phase22 visual transforms.
    No source pixels are modified.
    """
    def __init__(self, scenes: SceneRepository) -> None:
        self.scenes=scenes

    def get(self, project_id: str, scene_id: str) -> dict[str, object]:
        scene=self._scene(project_id,scene_id)
        value=dict(scene.metadata.get("shortReframe") or {})
        return self._normalize(value)

    def set(self, project_id: str, scene_id: str, *, scale: float=1.0, offset_x: float=0.0, offset_y: float=0.0,
            fit_mode: str="fill", crop_left: float=0.0, crop_top: float=0.0, crop_right: float=0.0, crop_bottom: float=0.0,
            background: str="solid") -> dict[str, object]:
        scene=self._scene(project_id,scene_id)
        value=self._normalize({"scale":scale,"offsetX":offset_x,"offsetY":offset_y,"fitMode":fit_mode,
                               "cropLeft":crop_left,"cropTop":crop_top,"cropRight":crop_right,"cropBottom":crop_bottom,
                               "background":background})
        scene.metadata["shortReframe"]=value; self.scenes.update(scene); return value

    def apply_preset(self, project_id: str, scene_id: str, preset: str, *, scale: float=1.0) -> dict[str, object]:
        try: x,y=REFRAME_PRESETS[str(preset).lower()]
        except KeyError as exc: raise ShortReframeInvalid("Unknown reframe preset.") from exc
        current=self.get(project_id,scene_id)
        return self.set(project_id,scene_id,scale=scale,offset_x=x,offset_y=y,fit_mode=str(current.get("fitMode","fill")),
                        crop_left=float(current.get("cropLeft",0)),crop_top=float(current.get("cropTop",0)),
                        crop_right=float(current.get("cropRight",0)),crop_bottom=float(current.get("cropBottom",0)),
                        background=str(current.get("background","solid")))

    def reset(self, project_id: str, scene_id: str) -> dict[str, object]:
        return self.set(project_id,scene_id)

    @staticmethod
    def _normalize(value: dict[str, object]) -> dict[str, object]:
        scale=float(value.get("scale",1.0) or 1.0); ox=float(value.get("offsetX",0.0) or 0.0); oy=float(value.get("offsetY",0.0) or 0.0)
        fit=str(value.get("fitMode","fill") or "fill"); background=str(value.get("background","solid") or "solid")
        if not .1<=scale<=8.0: raise ShortReframeInvalid("Reframe scale must be between 0.1x and 8x.")
        if not -1.0<=ox<=1.0 or not -1.0<=oy<=1.0: raise ShortReframeInvalid("Reframe pan must remain inside the source bounds.")
        if fit not in {"fill","fit","stretch"}: raise ShortReframeInvalid("Unsupported reframe fit mode.")
        if background not in {"solid","fit"}: raise ShortReframeInvalid("Unsupported Short background fill mode.")
        crop={k:max(0.0,min(.95,float(value.get(k,0.0) or 0.0))) for k in ("cropLeft","cropTop","cropRight","cropBottom")}
        if crop["cropLeft"]+crop["cropRight"]>=.98 or crop["cropTop"]+crop["cropBottom"]>=.98: raise ShortReframeInvalid("Crop removes the whole source image.")
        return {"scale":scale,"offsetX":ox,"offsetY":oy,"fitMode":fit,"background":background,**crop}

    def _scene(self, project_id: str, scene_id: str):
        scene=self.scenes.get(scene_id)
        if scene is None or scene.project_id!=project_id: raise ShortReframeInvalid("Short scene could not be found.")
        return scene

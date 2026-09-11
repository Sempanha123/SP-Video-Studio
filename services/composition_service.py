from __future__ import annotations

from pathlib import Path

from domain.phase22_errors import ChromaKeyUnavailable, CompositionError


class CompositionService:
    """Enriches the existing Scene render spec; does not create another render plan."""
    def __init__(self, scene_service, media_repository, phase22_repository=None) -> None:
        self.scenes=scene_service; self.media=media_repository; self.phase22=phase22_repository

    def build_scene_spec(self, project_id: str, scene_id: str) -> dict[str, object]:
        return self.enrich_spec(project_id, self.scenes.build_scene_render_spec(project_id,scene_id))

    def enrich_spec(self, project_id: str, spec: dict[str, object]) -> dict[str, object]:
        scene_id=str(spec.get("sceneId","") or "")
        enriched=[]
        for raw in list(spec.get("layers",[]) or []):
            item=dict(raw); asset_id=str(item.get("assetId","") or "")
            asset=self.media.get_by_id(asset_id) if asset_id else None
            if asset is None or asset.project_id!=project_id:
                item["missingMedia"]=bool(asset_id); item["assetPath"]=""; enriched.append(item); continue
            item.update({"assetPath":asset.project_path,"mediaType":asset.type,"mediaDurationMs":int(asset.duration_ms or 0),
                         "hasAudio":bool(asset.audio_codec),"audioCodec":asset.audio_codec or "","sourceWidth":int(asset.width or 0),"sourceHeight":int(asset.height or 0)})
            enriched.append(item)
        spec["layers"]=sorted(enriched,key=lambda x:(int(x.get("zOrder",x.get("order",0)) or 0),int(x.get("order",0) or 0)))
        if self.phase22 is not None:
            clips=[]
            for clip in self.phase22.audio_clips(project_id,scene_id):
                asset=self.media.get_by_id(clip.media_id)
                if asset is None or asset.project_id!=project_id: continue
                row=clip.to_dict(); row["assetPath"]=asset.project_path; row["hasAudio"]=True; clips.append(row)
            spec["manualAudio"]=clips
        return spec

    @staticmethod
    def validate(spec: dict[str, object], available_filters: set[str] | frozenset[str] = frozenset()) -> list[dict[str,str]]:
        issues=[]
        for layer in list(spec.get("layers",[]) or []):
            if layer.get("missingMedia") or (layer.get("assetId") and not layer.get("assetPath")):
                issues.append({"severity":"error","code":"missing_media","message":"The video used by this layer is no longer available."})
            chroma=dict(layer.get("chromaKey") or {})
            if chroma.get("enabled") and not ({"chromakey","colorkey"}&set(available_filters)):
                issues.append({"severity":"error","code":"chroma_unavailable","message":"Your FFmpeg build does not support the required chroma-key filter."})
        return issues

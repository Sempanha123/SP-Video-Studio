from __future__ import annotations

from domain.manual_audio_clip import ManualAudioClip
from domain.scene_layer import VisualLayerRole


class UniversalVideoService:
    """Manual/no-AI editing coordinator built on canonical Scene/Media/Timeline records."""
    def __init__(self, scene_service, media_repository, phase22_repository, visual_layers, timeline_mapping) -> None:
        self.scenes=scene_service; self.media=media_repository; self.repository=phase22_repository; self.layers=visual_layers; self.timeline=timeline_mapping

    def add_media_at_playhead(self, project_id: str, media_id: str, playhead_ms: int, track: str="video"):
        asset=self.media.get_by_id(media_id)
        if asset is None or asset.project_id!=project_id: raise KeyError("Media is not in this project.")
        mapped=self.timeline.project_to_scene_time(project_id,max(0,int(playhead_ms)))
        if asset.type=="audio":
            duration=max(1,int(asset.duration_ms or 5000)); scene_id=mapped[0] if mapped else ""; local_start=mapped[1] if mapped else max(0,int(playhead_ms))
            item=ManualAudioClip(project_id=project_id,media_id=asset.id,start_ms=local_start,duration_ms=duration,scene_id=scene_id,metadata={"track":track,"projectStartMs":max(0,int(playhead_ms))})
            return self.repository.save_audio_clip(item)
        if asset.type not in {"video","image"}: raise ValueError("Only video, image or audio media can be added to the timeline.")
        if mapped is None:
            duration=max(1000,int(asset.duration_ms or 5000)); scene=self.scenes.add_scene(project_id,asset.name,duration); self.scenes.assign_media(project_id,scene.id,asset.id); return scene
        scene_id,local=mapped
        scene=self.scenes.get(project_id,scene_id)[0]
        if track in {"video","v1","main"} and not scene.primary_media_id:
            return self.scenes.assign_media(project_id,scene_id,asset.id)
        role=VisualLayerRole.BROLL.value if track in {"broll","v2"} else VisualLayerRole.OVERLAY_VIDEO.value
        return self.layers.add_media_layer(project_id,scene_id,asset.id,role=role,start_ms=local,duration_ms=max(1,min(scene.duration_ms-local,int(asset.duration_ms or scene.duration_ms))))

    def add_text_at_playhead(self,project_id:str,text:str,playhead_ms:int):
        mapped=self.timeline.project_to_scene_time(project_id,playhead_ms)
        if not mapped: raise ValueError("Add a visual scene before adding text.")
        item=self.scenes.add_text_overlay(project_id,mapped[0],text or "Text","body_text")
        item.start_offset_ms=mapped[1]
        return self.scenes.repository.update_overlay(project_id,item,self.scenes.get(project_id,mapped[0])[0].duration_ms)

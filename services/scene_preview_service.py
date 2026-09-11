from __future__ import annotations

from domain.scene import Scene
from domain.scene_layer import SceneLayer
from domain.scene_overlay import SceneOverlay


class ScenePreviewService:
    """Produces renderer-neutral scene/sequence specifications; Phase 13 never invokes FFmpeg."""

    @staticmethod
    def build_scene_spec(scene: Scene, layers: list[SceneLayer], overlays: list[SceneOverlay], *, media_path: str="", narration_path: str="", subtitle_track: dict|None=None, aspect_ratio: str="16:9") -> dict[str,object]:
        return {
            "sceneId":scene.id,"durationMs":scene.duration_ms,"aspectRatio":aspect_ratio,"enabled":scene.enabled,
            "visual":{"mediaId":scene.primary_media_id,"path":media_path,"fitMode":scene.fit_mode,"sourceStartMs":scene.source_start_ms,"sourceEndMs":scene.source_end_ms,"backgroundColor":scene.background_color,"backgroundEnabled":bool(scene.metadata.get("backgroundEnabled",False))},
            "audio":{"narrationAudioId":scene.narration_audio_id,"narrationPath":narration_path,**scene.audio.to_dict()},
            "subtitle":{"trackId":scene.subtitle_track_id,**(subtitle_track or {})},
            "layers":[item.to_dict() for item in layers],"overlays":[item.to_dict() for item in overlays],
            "transitionIn":scene.transition_in.to_dict(),"transitionOut":scene.transition_out.to_dict(),
            "source":{"scriptSectionId":scene.script_section_id,"transcriptSegmentId":scene.transcript_segment_id,"translationSegmentId":scene.translation_segment_id,"hash":scene.source_hash,"status":scene.source_status_code},
        }

    @staticmethod
    def build_sequence(items: list[dict[str,object]]) -> dict[str,object]:
        cursor=0; result=[]
        for spec in items:
            if not spec.get("enabled",True): continue
            duration=int(spec.get("durationMs",0) or 0)
            result.append({"sceneId":spec["sceneId"],"startMs":cursor,"endMs":cursor+duration,"durationMs":duration,"transitionOut":spec.get("transitionOut",{}),"spec":spec})
            cursor+=duration
        return {"timelinePolicy":"sequential_no_overlap_phase13","totalDurationMs":cursor,"scenes":result}

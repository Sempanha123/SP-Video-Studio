from __future__ import annotations

from domain.timeline_clip import TimelineClip
from rendering.render_plan import expected_sequence_duration_ms, project_time_map
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.timeline_repository import TimelineRepository


class TimelineMappingService:
    """Derives editor clips from canonical Scene/Overlay/Audio/Subtitle records."""
    def __init__(self, scenes:SceneRepository, media:MediaRepository, audio:GeneratedAudioRepository, subtitles:SubtitleRepository, timeline:TimelineRepository) -> None:
        self.scenes=scenes; self.media=media; self.audio=audio; self.subtitles=subtitles; self.timeline=timeline

    def scene_specs(self, project_id:str)->list[dict]:
        result=[]
        for scene in self.scenes.list_enabled(project_id):
            result.append({"sceneId":scene.id,"durationMs":scene.duration_ms,"transitionOut":scene.transition_out.to_dict()})
        return result

    def scene_ranges(self,project_id:str)->list[dict[str,int|str]]:
        return project_time_map(self.scene_specs(project_id))

    def duration_ms(self,project_id:str)->int:
        return expected_sequence_duration_ms(self.scene_specs(project_id))

    @staticmethod
    def quantize_to_frame(time_ms:int,fps:float)->int:
        rate=max(1.0,float(fps)); frame=round(max(0,int(time_ms))*rate/1000.0); return max(0,int(round(frame*1000.0/rate)))

    def project_to_scene_time(self,project_id:str,project_ms:int)->tuple[str,int]|None:
        value=max(0,int(project_ms)); ranges=self.scene_ranges(project_id)
        # During an overlap both scenes are active; prefer the incoming/later scene for editing.
        for item in reversed(ranges):
            if int(item["startMs"])<=value<int(item["endMs"]):
                return str(item["sceneId"]),value-int(item["startMs"])
        if ranges and value==int(ranges[-1]["endMs"]): return str(ranges[-1]["sceneId"]),int(ranges[-1]["durationMs"])
        return None

    def scene_to_project_time(self,project_id:str,scene_id:str,local_ms:int)->int:
        for item in self.scene_ranges(project_id):
            if str(item["sceneId"])==scene_id: return int(item["startMs"])+max(0,min(int(local_ms),int(item["durationMs"])))
        raise KeyError("Scene is not on the enabled project timeline.")

    def get_scene_at_time(self,project_id:str,project_ms:int):
        mapped=self.project_to_scene_time(project_id,project_ms)
        return self.scenes.get(mapped[0]) if mapped else None

    def get_active_overlays(self,project_id:str,project_ms:int):
        result=[]; value=int(project_ms)
        for item in self.scene_ranges(project_id):
            start=int(item["startMs"]); end=int(item["endMs"])
            if not start<=value<end: continue
            local=value-start
            for overlay in self.scenes.overlays(str(item["sceneId"])):
                if overlay.visible and overlay.start_offset_ms<=local<overlay.end_offset_ms: result.append(overlay)
        return result

    def get_active_subtitle_cues(self,project_id:str,project_ms:int):
        track=self.subtitles.default_for_project(project_id)
        if not track: return []
        value=int(project_ms)
        return [cue for cue in self.subtitles.cues(track.id) if cue.start_ms<=value<cue.end_ms]

    def build_clips(self,project_id:str)->dict[str,list[TimelineClip]]:
        tracks={t.type_code:t for t in self.timeline.ensure_tracks(project_id)}; out={k:[] for k in tracks}
        ranges=self.scene_ranges(project_id); range_by_scene={str(x["sceneId"]):x for x in ranges}
        for item in ranges:
            scene=self.scenes.get(str(item["sceneId"]));
            if scene is None: continue
            start=int(item["startMs"]); duration=scene.duration_ms
            media=self.media.get_by_id(scene.primary_media_id) if scene.primary_media_id else None
            source_type="scene_image" if media and media.type=="image" else "scene_video"
            out["video"].append(TimelineClip(f"scene:{scene.id}",tracks["video"].id,source_type,scene.id,start,duration,scene.source_start_ms,scene.source_end_ms,scene.enabled,tracks["video"].locked,False,scene.name,{"thumbnail":media.thumbnail_path if media else "","missing":bool(scene.primary_media_id and media is None),"fitMode":scene.fit_mode,"transitionType":scene.transition_out.type_code,"transitionDurationMs":scene.transition_out.duration_ms}))
            for overlay in self.scenes.overlays(scene.id):
                dur=max(1,overlay.end_offset_ms-overlay.start_offset_ms)
                out["overlay"].append(TimelineClip(f"overlay:{overlay.id}",tracks["overlay"].id,"scene_overlay",overlay.id,start+overlay.start_offset_ms,dur,0,None,overlay.visible,tracks["overlay"].locked,False,overlay.text or overlay.type_code,{"sceneId":scene.id,"overlayType":overlay.type_code}))
            if scene.narration_audio_id:
                audio=self.audio.get(scene.narration_audio_id); offset=max(0,int(scene.metadata.get("narrationOffsetMs",0) or 0)); adur=(audio.duration_ms if audio else duration)
                out["voice"].append(TimelineClip(f"narration:{scene.id}",tracks["voice"].id,"narration",scene.id,start+offset,max(1,min(adur,max(1,duration-offset))),0,None,scene.audio.narration_enabled,tracks["voice"].locked,tracks["voice"].muted or not scene.audio.narration_enabled,(audio.metadata.get("voiceName","") if audio and isinstance(audio.metadata,dict) else "Narration") or "Narration",{"audioId":scene.narration_audio_id,"volume":scene.audio.narration_volume,"missing":audio is None}))
            if media and media.type=="video" and media.audio_codec:
                out["source_audio"].append(TimelineClip(f"source-audio:{scene.id}",tracks["source_audio"].id,"source_audio",scene.id,start,duration,scene.source_start_ms,scene.source_end_ms,scene.audio.source_audio_enabled,tracks["source_audio"].locked,tracks["source_audio"].muted or not scene.audio.source_audio_enabled,scene.name,{"volume":scene.audio.source_audio_volume}))
        default=self.subtitles.default_for_project(project_id)
        if default:
            for cue in self.subtitles.cues(default.id):
                out["subtitle"].append(TimelineClip(f"subtitle:{cue.id}",tracks["subtitle"].id,"subtitle",cue.id,cue.start_ms,max(1,cue.end_ms-cue.start_ms),0,None,True,tracks["subtitle"].locked,False,cue.text,{"trackId":default.id,"language":default.language}))
        return out

from __future__ import annotations

from domain.timeline_clip import TimelineClip
from rendering.render_plan import expected_sequence_duration_ms, project_time_map
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.timeline_repository import TimelineRepository


class TimelineMappingService:
    """Derives editor clips from canonical Scene/Layer/Overlay/Audio/Subtitle records."""
    def __init__(self, scenes:SceneRepository, media:MediaRepository, audio:GeneratedAudioRepository, subtitles:SubtitleRepository, timeline:TimelineRepository, phase22_repository=None) -> None:
        self.scenes=scenes; self.media=media; self.audio=audio; self.subtitles=subtitles; self.timeline=timeline; self.phase22=phase22_repository

    def scene_specs(self, project_id:str)->list[dict]:
        return [{"sceneId":scene.id,"durationMs":scene.duration_ms,"transitionOut":scene.transition_out.to_dict()} for scene in self.scenes.list_enabled(project_id)]

    def scene_ranges(self,project_id:str)->list[dict[str,int|str]]: return project_time_map(self.scene_specs(project_id))
    def duration_ms(self,project_id:str)->int: return expected_sequence_duration_ms(self.scene_specs(project_id))

    @staticmethod
    def quantize_to_frame(time_ms:int,fps:float)->int:
        rate=max(1.0,float(fps)); frame=round(max(0,int(time_ms))*rate/1000.0); return max(0,int(round(frame*1000.0/rate)))

    def project_to_scene_time(self,project_id:str,project_ms:int)->tuple[str,int]|None:
        value=max(0,int(project_ms)); ranges=self.scene_ranges(project_id)
        for item in reversed(ranges):
            if int(item["startMs"])<=value<int(item["endMs"]): return str(item["sceneId"]),value-int(item["startMs"])
        if ranges and value==int(ranges[-1]["endMs"]): return str(ranges[-1]["sceneId"]),int(ranges[-1]["durationMs"])
        return None

    def scene_to_project_time(self,project_id:str,scene_id:str,local_ms:int)->int:
        for item in self.scene_ranges(project_id):
            if str(item["sceneId"])==scene_id: return int(item["startMs"])+max(0,min(int(local_ms),int(item["durationMs"])))
        raise KeyError("Scene is not on the enabled project timeline.")

    def get_scene_at_time(self,project_id:str,project_ms:int):
        mapped=self.project_to_scene_time(project_id,project_ms); return self.scenes.get(mapped[0]) if mapped else None

    def get_active_overlays(self,project_id:str,project_ms:int):
        result=[]; value=int(project_ms)
        for item in self.scene_ranges(project_id):
            start=int(item["startMs"]); end=int(item["endMs"])
            if not start<=value<end: continue
            local=value-start
            for overlay in self.scenes.overlays(str(item["sceneId"])):
                if overlay.visible and overlay.start_offset_ms<=local<(overlay.end_offset_ms if overlay.end_offset_ms is not None else int(item["durationMs"])): result.append(overlay)
        return result

    def get_active_layers(self,project_id:str,project_ms:int):
        result=[]; mapped=self.project_to_scene_time(project_id,project_ms)
        if not mapped: return result
        scene_id,local=mapped
        for layer in self.scenes.layers(scene_id):
            duration=layer.duration_ms or max(1,(self.scenes.get(scene_id).duration_ms if self.scenes.get(scene_id) else 1)-layer.start_ms)
            if layer.visible and layer.start_ms<=local<layer.start_ms+duration: result.append(layer)
        return sorted(result,key=lambda x:(x.z_order,x.order,x.id))

    def get_active_subtitle_cues(self,project_id:str,project_ms:int):
        track=self.subtitles.default_for_project(project_id)
        if not track: return []
        value=int(project_ms); return [cue for cue in self.subtitles.cues(track.id) if cue.start_ms<=value<cue.end_ms]

    def build_clips(self,project_id:str)->dict[str,list[TimelineClip]]:
        tracks={t.type_code:t for t in self.timeline.ensure_tracks(project_id)}; out={k:[] for k in tracks}
        ranges=self.scene_ranges(project_id)
        for item in ranges:
            scene=self.scenes.get(str(item["sceneId"]));
            if scene is None: continue
            start=int(item["startMs"]); duration=scene.duration_ms
            media=self.media.get_by_id(scene.primary_media_id) if scene.primary_media_id else None
            source_type="scene_image" if media and media.type=="image" else "scene_video"
            out["video"].append(TimelineClip(f"scene:{scene.id}",tracks["video"].id,source_type,scene.id,start,duration,scene.source_start_ms,scene.source_end_ms,scene.enabled,tracks["video"].locked,False,scene.name,{"thumbnail":media.thumbnail_path if media else "","missing":bool(scene.primary_media_id and media is None),"fitMode":scene.fit_mode,"transitionType":scene.transition_out.type_code,"transitionDurationMs":scene.transition_out.duration_ms,"trackLabel":"V1 Main"}))
            for layer in sorted(self.scenes.layers(scene.id),key=lambda x:(x.z_order,x.order,x.id)):
                asset=self.media.get_by_id(layer.asset_id) if layer.asset_id else None; role=layer.role
                target="broll" if role in {"broll","image_overlay"} else "overlay"
                if target not in tracks: target="overlay"
                ldur=layer.duration_ms or max(1,duration-layer.start_ms); metadata=layer.to_dict(); metadata.update({"sceneId":scene.id,"thumbnail":asset.thumbnail_path if asset else "","missing":bool(layer.asset_id and asset is None),"trackLabel":"V2 B-roll" if target=="broll" else "V3 Presenter/Overlay"})
                out[target].append(TimelineClip(f"layer:{layer.id}",tracks[target].id,"visual_layer",layer.id,start+layer.start_ms,ldur,layer.source_in_ms,layer.source_out_ms,layer.visible,tracks[target].locked,False,(asset.name if asset else role.replace("_"," ").title()),metadata))
            for overlay in self.scenes.overlays(scene.id):
                dur=max(1,(overlay.end_offset_ms if overlay.end_offset_ms is not None else scene.duration_ms)-overlay.start_offset_ms)
                out["overlay"].append(TimelineClip(f"overlay:{overlay.id}",tracks["overlay"].id,"scene_overlay",overlay.id,start+overlay.start_offset_ms,dur,0,None,overlay.visible,tracks["overlay"].locked,False,overlay.text or overlay.type_code,{"sceneId":scene.id,"overlayType":overlay.type_code}))
            if scene.narration_audio_id:
                audio=self.audio.get(scene.narration_audio_id); offset=max(0,int(scene.metadata.get("narrationOffsetMs",0) or 0)); adur=(audio.duration_ms if audio else duration)
                out["voice"].append(TimelineClip(f"narration:{scene.id}",tracks["voice"].id,"narration",scene.id,start+offset,max(1,min(adur,max(1,duration-offset))),0,None,scene.audio.narration_enabled,tracks["voice"].locked,tracks["voice"].muted or not scene.audio.narration_enabled,(audio.metadata.get("voiceName","") if audio and isinstance(audio.metadata,dict) else "Narration") or "Narration",{"audioId":scene.narration_audio_id,"volume":scene.audio.narration_volume,"missing":audio is None}))
            if media and media.type=="video" and media.audio_codec:
                out["source_audio"].append(TimelineClip(f"source-audio:{scene.id}",tracks["source_audio"].id,"source_audio",scene.id,start,duration,scene.source_start_ms,scene.source_end_ms,scene.audio.source_audio_enabled,tracks["source_audio"].locked,tracks["source_audio"].muted or not scene.audio.source_audio_enabled,scene.name,{"volume":scene.audio.source_audio_volume}))
        if self.phase22 is not None and "music" in tracks:
            for clip in self.phase22.audio_clips(project_id):
                asset=self.media.get_by_id(clip.media_id); project_start=int(clip.metadata.get("projectStartMs",clip.start_ms) or clip.start_ms); out["music"].append(TimelineClip(f"manual-audio:{clip.id}",tracks["music"].id,"manual_audio",clip.id,project_start,clip.duration_ms,clip.source_in_ms,None,not clip.muted,tracks["music"].locked,tracks["music"].muted or clip.muted,(asset.name if asset else "Manual Audio"),{"mediaId":clip.media_id,"volume":clip.volume,"fadeInMs":clip.fade_in_ms,"fadeOutMs":clip.fade_out_ms,"missing":asset is None}))
        default=self.subtitles.default_for_project(project_id)
        if default:
            for cue in self.subtitles.cues(default.id): out["subtitle"].append(TimelineClip(f"subtitle:{cue.id}",tracks["subtitle"].id,"subtitle",cue.id,cue.start_ms,max(1,cue.end_ms-cue.start_ms),0,None,True,tracks["subtitle"].locked,False,cue.text,{"trackId":default.id,"language":default.language}))
        return out

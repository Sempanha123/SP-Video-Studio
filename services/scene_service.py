from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from domain.project import utc_now_iso
from domain.scene import Scene, SceneSourceStatus, SceneStatus
from domain.scene_audio import SceneAudioSettings
from domain.scene_layer import SceneLayer
from domain.scene_overlay import SceneOverlay, SceneOverlayType
from domain.scene_transition import SceneTransition, SceneTransitionType
from services.scene_generation_service import SceneGenerationService, script_section_source_hash
from services.scene_preview_service import ScenePreviewService
from services.scene_validation_service import SceneIssue, SceneValidationService
from services.script_service import ScriptService
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.transcript_repository import TranscriptRepository


class SceneServiceError(RuntimeError):
    user_message = "SP Video Studio could not complete this scene action."


class SceneNotFound(SceneServiceError): pass
class SceneInvalidDuration(SceneServiceError): pass
class SceneMissingMedia(SceneServiceError): pass
class SceneInvalidSourceRange(SceneServiceError): pass
class SceneInvalidOverlay(SceneServiceError): pass
class SceneInvalidTransition(SceneServiceError): pass
class SceneSourceMismatch(SceneServiceError): pass


class SceneService:
    def __init__(
        self,
        repository: SceneRepository,
        project_repository: ProjectRepository,
        media_repository: MediaRepository,
        audio_repository: GeneratedAudioRepository,
        subtitle_repository: SubtitleRepository,
        script_service: ScriptService,
        transcript_repository: TranscriptRepository,
        generation: SceneGenerationService,
        validation: SceneValidationService,
        preview: ScenePreviewService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository=repository; self.project_repository=project_repository; self.media_repository=media_repository
        self.audio_repository=audio_repository; self.subtitle_repository=subtitle_repository; self.script_service=script_service
        self.transcript_repository=transcript_repository; self.generation=generation; self.validation=validation
        self.preview=preview or ScenePreviewService(); self.logger=logger or logging.getLogger("sp_video_studio.scenes")

    def list_scenes(self, project_id: str) -> list[Scene]:
        self._project(project_id); scenes=self.repository.list_for_project(project_id)
        for scene in scenes: self._refresh_status(scene, persist=False)
        return scenes

    def get(self, project_id: str, scene_id: str) -> tuple[Scene,list[SceneLayer],list[SceneOverlay]]:
        scene=self._owned(project_id,scene_id); self._refresh_status(scene,persist=False)
        return scene,self.repository.layers(scene_id),self.repository.overlays(scene_id)

    def add_scene(self, project_id: str, name: str | None=None, duration_ms: int=5000) -> Scene:
        self._project(project_id); scenes=self.repository.list_for_project(project_id)
        scene=Scene(project_id=project_id,order=len(scenes),name=(name or f"Scene {len(scenes)+1}").strip() or f"Scene {len(scenes)+1}",duration_ms=max(1,int(duration_ms)))
        scene.status=SceneStatus.INCOMPLETE; self.repository.create(scene); self.logger.info("Scene created: %s",scene.id); return scene

    def delete_scene(self, project_id: str, scene_id: str) -> None:
        self._owned(project_id,scene_id); self.repository.delete(project_id,scene_id); self._normalize(project_id); self.logger.info("Scene removed: %s",scene_id)

    def duplicate_scene(self, project_id: str, scene_id: str) -> Scene:
        source=self._owned(project_id,scene_id); scenes=self.repository.list_for_project(project_id)
        index=next(i for i,s in enumerate(scenes) if s.id==scene_id)
        clone=deepcopy(source); clone.scene_id=str(uuid4()); clone.name=f"{source.name} Copy"; clone.order=index+1; clone.created_at=clone.updated_at=utc_now_iso()
        layers=[]
        for layer in self.repository.layers(source.id):
            item=deepcopy(layer); item.layer_id=str(uuid4()); item.scene_id=clone.id; layers.append(item)
        overlays=[]
        for overlay in self.repository.overlays(source.id):
            item=deepcopy(overlay); item.overlay_id=str(uuid4()); item.scene_id=clone.id; overlays.append(item)
        # temporarily append to avoid unique index collision, then reorder
        clone.order=len(scenes); self.repository.create(clone,layers,overlays)
        ordered=scenes[:index+1]+[clone]+scenes[index+1:]; self.repository.save_order(project_id,ordered)
        self.logger.info("Scene duplicated: %s -> %s",source.id,clone.id); return clone

    def move_scene(self, project_id: str, scene_id: str, new_index: int) -> list[Scene]:
        scenes=self.repository.list_for_project(project_id); idx=next((i for i,s in enumerate(scenes) if s.id==scene_id),None)
        if idx is None: raise SceneNotFound("Scene could not be found.")
        item=scenes.pop(idx); target=max(0,min(int(new_index),len(scenes))); scenes.insert(target,item); self.repository.save_order(project_id,scenes); return scenes

    def set_enabled(self, project_id: str, scene_id: str, enabled: bool) -> Scene:
        scene=self._owned(project_id,scene_id); scene.enabled=bool(enabled); return self._save(scene)

    def update_general(self, project_id: str, scene_id: str, *, name: str|None=None, duration_ms: int|None=None, background_color: str|None=None) -> Scene:
        scene=self._owned(project_id,scene_id)
        if name is not None:
            clean=name.strip()
            if not clean: raise SceneServiceError("Scene name is required.")
            scene.name=clean
        if duration_ms is not None:
            if int(duration_ms)<=0: raise SceneInvalidDuration("Scene duration must be greater than zero.")
            scene.duration_ms=int(duration_ms)
        if background_color is not None:
            scene.background_color=str(background_color); scene.metadata["backgroundEnabled"]=True
        return self._save(scene)

    def set_background_enabled(self, project_id: str, scene_id: str, enabled: bool) -> Scene:
        scene=self._owned(project_id,scene_id); scene.metadata["backgroundEnabled"]=bool(enabled); return self._save(scene)

    def assign_media(self, project_id: str, scene_id: str, media_id: str, *, fit_mode: str|None=None) -> Scene:
        scene=self._owned(project_id,scene_id); asset=self.media_repository.get_by_id(media_id)
        if asset is None or asset.project_id!=project_id: raise SceneMissingMedia("This media item is not part of the current project.")
        if asset.type not in {"image","video"}: raise SceneMissingMedia("Choose an image or video for scene visuals.")
        scene.primary_media_id=media_id
        if fit_mode is not None: scene.fit_mode=fit_mode
        if asset.type=="video" and asset.duration_ms:
            scene.source_start_ms=min(scene.source_start_ms,max(0,asset.duration_ms-1)); scene.source_end_ms=None
        return self._save(scene)

    def replace_media(self, project_id: str, scene_id: str, media_id: str) -> Scene: return self.assign_media(project_id,scene_id,media_id)

    def clear_media(self, project_id: str, scene_id: str) -> Scene:
        scene=self._owned(project_id,scene_id); scene.primary_media_id=""; scene.source_start_ms=0; scene.source_end_ms=None; return self._save(scene)

    def set_fit_mode(self, project_id: str, scene_id: str, fit_mode: str) -> Scene:
        scene=self._owned(project_id,scene_id); scene.fit_mode=fit_mode; return self._save(scene)

    def set_video_range(self, project_id: str, scene_id: str, start_ms: int, end_ms: int|None=None) -> Scene:
        scene=self._owned(project_id,scene_id)
        if not scene.primary_media_id: raise SceneInvalidSourceRange("Choose a video first.")
        media=self.media_repository.get_by_id(scene.primary_media_id)
        if media is None or media.project_id!=project_id or media.type!="video": raise SceneInvalidSourceRange("The selected scene visual is not a video.")
        start=max(0,int(start_ms)); end=None if end_ms is None or int(end_ms)<0 else int(end_ms)
        if end is not None and end<=start: raise SceneInvalidSourceRange("Video end must be after video start.")
        if media.duration_ms and (start>=media.duration_ms or (end is not None and end>media.duration_ms)): raise SceneInvalidSourceRange("The selected video range is outside the media duration.")
        scene.source_start_ms=start; scene.source_end_ms=end; return self._save(scene)

    def assign_narration(self, project_id: str, scene_id: str, audio_id: str) -> Scene:
        scene=self._owned(project_id,scene_id)
        if audio_id:
            audio=self.audio_repository.get(audio_id)
            if audio is None or audio.project_id!=project_id: raise SceneServiceError("Generated narration could not be found in this project.")
        scene.narration_audio_id=audio_id; return self._save(scene)

    def match_duration_to_narration(self, project_id: str, scene_id: str) -> Scene:
        scene=self._owned(project_id,scene_id)
        audio=self.audio_repository.get(scene.narration_audio_id) if scene.narration_audio_id else None
        if audio is None or audio.project_id!=project_id or audio.duration_ms<=0: raise SceneServiceError("Assign valid narration before matching duration.")
        scene.duration_ms=audio.duration_ms; return self._save(scene)

    def assign_subtitle(self, project_id: str, scene_id: str, track_id: str) -> Scene:
        scene=self._owned(project_id,scene_id)
        if track_id:
            track=self.subtitle_repository.get_track(track_id)
            if track is None or track.project_id!=project_id: raise SceneServiceError("Subtitle track could not be found in this project.")
        scene.subtitle_track_id=track_id; return self._save(scene)

    def set_audio(self, project_id: str, scene_id: str, *, source_enabled: bool|None=None, source_volume: float|None=None, narration_enabled: bool|None=None, narration_volume: float|None=None) -> Scene:
        scene=self._owned(project_id,scene_id); audio=scene.audio
        if source_enabled is not None: audio.source_audio_enabled=bool(source_enabled)
        if source_volume is not None: audio.source_audio_volume=max(0,min(1,float(source_volume)))
        if narration_enabled is not None: audio.narration_enabled=bool(narration_enabled)
        if narration_volume is not None: audio.narration_volume=max(0,min(1,float(narration_volume)))
        return self._save(scene)

    def set_transition(self, project_id: str, scene_id: str, transition_type: str, duration_ms: int=0, *, outgoing: bool=True, direction: str="") -> Scene:
        scene=self._owned(project_id,scene_id); transition=SceneTransition(transition_type,int(duration_ms),direction); transition.validate()
        if transition.duration_ms>scene.duration_ms//2: raise SceneInvalidTransition("Transition is too long for this scene.")
        if outgoing: scene.transition_out=transition
        else: scene.transition_in=transition
        return self._save(scene)

    def overlays(self, project_id: str, scene_id: str) -> list[SceneOverlay]: self._owned(project_id,scene_id); return self.repository.overlays(scene_id)

    def add_text_overlay(self, project_id: str, scene_id: str, text: str="Text", overlay_type: str="body_text") -> SceneOverlay:
        scene=self._owned(project_id,scene_id); overlays=self.repository.overlays(scene_id)
        defaults={"headline":(.08,.08,.84,.18),"lower_third":(.07,.72,.70,.18),"body_text":(.10,.36,.80,.22),"label":(.10,.10,.45,.12)}
        x,y,w,h=defaults.get(overlay_type,defaults["body_text"])
        overlay=SceneOverlay(scene_id=scene_id,order=len(overlays),overlay_type=overlay_type,text=text,x=x,y=y,width=w,height=h,end_offset_ms=scene.duration_ms)
        return self.repository.add_overlay(project_id,overlay,scene.duration_ms)

    def add_lower_third(self, project_id: str, scene_id: str, primary: str="Name", secondary: str="Role") -> SceneOverlay:
        item=self.add_text_overlay(project_id,scene_id,primary,"lower_third"); item.secondary_text=secondary; return self.repository.update_overlay(project_id,item,self._owned(project_id,scene_id).duration_ms)

    def add_logo(self, project_id: str, scene_id: str, media_id: str) -> SceneOverlay:
        scene=self._owned(project_id,scene_id); asset=self.media_repository.get_by_id(media_id)
        if asset is None or asset.project_id!=project_id or asset.type!="image": raise SceneInvalidOverlay("Choose a project image for the logo.")
        overlays=self.repository.overlays(scene_id); item=SceneOverlay(scene_id=scene_id,order=len(overlays),overlay_type=SceneOverlayType.LOGO,asset_id=media_id,x=.78,y=.05,width=.16,height=.16,end_offset_ms=scene.duration_ms)
        return self.repository.add_overlay(project_id,item,scene.duration_ms)

    def update_overlay(self, project_id: str, scene_id: str, overlay_id: str, updates: dict[str,object]) -> SceneOverlay:
        scene=self._owned(project_id,scene_id); items=self.repository.overlays(scene_id); item=next((x for x in items if x.id==overlay_id),None)
        if item is None: raise SceneInvalidOverlay("Overlay could not be found.")
        aliases={"secondaryText":"secondary_text","startOffsetMs":"start_offset_ms","endOffsetMs":"end_offset_ms","assetId":"asset_id"}
        allowed={"text","secondary_text","x","y","width","height","opacity","rotation","visible","start_offset_ms","end_offset_ms","style","asset_id"}
        for key,value in updates.items():
            attr=aliases.get(key,key)
            if attr not in allowed: continue
            setattr(item,attr,value)
        try: return self.repository.update_overlay(project_id,item,scene.duration_ms)
        except ValueError as exc: raise SceneInvalidOverlay(str(exc)) from exc

    def delete_overlay(self, project_id: str, scene_id: str, overlay_id: str) -> None:
        self._owned(project_id,scene_id); self.repository.delete_overlay(project_id,overlay_id); self._normalize_overlays(project_id,scene_id)

    def move_overlay(self, project_id: str, scene_id: str, overlay_id: str, delta: int) -> list[SceneOverlay]:
        self._owned(project_id,scene_id); items=self.repository.overlays(scene_id); idx=next((i for i,x in enumerate(items) if x.id==overlay_id),None)
        if idx is None: raise SceneInvalidOverlay("Overlay could not be found.")
        target=max(0,min(idx+int(delta),len(items)-1)); item=items.pop(idx); items.insert(target,item); self.repository.replace_overlays(project_id,scene_id,items,self._owned(project_id,scene_id).duration_ms); return items

    def create_from_script(self, project_id: str, *, append: bool=False) -> list[Scene]:
        project=self._project(project_id); script,sections=self.script_service.load_or_create(project_id)
        existing=self.repository.list_for_project(project_id)
        if existing and not append: raise SceneServiceError("This project already has scenes. Use Sync Scenes with Script or add scenes manually.")
        result=list(existing); mapped={s.script_section_id for s in existing if s.script_section_id}
        order=len(existing)
        for section in sections:
            if not section.enabled or section.section_id in mapped: continue
            scene=self.generation.from_script_section(project_id,section,script.language,str(script.pace),order); self.repository.create(scene); result.append(scene); order+=1
        return result

    def create_from_transcript(self, project_id: str, transcript_id: str, *, group_ms: int=15000, append: bool=True) -> list[Scene]:
        self._project(project_id); transcript=self.transcript_repository.get(transcript_id)
        if transcript is None or transcript.project_id!=project_id: raise SceneSourceMismatch("Transcript could not be found in this project.")
        segments=self.transcript_repository.segments(transcript_id); groups=[]; current=[]; start=None
        for segment in segments:
            if start is None: start=segment.start_ms
            if current and segment.end_ms-start>max(3000,int(group_ms)):
                groups.append(current); current=[]; start=segment.start_ms
            current.append(segment)
        if current: groups.append(current)
        if not append and self.repository.list_for_project(project_id): raise SceneServiceError("This project already has scenes.")
        order=len(self.repository.list_for_project(project_id)); created=[]
        for i,group in enumerate(groups,1):
            scene=self.generation.from_transcript_group(project_id,group,order,f"Transcript Scene {i}")
            # Transcript scenes reuse the project-managed source media and preserve the
            # selected source range. No copy or trim is created in Phase 13.
            media=self.media_repository.get_by_id(transcript.media_id)
            if media is not None and media.project_id==project_id and media.type in {"image","video"}:
                scene.primary_media_id=media.id
                if media.type=="video":
                    scene.source_start_ms=min(x.start_ms for x in group)
                    scene.source_end_ms=max(x.end_ms for x in group)
            self.repository.create(scene); created.append(scene); order+=1
        return created

    def sync_with_script(self, project_id: str, *, create_new: bool=True) -> dict[str,int]:
        script,sections=self.script_service.load_or_create(project_id); scenes=self.repository.list_for_project(project_id); section_by_id={s.section_id:s for s in sections}; mapped={s.script_section_id:s for s in scenes if s.script_section_id}; changed=missing=added=0
        for scene in scenes:
            if not scene.script_section_id: continue
            section=section_by_id.get(scene.script_section_id)
            if section is None:
                if scene.source_status_code!=SceneSourceStatus.MISSING.value: scene.source_status=SceneSourceStatus.MISSING; self.repository.update(scene); missing+=1
                continue
            current_hash=script_section_source_hash(section)
            if current_hash!=scene.source_hash:
                scene.source_status=SceneSourceStatus.CHANGED; scene.metadata["sourceTitle"]=section.title; self.repository.update(scene); changed+=1
            else:
                scene.source_status=SceneSourceStatus.CURRENT; self.repository.update(scene)
        if create_new:
            order=len(scenes)
            for section in sections:
                if section.enabled and section.section_id not in mapped:
                    scene=self.generation.from_script_section(project_id,section,script.language,str(script.pace),order); self.repository.create(scene); added+=1; order+=1
        return {"changed":changed,"missing":missing,"added":added}

    def sync_scene_from_script(self, project_id: str, scene_id: str, *, update_name: bool=True, update_duration: bool=False) -> Scene:
        scene=self._owned(project_id,scene_id)
        if not scene.script_section_id: raise SceneSourceMismatch("This scene is not linked to a script section.")
        script,sections=self.script_service.load_or_create(project_id); section=next((s for s in sections if s.section_id==scene.script_section_id),None)
        if section is None: scene.source_status=SceneSourceStatus.MISSING; return self._save(scene)
        if update_name: scene.name=section.title
        if update_duration:
            estimate=self.script_service.analysis.analyze_text(section.content,script.language,str(script.pace)).estimated_duration_ms
            if estimate>0: scene.duration_ms=estimate
        scene.source_hash=script_section_source_hash(section); scene.source_status=SceneSourceStatus.CURRENT; scene.metadata["sourceTitle"]=section.title
        return self._save(scene)

    def validate_scene(self, project_id: str, scene_id: str) -> list[SceneIssue]:
        scene=self._owned(project_id,scene_id); return self.validation.validate(scene,self.repository.overlays(scene_id))

    def project_summary(self, project_id: str) -> dict[str,int]:
        scenes=self.list_scenes(project_id); ready=warnings=missing=0; total=0
        for scene in scenes:
            if scene.enabled: total+=scene.duration_ms
            issues=self.validation.validate(scene,self.repository.overlays(scene.id))
            if scene.status_code==SceneStatus.READY.value: ready+=1
            if any(i.severity=="warning" for i in issues): warnings+=1
            if any(i.code in {"missing_media","missing_narration","missing_subtitle"} for i in issues): missing+=1
        return {"sceneCount":len(scenes),"totalDurationMs":total,"readyCount":ready,"warningCount":warnings,"missingCount":missing}

    def build_scene_render_spec(self, project_id: str, scene_id: str) -> dict[str,object]:
        project=self._project(project_id); scene,layers,overlays=self.get(project_id,scene_id); media_path=""; narration_path=""; subtitle={}
        asset=None
        if scene.primary_media_id:
            asset=self.media_repository.get_by_id(scene.primary_media_id); media_path=asset.project_path if asset and asset.project_id==project_id else ""
        narration=None
        if scene.narration_audio_id:
            narration=self.audio_repository.get(scene.narration_audio_id); narration_path=narration.file_path if narration and narration.project_id==project_id else ""
        if scene.subtitle_track_id:
            track=self.subtitle_repository.get_track(scene.subtitle_track_id); subtitle=track.to_dict() if track and track.project_id==project_id else {}
        spec=self.preview.build_scene_spec(scene,layers,overlays,media_path=media_path,narration_path=narration_path,subtitle_track=subtitle,aspect_ratio=project.aspect_ratio)
        visual=spec["visual"]
        if asset is not None and asset.project_id==project_id:
            visual.update({"mediaType":asset.type,"width":asset.width or 0,"height":asset.height or 0,"durationMs":asset.duration_ms or 0,"hasAudio":bool(asset.audio_codec),"audioCodec":asset.audio_codec or "","rotation":int((asset.metadata_json or {}).get("rotation",0) or 0) if isinstance(asset.metadata_json,dict) else 0})
        spec["audio"]["narrationDurationMs"] = narration.duration_ms if narration is not None and narration.project_id==project_id else 0
        enriched=[]
        for overlay in spec.get("overlays",[]):
            item=dict(overlay); asset_id=str(item.get("assetId","") or "")
            if asset_id:
                overlay_asset=self.media_repository.get_by_id(asset_id)
                if overlay_asset is not None and overlay_asset.project_id==project_id: item["assetPath"]=overlay_asset.project_path
            enriched.append(item)
        spec["overlays"]=enriched
        return spec

    def build_project_scene_sequence(self, project_id: str) -> dict[str,object]:
        specs=[self.build_scene_render_spec(project_id,s.id) for s in self.repository.list_enabled(project_id)]; return self.preview.build_sequence(specs)

    def duplicate_project_scenes(self, source_project_id: str, target_project_id: str, *, media_map:dict[str,str]|None=None,audio_map:dict[str,str]|None=None,script_section_map:dict[str,str]|None=None,transcript_segment_map:dict[str,str]|None=None,translation_segment_map:dict[str,str]|None=None,subtitle_track_map:dict[str,str]|None=None) -> dict[str,str]:
        maps=[media_map or {},audio_map or {},script_section_map or {},transcript_segment_map or {},translation_segment_map or {},subtitle_track_map or {}]
        media_map,audio_map,script_section_map,transcript_segment_map,translation_segment_map,subtitle_track_map=maps
        result={}
        for source in self.repository.list_for_project(source_project_id):
            clone=deepcopy(source); clone.scene_id=str(uuid4()); clone.project_id=target_project_id; clone.primary_media_id=media_map.get(source.primary_media_id,"") if source.primary_media_id else ""; clone.background_media_id=media_map.get(source.background_media_id,"") if source.background_media_id else ""; clone.narration_audio_id=audio_map.get(source.narration_audio_id,"") if source.narration_audio_id else ""; clone.subtitle_track_id=subtitle_track_map.get(source.subtitle_track_id,"") if source.subtitle_track_id else ""; clone.script_section_id=script_section_map.get(source.script_section_id,"") if source.script_section_id else ""; clone.transcript_segment_id=transcript_segment_map.get(source.transcript_segment_id,"") if source.transcript_segment_id else ""; clone.translation_segment_id=translation_segment_map.get(source.translation_segment_id,"") if source.translation_segment_id else ""; clone.created_at=clone.updated_at=utc_now_iso()
            layers=[]
            for layer in self.repository.layers(source.id):
                item=deepcopy(layer); item.layer_id=str(uuid4()); item.scene_id=clone.id; item.asset_id=media_map.get(item.asset_id,"") if item.asset_id else ""; layers.append(item)
            overlays=[]
            for overlay in self.repository.overlays(source.id):
                item=deepcopy(overlay); item.overlay_id=str(uuid4()); item.scene_id=clone.id; item.asset_id=media_map.get(item.asset_id,"") if item.asset_id else ""; overlays.append(item)
            self.repository.create(clone,layers,overlays); result[source.id]=clone.id
        return result

    def _save(self, scene: Scene) -> Scene:
        self._refresh_status(scene,persist=False); return self.repository.update(scene)

    def _refresh_status(self, scene: Scene, *, persist: bool) -> Scene:
        if not scene.enabled: status=SceneStatus.DISABLED
        else:
            issues=self.validation.validate(scene,self.repository.overlays(scene.id) if self.repository.get(scene.id) else [])
            if any(i.code in {"missing_media","missing_narration","missing_subtitle"} for i in issues): status=SceneStatus.MISSING_ASSET
            elif not scene.primary_media_id and not bool(scene.metadata.get("backgroundEnabled", False)): status=SceneStatus.INCOMPLETE
            else: status=SceneStatus.READY
        if scene.status_code!=status.value:
            scene.status=status
            if persist and self.repository.get(scene.id): self.repository.update(scene)
        return scene

    def _normalize(self, project_id: str) -> None: self.repository.save_order(project_id,self.repository.list_for_project(project_id))
    def _normalize_overlays(self, project_id: str, scene_id: str) -> None:
        scene=self._owned(project_id,scene_id); self.repository.replace_overlays(project_id,scene_id,self.repository.overlays(scene_id),scene.duration_ms)
    def _owned(self, project_id: str, scene_id: str) -> Scene:
        scene=self.repository.get(scene_id)
        if scene is None or scene.project_id!=project_id: raise SceneNotFound("Scene could not be found in this project.")
        return scene
    def _project(self, project_id: str):
        project=self.project_repository.get_by_id(project_id)
        if project is None: raise SceneServiceError("Project could not be found.")
        return project

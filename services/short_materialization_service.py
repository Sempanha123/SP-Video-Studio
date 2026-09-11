from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from domain.project import ProjectWorkflow, utc_now_iso
from domain.short_candidate import ShortCandidateStatus
from domain.short_project import ShortProject, ShortProjectStatus
from domain.shorts_errors import ShortCandidateInvalid, ShortSourceMissing
from services.short_reframe_service import ShortReframeService
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.short_repository import ShortRepository
from storage.repositories.transcript_repository import TranscriptRepository


class ShortMaterializationService:
    """Turns a candidate into ordinary editable Scene/Timeline state in an independent project."""
    def __init__(
        self,
        shorts: ShortRepository,
        project_service,
        project_repository: ProjectRepository,
        media: MediaRepository,
        scenes,
        scene_repository: SceneRepository,
        transcripts: TranscriptRepository,
        reframe: ShortReframeService,
        dubbing_repository=None, short_audio=None, subtitle_ranges=None,
    ) -> None:
        self.shorts=shorts; self.project_service=project_service; self.projects=project_repository; self.media=media
        self.scenes=scenes; self.scene_repository=scene_repository; self.transcripts=transcripts; self.reframe=reframe
        self.dubbing=dubbing_repository; self.short_audio=short_audio; self.subtitle_ranges=subtitle_ranges

    def create_derived_project(self, candidate_id: str, *, title: str|None=None, target_aspect_ratio: str="9:16", platform: str="generic", style: str="creator"):
        source_candidate=self.shorts.get_candidate(candidate_id)
        if source_candidate is None: raise ShortCandidateInvalid("Short candidate could not be found.")
        source_project=self.projects.get_by_id(source_candidate.project_id)
        if source_project is None: raise ShortSourceMissing("The source project is unavailable.")

        # Reuse the authoritative ProjectService duplication path so News/Story/Speaker/Media mappings remain independent.
        duplicate=self.project_service.duplicate_project(source_project.project_id)
        duplicate.title=(title or f"{source_candidate.title} Short").strip() or f"{source_candidate.title} Short"
        duplicate.workflow=ProjectWorkflow.SHORTS
        duplicate.aspect_ratio=target_aspect_ratio
        duplicate.language=source_candidate.language or source_project.language
        duplicate.updated_at=utc_now_iso()
        duplicate.validate(); self.projects.update(duplicate)
        # ProjectService owns portable project.json. This is an existing internal helper, not a second metadata writer.
        writer=getattr(self.project_service,"_write_metadata",None)
        if callable(writer): writer(duplicate)

        target_candidate=self._find_or_copy_candidate(source_candidate,duplicate.project_id)
        self._remap_target_candidate_source(source_candidate,target_candidate,source_project.project_id,duplicate.project_id)
        source_segments=self.shorts.segments(source_candidate.id)
        self._materialize_sequence(source_candidate,target_candidate,source_project.project_id,duplicate.project_id)
        if source_candidate.source_type_code not in {"scenes","news","story"} and self.subtitle_ranges is not None:
            self.subtitle_ranges.trim_project_tracks(duplicate.project_id,source_segments)
        if source_candidate.source_type_code=="dub":
            self._materialize_dub_audio(source_candidate,target_candidate,source_segments,source_project,duplicate)
        target_candidate.status=ShortCandidateStatus.APPROVED
        target_candidate.metadata["derivedFromCandidateId"]=source_candidate.id
        target_candidate.metadata["derivedFromProjectId"]=source_project.project_id
        self.shorts.save_candidate(target_candidate,self.shorts.segments(target_candidate.id))
        meta=ShortProject(
            project_id=duplicate.project_id,source_type=source_candidate.source_type_code,source_id=target_candidate.source_id,
            target_duration_ms=int(source_candidate.metadata.get("targetDurationMs",source_candidate.duration_ms) or source_candidate.duration_ms),
            target_aspect_ratio=target_aspect_ratio,language=duplicate.language,platform=platform,style=style,status=ShortProjectStatus.REVIEW,
            source_project_id=source_project.project_id,source_entity_ids=list(source_candidate.source_entity_ids),source_fingerprint=source_candidate.source_fingerprint,
            metadata={"sourceCandidateId":source_candidate.id,"candidateId":target_candidate.id,"independent":True,"sourceWorkflow":str(source_project.workflow),"sourceProjectUpdatedAt":source_project.updated_at,**({"primaryAudioOverride":target_candidate.metadata.get("primaryAudioOverride")} if target_candidate.metadata.get("primaryAudioOverride") else {})},
        )
        self.shorts.save_project(meta)
        return duplicate,target_candidate

    def _find_or_copy_candidate(self, source, target_project_id: str):
        for item in self.shorts.list_candidates(target_project_id):
            if item.source_fingerprint==source.source_fingerprint and item.title==source.title:
                return item
        # The general project duplication patch may be unavailable in tests; preserve a safe fallback.
        return self.shorts.duplicate_candidate(source.project_id,source.id,target_project_id=target_project_id)

    def _materialize_sequence(self, source_candidate, target_candidate, source_project_id: str, target_project_id: str) -> None:
        source_segments=self.shorts.segments(source_candidate.id)
        if not source_segments: raise ShortCandidateInvalid("Short candidate has no selected ranges.")
        scene_types={"scenes","news","story"}
        if source_candidate.source_type_code in scene_types:
            self._keep_selected_scenes(source_candidate,target_project_id)
        else:
            self._build_range_scenes(source_candidate,source_segments,source_project_id,target_project_id)
        target_scenes=self.scene_repository.list_for_project(target_project_id)
        for scene in target_scenes:
            scene.metadata["shortCandidateId"]=target_candidate.id
            scene.metadata["shortSourceProjectId"]=source_project_id
            scene.metadata["shortSourceFingerprint"]=source_candidate.source_fingerprint
            self.scene_repository.update(scene)
            self.reframe.apply_preset(target_project_id,scene.id,"center")
        if source_candidate.hook.strip() and target_scenes:
            overlay=self.scenes.add_text_overlay(target_project_id,target_scenes[0].id,source_candidate.hook.strip(),"headline")
            self.scenes.update_overlay(target_project_id,target_scenes[0].id,overlay.id,{"endOffsetMs":min(3000,target_scenes[0].duration_ms)})

    def _keep_selected_scenes(self, candidate, target_project_id: str) -> None:
        source_scenes=self.scene_repository.list_for_project(candidate.project_id); target_scenes=self.scene_repository.list_for_project(target_project_id)
        source_order_by_id={scene.id:scene.order for scene in source_scenes}; wanted_orders={source_order_by_id[x] for x in candidate.source_entity_ids if x in source_order_by_id}
        if not wanted_orders: raise ShortCandidateInvalid("Selected source scenes are no longer available.")
        for scene in list(target_scenes):
            if scene.order not in wanted_orders:self.scenes.delete_scene(target_project_id,scene.id)
        # Remaining scenes are already independent copies with News/Story overlays/provenance and speaker relations remapped by existing services.

    def _build_range_scenes(self, candidate, segments, source_project_id: str, target_project_id: str) -> None:
        for scene in list(self.scene_repository.list_for_project(target_project_id)):
            self.scenes.delete_scene(target_project_id,scene.id)
        source_media_id=self._source_media_id(candidate)
        target_media_id=self._map_media(source_project_id,target_project_id,source_media_id)
        if not target_media_id: raise ShortSourceMissing("The source video for this Short is unavailable in the derived project.")
        for order,segment in enumerate(segments):
            duration=segment.duration_ms; scene=self.scenes.add_scene(target_project_id,f"Short Clip {order+1}",duration)
            self.scenes.assign_media(target_project_id,scene.id,target_media_id,fit_mode="fill")
            asset=self.media.get_by_id(target_media_id)
            if asset is not None and asset.type=="video": self.scenes.set_video_range(target_project_id,scene.id,segment.source_start_ms,segment.source_end_ms)
            scene=self.scene_repository.get(scene.id)
            if scene is not None:
                scene.metadata["shortSourceRange"]={"startMs":segment.source_start_ms,"endMs":segment.source_end_ms,"sourceEntityId":segment.source_entity_id}
                scene.metadata["shortRippleIndex"]=order; self.scene_repository.update(scene)


    def _materialize_dub_audio(self, source_candidate, target_candidate, segments, source_project, target_project) -> None:
        if self.dubbing is None or self.short_audio is None:return
        output=self.dubbing.latest_output(source_project.project_id,"final_mix")
        if output is None or output.status_code!="ready":return
        source_path=Path(output.file_path)
        if not source_path.is_file():return
        destination=Path(target_project.project_path)/"audio"/"shorts"/f"{target_candidate.id}-dub.wav"
        path=self.short_audio.assemble(source_path,segments,destination)
        target_candidate.metadata["primaryAudioOverride"]=str(path)
        target_candidate.metadata["sourceDubOutputId"]=output.id
        target_candidate.metadata["dubLanguage"]=output.target_language
        self.shorts.save_candidate(target_candidate,self.shorts.segments(target_candidate.id))

    def _remap_target_candidate_source(self, source_candidate, target_candidate, source_project_id: str, target_project_id: str) -> None:
        target_candidate.metadata["sourceOriginalId"]=source_candidate.source_id
        if source_candidate.source_type_code in {"video","manual","dub"}:
            source_media=str(source_candidate.metadata.get("mediaId",source_candidate.source_id) or source_candidate.source_id)
            mapped=self._map_media(source_project_id,target_project_id,source_media)
            if mapped:
                target_candidate.source_id=mapped; target_candidate.metadata["mediaId"]=mapped
        elif source_candidate.source_type_code=="transcript":
            mapped=self._map_transcript(source_project_id,target_project_id,source_candidate.source_id)
            if mapped: target_candidate.source_id=mapped
        elif source_candidate.source_type_code in {"scenes","news","story"}:
            target_candidate.source_id=target_project_id
        self.shorts.save_candidate(target_candidate,self.shorts.segments(target_candidate.id))

    def _map_transcript(self, source_project_id: str, target_project_id: str, transcript_id: str) -> str:
        source=self.transcripts.get(transcript_id)
        if source is None or source.project_id!=source_project_id:return ""
        targets=self.transcripts.list_for_project(target_project_id)
        # Existing duplication preserves transcript model/source fingerprints while remapping IDs.
        key=(source.model_id,source.model_version,source.language_mode,source.source_fingerprint,int(source.duration_ms or 0))
        for item in targets:
            if (item.model_id,item.model_version,item.language_mode,item.source_fingerprint,int(item.duration_ms or 0))==key:return item.id
        # Conservative order fallback for legacy transcripts without a fingerprint.
        sources=self.transcripts.list_for_project(source_project_id)
        try:index=next(i for i,x in enumerate(sources) if x.id==transcript_id)
        except StopIteration:return ""
        return targets[index].id if index<len(targets) else ""

    def _source_media_id(self, candidate) -> str:
        if candidate.source_type_code in {"video","manual","dub"}:
            return str(candidate.metadata.get("mediaId",candidate.source_id) or candidate.source_id)
        if candidate.source_type_code=="transcript":
            transcript=self.transcripts.get(candidate.source_id); return transcript.media_id if transcript else ""
        return str(candidate.metadata.get("mediaId","") or "")

    def _map_media(self, source_project_id: str, target_project_id: str, source_media_id: str) -> str:
        source=self.media.get_by_id(source_media_id)
        if source is None or source.project_id!=source_project_id:return ""
        candidates=self.media.list_by_project(target_project_id)
        key=(source.name,source.original_path,source.type,int(source.file_size),int(source.duration_ms or 0))
        for item in candidates:
            if (item.name,item.original_path,item.type,int(item.file_size),int(item.duration_ms or 0))==key:return item.id
        return ""

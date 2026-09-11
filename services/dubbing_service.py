from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from domain.dub_audio import DubAudioOutput
from domain.dub_mix_settings import DubMixSettings
from domain.dub_segment import DubAudioStatus, DubSegment, DubTimingStatus, dub_text_hash
from domain.dubbing_errors import DubGenerationError, DubTranslationMissing, DubVoiceMissing
from domain.dubbing_project import DubbingProject, DubbingProjectStatus
from domain.generated_audio import GeneratedAudio
from domain.project import utc_now_iso
from engines.tts.types import TTSRequest
from services.dubbing_alignment_service import DubbingAlignmentService
from services.dubbing_audio_service import DubbingAudioService
from storage.repositories.dubbing_repository import DubbingRepository


class DubbingService:
    """Phase 21 orchestration. Existing STT/Translation/Voice/TTS services remain authoritative."""

    def __init__(self, repository: DubbingRepository, project_repository, translation_repository,
                 generated_audio_repository, voice_service, tts_service,
                 alignment_service: DubbingAlignmentService, audio_service: DubbingAudioService,
                 logger: logging.Logger | None = None, media_repository=None) -> None:
        self.repository=repository; self.project_repository=project_repository
        self.translation_repository=translation_repository; self.generated_audio_repository=generated_audio_repository
        self.voice_service=voice_service; self.tts_service=tts_service; self.alignment=alignment_service
        self.audio=audio_service; self.logger=logger or logging.getLogger("sp_video_studio.dubbing")
        self.media_repository=media_repository

    def ensure_project(self, project_id: str, *, source_language: str="auto", target_language: str="km") -> DubbingProject:
        item=self.repository.get_project(project_id)
        if item is None:
            item=DubbingProject(project_id=project_id,source_language=source_language,target_language=target_language)
            self.repository.save_project(item); self.repository.save_mix_settings(DubMixSettings(project_id=project_id))
        return item

    def assign_source(self, project_id: str, media_id: str, source_language: str, target_language: str) -> DubbingProject:
        if self.media_repository is not None:
            media=self.media_repository.get_by_id(media_id)
            if media is None or media.project_id != project_id:
                raise ValueError("Choose a video from this project.")
            if getattr(media,"type","") != "video":
                raise ValueError("Translate & Dub requires video media in Phase 21.")
        item=self.ensure_project(project_id,source_language=source_language,target_language=target_language)
        changed=item.source_media_id and item.source_media_id != media_id
        item.source_media_id=media_id; item.source_language=source_language; item.target_language=target_language
        item.validate()
        if changed:
            item.status=DubbingProjectStatus.OUTDATED; self.repository.mark_outputs_outdated(project_id)
            for segment in self.repository.segments(project_id):
                if not segment.locked: segment.audio_status=DubAudioStatus.OUTDATED; self.repository.save_segment(segment)
        return self.repository.save_project(item)

    def link_transcript(self, project_id: str, transcript_id: str) -> DubbingProject:
        item=self.ensure_project(project_id); item.transcript_id=transcript_id; item.status=DubbingProjectStatus.TRANSCRIPT_REVIEW
        return self.repository.save_project(item)

    def link_translation(self, project_id: str, translation_id: str) -> DubbingProject:
        item=self.ensure_project(project_id); item.translation_id=translation_id; item.status=DubbingProjectStatus.TRANSLATION_REVIEW
        return self.repository.save_project(item)

    def sync_translation_segments(self, project_id: str, translation_segments: list[Any]) -> list[DubSegment]:
        project=self.ensure_project(project_id)
        if not project.translation_id: raise DubTranslationMissing("Review or create the target-language translation before generating dub audio.")
        existing={s.translation_segment_id:s for s in self.repository.segments(project_id) if s.translation_segment_id}
        result:list[DubSegment]=[]
        for row in sorted(translation_segments,key=lambda s:int(getattr(s,"order",0))):
            translated=str(getattr(row,"translated_text","") or "").strip()
            source_start=int(getattr(row,"start_ms",0) or 0); source_end=int(getattr(row,"end_ms",source_start) or source_start)
            source_segment_id=str(getattr(row,"source_segment_id","") or "")
            translation_segment_id=str(getattr(row,"id",getattr(row,"segment_id","")))
            source_hash=str(getattr(row,"source_hash","") or "")
            item=existing.get(translation_segment_id)
            if item is None:
                item=DubSegment(project_id=project_id,source_transcript_segment_id=source_segment_id,
                                translation_segment_id=translation_segment_id,order=int(getattr(row,"order",0)),
                                source_start_ms=source_start,source_end_ms=source_end,target_text=translated,source_hash=source_hash,
                                metadata={"translationReviewed":bool(getattr(row,"reviewed",False))})
            else:
                changed=(item.target_text != translated or item.source_start_ms != source_start or item.source_end_ms != source_end)
                item.order=int(getattr(row,"order",0)); item.source_transcript_segment_id=source_segment_id
                item.source_start_ms=source_start; item.source_end_ms=source_end; item.source_hash=source_hash
                item.metadata["translationReviewed"]=bool(getattr(row,"reviewed",False))
                if item.target_text != translated:
                    item.target_text=translated; item.user_modified=True
                if changed and item.generated_audio_path and not item.locked:
                    item.audio_status=DubAudioStatus.OUTDATED; item.timing_status=DubTimingStatus.NEEDS_REVIEW
            self.repository.save_segment(item); result.append(item)
        if any(s.audio_status_code == DubAudioStatus.OUTDATED.value for s in result): self.repository.mark_outputs_outdated(project_id)
        return result

    def set_project_voice(self, project_id: str, voice_id: str) -> DubbingProject:
        self.voice_service.get(voice_id)
        project=self.ensure_project(project_id); old=project.target_voice_id; project.target_voice_id=voice_id
        if old and old != voice_id:
            for segment in self.repository.segments(project_id):
                if not segment.voice_id and segment.generated_audio_path and not segment.locked:
                    segment.audio_status=DubAudioStatus.OUTDATED; segment.metadata["outdatedReason"]="voice_changed"; self.repository.save_segment(segment)
            self.repository.mark_outputs_outdated(project_id)
        return self.repository.save_project(project)

    def set_segment_voice(self, project_id: str, segment_id: str, voice_id: str) -> DubSegment:
        if voice_id: self.voice_service.get(voice_id)
        item=self._segment(project_id,segment_id); changed=item.voice_id != voice_id; item.voice_id=voice_id
        if changed and item.generated_audio_path: item.audio_status=DubAudioStatus.OUTDATED; item.metadata["outdatedReason"]="voice_changed"
        self.repository.mark_outputs_outdated(project_id); return self.repository.save_segment(item)

    def update_timing(self, project_id: str, segment_id: str, *, timing_mode: str | None=None,
                      start_offset_ms: int | None=None, allow_overlap: bool=False) -> DubSegment:
        item=self._segment(project_id,segment_id)
        if timing_mode is not None: item.timing_mode=timing_mode
        if start_offset_ms is not None: item.start_offset_ms=self.alignment.validate_offset(item,start_offset_ms,allow_overlap=allow_overlap)
        self.alignment.apply_analysis(item); item.user_modified=True; self.repository.mark_outputs_outdated(project_id)
        return self.repository.save_segment(item)

    def lock_segment(self, project_id: str, segment_id: str, locked: bool=True) -> DubSegment:
        item=self._segment(project_id,segment_id); item.locked=locked; return self.repository.save_segment(item)

    def generation_candidates(self, project_id: str, selected_ids: set[str] | None=None) -> list[DubSegment]:
        allowed={DubAudioStatus.PENDING.value,DubAudioStatus.OUTDATED.value,DubAudioStatus.FAILED.value,DubAudioStatus.CANCELLED.value}
        return [s for s in self.repository.segments(project_id) if not s.locked and s.audio_status_code in allowed and (selected_ids is None or s.id in selected_ids)]

    def generate_segment(self, project_id: str, segment_id: str, *, cancellation=None, force: bool=False) -> DubSegment:
        project=self.ensure_project(project_id); segment=self._segment(project_id,segment_id)
        if segment.locked and not force: return segment
        text=segment.target_text.strip()
        if not text: raise DubTranslationMissing("Review or create the target-language translation before generating dub audio.")
        voice_id=segment.voice_id or project.target_voice_id
        if not voice_id: raise DubVoiceMissing("Choose a target voice.")
        project_entry=self.project_repository.get_by_id(project_id)
        if project_entry is None: raise KeyError("Project not found.")
        voice_config=self.voice_service.voice_config(voice_id)
        model_version=""
        try:
            installation=self.tts_service.model_service.repository.get(self.tts_service.MODEL_ID)
            model_version=str(getattr(installation,"version","") or "") if installation else ""
        except Exception: pass
        settings={"timingMode":segment.timing_mode_code}
        generation_hash=dub_text_hash(text,asdict(voice_config) if is_dataclass(voice_config) else str(voice_config),model_version,settings)
        root=Path(project_entry.project_path)/"audio"/"dubbing"; root.mkdir(parents=True,exist_ok=True)
        final_path=root/f"{segment.id}.wav"; temp_path=root/f".{segment.id}.new.wav"
        old=(segment.generated_audio_id,segment.generated_audio_path,segment.generated_duration_ms,segment.generation_hash,segment.audio_status)
        segment.audio_status=DubAudioStatus.GENERATING; self.repository.save_segment(segment)
        try:
            request=TTSRequest(project_id=project_id,text=text,language=project.target_language,output_path=temp_path,
                               voice_config=voice_config,metadata={"workflow":"dubbing","dubSegmentId":segment.id})
            result=self.tts_service.generate(request,cancellation)
            if not Path(result.output_path).is_file(): raise DubGenerationError("Generated dub audio was not created.")
            Path(result.output_path).replace(final_path)
            audio=GeneratedAudio(project_id=project_id,engine=self.tts_service.ENGINE_ID,model_id=self.tts_service.MODEL_ID,
                                 language=project.target_language,voice_mode=str(getattr(voice_config,"mode_code",getattr(voice_config,"mode","designed"))),
                                 text_hash=generation_hash,file_path=str(final_path),duration_ms=int(result.duration_ms),sample_rate=int(result.sample_rate),
                                 channels=int(result.channels),voice_config={"voiceId":voice_id},generation_settings=settings,
                                 metadata={"workflow":"dubbing","dubSegmentId":segment.id,"modelVersion":result.model_version})
            self.generated_audio_repository.create(audio)
            segment.generated_audio_id=audio.id; segment.generated_audio_path=str(final_path); segment.generated_duration_ms=int(result.duration_ms)
            segment.generation_hash=generation_hash; segment.audio_status=DubAudioStatus.READY; segment.metadata.pop("regenerationError",None)
            self.alignment.apply_analysis(segment); self.repository.mark_outputs_outdated(project_id)
            return self.repository.save_segment(segment)
        except Exception as exc:
            temp_path.unlink(missing_ok=True)
            if old[1]:
                segment.generated_audio_id,segment.generated_audio_path,segment.generated_duration_ms,segment.generation_hash,segment.audio_status=old
                segment.metadata["regenerationError"]=str(exc)
            else:
                segment.audio_status=DubAudioStatus.FAILED; segment.metadata["generationError"]=str(exc)
            self.repository.save_segment(segment); self.logger.exception("Dub generation failed for segment %s",segment.id)
            raise

    def register_manual_audio(self, project_id: str, segment_id: str, source_path: str, duration_ms: int) -> DubSegment:
        item=self._segment(project_id,segment_id)
        project_entry=self.project_repository.get_by_id(project_id)
        if project_entry is None: raise KeyError("Project not found.")
        source=Path(source_path).expanduser().resolve()
        if not source.is_file() or source.stat().st_size <= 0:
            raise ValueError("Replacement dub audio could not be found.")
        if source.suffix.lower() not in {".wav",".mp3",".m4a",".aac",".flac",".ogg",".opus"}:
            raise ValueError("Unsupported replacement dub audio format.")
        root=Path(project_entry.project_path)/"audio"/"dubbing"/"manual"; root.mkdir(parents=True,exist_ok=True)
        target=root/f"{item.id}{source.suffix.lower()}"
        temp=root/f".{item.id}.new{source.suffix.lower()}"
        shutil.copy2(source,temp); temp.replace(target)
        item.generated_audio_id=""; item.generated_audio_path=str(target)
        item.generated_duration_ms=max(0,int(duration_ms)); item.audio_status=DubAudioStatus.READY
        item.generation_hash=self._manual_hash(item,str(target)); self.alignment.apply_analysis(item); self.repository.mark_outputs_outdated(project_id)
        return self.repository.save_segment(item)

    def build_final_mix(self, project_id: str, *, source_video_path: str, source_fingerprint: str, duration_ms: int) -> DubAudioOutput:
        project=self.ensure_project(project_id); segments=self.repository.segments(project_id); settings=self.repository.get_mix_settings(project_id)
        if not segments: raise DubGenerationError("Create dub segments before rebuilding the audio mix.")
        unavailable=[s for s in segments if s.audio_status_code != DubAudioStatus.READY.value or not s.generated_audio_path or not Path(s.generated_audio_path).is_file()]
        if unavailable: raise DubGenerationError(f"{len(unavailable)} dub segment(s) still need generation or regeneration.")
        overlaps=self.alignment.detect_overlaps(segments)
        if overlaps: raise DubGenerationError("Resolve overlapping spoken dub segments before rebuilding the audio mix.")
        entry=self.project_repository.get_by_id(project_id)
        if entry is None: raise KeyError("Project not found.")
        root=Path(entry.project_path)/"audio"/"dubbing"/"final"; root.mkdir(parents=True,exist_ok=True)
        narration=root/f"{project.target_language}-narration.wav"; mixed=root/f"{project.target_language}-mix.wav"
        self.audio.build_narration_track(segments,duration_ms,narration)
        self.audio.build_final_mix(source_video_path,narration,duration_ms,settings,segments,mixed)
        fingerprint=self.audio.final_mix_fingerprint(source_fingerprint,segments,settings)
        output=DubAudioOutput(project_id=project_id,source_media_id=project.source_media_id,target_language=project.target_language,
                              voice_profile_id=project.target_voice_id,file_path=str(mixed),duration_ms=duration_ms,fingerprint=fingerprint,
                              settings=settings.to_dict(),metadata={"narrationPath":str(narration),"originalSpeechMayRemain":settings.mode_code!="replace"})
        self.repository.save_output(output); project.status=DubbingProjectStatus.REVIEW; self.repository.save_project(project); return output


    def build_final_mix_for_project(self, project_id: str) -> DubAudioOutput:
        if self.media_repository is None:
            raise DubGenerationError("Source media lookup is unavailable.")
        project=self.ensure_project(project_id)
        media=self.media_repository.get_by_id(project.source_media_id) if project.source_media_id else None
        if media is None or media.project_id != project_id or getattr(media,"type","") != "video":
            raise DubGenerationError("Choose a valid source video before rebuilding the audio mix.")
        source_path=Path(media.project_path)
        if not source_path.is_file():
            raise DubGenerationError("The source video could not be found.")
        duration_ms=int(media.duration_ms or 0)
        if duration_ms <= 0:
            raise DubGenerationError("The source video duration is unavailable.")
        stat=source_path.stat()
        source_fingerprint=hashlib.sha256(f"{media.id}\0{stat.st_size}\0{stat.st_mtime_ns}".encode("utf-8")).hexdigest()
        expected=self.audio.final_mix_fingerprint(source_fingerprint,self.repository.segments(project_id),self.repository.get_mix_settings(project_id))
        current=self.repository.latest_output(project_id,"final_mix")
        if current and current.status_code == "ready" and current.fingerprint == expected and Path(current.file_path).is_file():
            return current
        return self.build_final_mix(project_id,source_video_path=str(source_path),source_fingerprint=source_fingerprint,duration_ms=duration_ms)

    def reset_audio(self, project_id: str) -> None:
        for value in self.repository.reset_audio(project_id):
            try: Path(value).unlink(missing_ok=True)
            except OSError: pass

    def _segment(self, project_id: str, segment_id: str) -> DubSegment:
        item=self.repository.segment(project_id,segment_id)
        if item is None: raise KeyError("Dub segment not found.")
        return item

    @staticmethod
    def _manual_hash(segment: DubSegment, path: str) -> str:
        payload=f"manual\0{segment.target_text}\0{path}\0{segment.generated_duration_ms}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

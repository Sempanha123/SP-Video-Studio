from __future__ import annotations

import logging
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from domain.project import utc_now_iso
from domain.render_job import RenderJob, RenderJobStatus
from domain.render_output import RenderOutput
from domain.render_preset import BUILTIN_RENDER_PRESETS, RenderPreset
from domain.render_settings import RenderSettings
from media.ffmpeg import FFmpegRunner
from media.probe import FFprobeService
from media.thumbnails import ThumbnailService
from rendering.encoder_registry import EncoderRegistry
from rendering.errors import RenderCancelled, RenderFFmpegMissing, RenderValidationError
from rendering.output_validator import OutputValidator
from rendering.render_plan import RenderPlan, expected_sequence_duration_ms
from rendering.renderer import FFmpegRenderer
from rendering.subtitle_renderer import SubtitleRenderer
from rendering.temp_manager import RenderTempManager
from services.project_service import safe_folder_slug
from services.render_validation_service import RenderIssue, RenderValidationService
from services.scene_service import SceneService
from services.subtitle_service import SubtitleService
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.render_job_repository import RenderJobRepository
from storage.repositories.render_output_repository import RenderOutputRepository
from workers.cancellation import CancellationToken


class RenderService:
    def __init__(self,project_repository:ProjectRepository,scene_service:SceneService,subtitle_service:SubtitleService,job_repository:RenderJobRepository,output_repository:RenderOutputRepository,ffmpeg_provider:Callable[[],str|Path|None],ffprobe_provider:Callable[[],str|Path|None],thumbnail_service:ThumbnailService,validation:RenderValidationService|None=None,logger:logging.Logger|None=None) -> None:
        self.projects=project_repository; self.scenes=scene_service; self.subtitles=subtitle_service; self.jobs=job_repository; self.outputs=output_repository; self.ffmpeg_provider=ffmpeg_provider; self.ffprobe_provider=ffprobe_provider; self.thumbnail_service=thumbnail_service; self.validation=validation or RenderValidationService(); self.logger=logger or logging.getLogger("sp_video_studio.render")
        self._runtime_path=""; self._runner:FFmpegRunner|None=None; self._encoders:EncoderRegistry|None=None; self._lock=threading.Lock()

    def presets(self)->tuple[RenderPreset,...]: return BUILTIN_RENDER_PRESETS

    def settings_for_preset(self,project_id:str,preset_id:str="")->RenderSettings:
        project=self._project(project_id); preset=next((p for p in BUILTIN_RENDER_PRESETS if p.id==preset_id),None)
        if preset is None:
            desired={"9:16":"vertical_full_hd","16:9":"landscape_full_hd","1:1":"square_full_hd"}.get(project.aspect_ratio,"landscape_full_hd"); preset=next(p for p in BUILTIN_RENDER_PRESETS if p.id==desired)
        return RenderSettings(preset.width,preset.height,project.fps,quality=preset.quality_profile)

    def encoder_options(self)->list[dict]:
        _,encoders,_=self._runtime(); return [{"id":x.encoder_id,"name":x.name,"hardware":x.hardware,"available":x.available,"runtimeReady":x.runtime_ready} for x in encoders.list(validate_hardware=False)]

    def build_plan(self,project_id:str,settings:RenderSettings,*,preset_id:str="custom",job_id:str="") -> RenderPlan:
        project=self._project(project_id); runner,encoders,version=self._runtime(); settings.validate()
        specs=[]
        for scene in self.scenes.list_scenes(project_id):
            if not scene.enabled: continue
            specs.append(self.scenes.build_scene_render_spec(project_id,scene.id))
        output=Path(settings.output_path) if settings.output_path else self._default_output(project,settings)
        if output.exists(): output=self._collision_path(output)
        settings.output_path=str(output)
        temp=Path(project.project_path)/"cache"/"render"/(job_id or "preview-plan")
        expected=expected_sequence_duration_ms(specs)
        return RenderPlan(project_id,str(output),settings,specs,expected,str(temp),settings.subtitle_track_id,ffmpeg_version=version,metadata={"presetId":preset_id,"projectAspectRatio":project.aspect_ratio,"projectFps":project.fps})

    def validate_plan(self,plan:RenderPlan)->list[RenderIssue]:
        project=self._project(plan.project_id); _,encoders,_=self._runtime()
        issues=self.validation.validate(project_path=Path(project.project_path),scenes=plan.scenes,settings=plan.settings,encoders=encoders,output_path=Path(plan.output_path),ffmpeg_filters=encoders.capabilities.filters,project_aspect_ratio=project.aspect_ratio)
        if plan.subtitle_track_id:
            try:
                track, _, _ = self.subtitles.get(plan.project_id, plan.subtitle_track_id)
                if getattr(track, "status_code", "") in {"outdated", "source_missing"}:
                    issues.append(RenderIssue("warning", "subtitle_source_stale", "The selected subtitle track may be out of date with its source."))
            except Exception:
                issues.append(RenderIssue("error", "subtitle_missing", "The selected subtitle track could not be loaded."))
        return issues

    def render(self,project_id:str,settings:RenderSettings,*,preset_id:str="custom",cancellation:CancellationToken|None=None,progress_callback=None)->RenderOutput:
        if not self._lock.acquire(blocking=False): raise RenderValidationError("Another video is already rendering.")
        job=RenderJob(project_id=project_id,preset=preset_id,settings=settings.to_dict()); self.jobs.create(job); manager=None
        try:
            job.status=RenderJobStatus.VALIDATING; job.started_at=utc_now_iso(); self.jobs.update(job)
            plan=self.build_plan(project_id,settings,preset_id=preset_id,job_id=job.id); manager=RenderTempManager(self._project(project_id).project_path,job.id); manager.prepare(); plan.temp_directory=str(manager.root)
            issues=self.validate_plan(plan); blocking=self.validation.blocking(issues)
            if blocking: raise RenderValidationError("; ".join(i.message for i in blocking))
            job.expected_duration_ms=plan.expected_duration_ms; job.output_path=plan.output_path; job.settings=plan.settings.to_dict(); job.metadata.update({"snapshot":plan.snapshot(),"warnings":[i.message for i in issues if i.severity=="warning"]}); job.status=RenderJobStatus.PREPARING; self.jobs.update(job)
            runner,encoders,version=self._runtime(); renderer=FFmpegRenderer(runner,encoders,SubtitleRenderer(self.subtitles),logger=self.logger)
            job.status=RenderJobStatus.RENDERING; self.jobs.update(job)
            def on_progress(state):
                job.progress=max(job.progress,float(state.overall_progress)); job.metadata["stage"]=state.stage; job.metadata["speed"]=state.speed; job.metadata["sceneIndex"]=state.scene_index; self.jobs.update(job)
                if progress_callback: progress_callback(state)
            execution=renderer.render(plan,cancellation=cancellation,progress_callback=on_progress)
            job.status=RenderJobStatus.VALIDATING_OUTPUT; job.progress=.99; self.jobs.update(job)
            probe=FFprobeService(self.ffprobe_provider); validation=OutputValidator(probe).validate(execution.output_path,width=settings.width,height=settings.height,fps=settings.fps,expected_duration_ms=plan.expected_duration_ms,audio_expected=True)
            thumb_path=Path(self._project(project_id).project_path)/"thumbnails"/"renders"/f"{job.id}.jpg"; thumb=""
            try: thumb=str(self.thumbnail_service.generate_video_thumbnail(execution.output_path,thumb_path,duration_ms=validation.probe.duration_ms))
            except Exception: self.logger.info("Render thumbnail generation failed",exc_info=True)
            output=RenderOutput(project_id,job.id,str(execution.output_path),settings.width,settings.height,float(validation.probe.fps or settings.fps),int(validation.probe.duration_ms or plan.expected_duration_ms),str(validation.probe.codec or "h264"),str(validation.probe.audio_codec or ""),validation.file_size,thumb,metadata={"encoder":execution.encoder,"ffmpegVersion":version,"renderGraph":execution.graph,"snapshotSchemaVersion":plan.schema_version})
            self.outputs.create(output); job.status=RenderJobStatus.COMPLETED; job.progress=1.0; job.actual_duration_ms=output.duration_ms; job.completed_at=utc_now_iso(); job.metadata["actualEncoder"]=execution.encoder; self.jobs.update(job); self.logger.info("Render completed: %s",job.id)
            if manager and not settings.keep_temp: manager.cleanup()
            return output
        except RenderCancelled:
            job.status=RenderJobStatus.CANCELLED; job.completed_at=utc_now_iso(); job.error_message="Render cancelled."; self.jobs.update(job)
            if manager: manager.cleanup()
            raise
        except Exception as exc:
            job.status=RenderJobStatus.FAILED; job.completed_at=utc_now_iso(); job.error_message=str(exc)[-2000:]; self.jobs.update(job); self.logger.exception("Render failed: %s",job.id)
            if manager and not settings.keep_temp: manager.cleanup()
            raise
        finally:
            self._lock.release()

    def history(self,project_id:str,limit:int=20)->list[RenderOutput]: self._project(project_id); return self.outputs.list_for_project(project_id,limit)
    def jobs_history(self,project_id:str,limit:int=20)->list[RenderJob]: self._project(project_id); return self.jobs.list_for_project(project_id,limit)

    def delete_output(self,project_id:str,output_id:str)->None:
        project=self._project(project_id); item=self.outputs.get(output_id)
        if item is None or item.project_id!=project_id: raise KeyError("Render output not found.")
        path=Path(item.file_path).resolve(); managed=(Path(project.project_path)/"renders").resolve()
        if path!=managed and managed not in path.parents: raise RenderValidationError("Only project-managed render outputs can be deleted here.")
        self.outputs.delete_record(project_id,output_id); path.unlink(missing_ok=True)
        if item.thumbnail_path:
            thumb=Path(item.thumbnail_path).resolve(); root=(Path(project.project_path)/"thumbnails"/"renders").resolve()
            if root in thumb.parents: thumb.unlink(missing_ok=True)

    def _runtime(self)->tuple[FFmpegRunner,EncoderRegistry,str]:
        path=self.ffmpeg_provider()
        if not path: raise RenderFFmpegMissing("FFmpeg is required to render video. Configure it in Settings.")
        value=str(path)
        if self._runner is None or self._runtime_path!=value:
            self._runner=FFmpegRunner(value); caps=self._runner.discover_capabilities(); self._encoders=EncoderRegistry(self._runner,caps); self._runtime_path=value
        assert self._encoders is not None
        return self._runner,self._encoders,self._encoders.capabilities.version

    def _project(self,project_id:str):
        item=self.projects.get_by_id(project_id)
        if item is None: raise KeyError("Project not found.")
        return item

    @staticmethod
    def _collision_path(path:Path)->Path:
        for i in range(1,10000):
            candidate=path.with_name(f"{path.stem}_{i:03d}{path.suffix}")
            if not candidate.exists(): return candidate
        raise RenderValidationError("Could not choose a unique output filename.")

    @staticmethod
    def _default_output(project,settings:RenderSettings)->Path:
        root=Path(project.project_path)/"renders"; root.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d"); base=f"{safe_folder_slug(project.title)}_{settings.width}x{settings.height}_{stamp}_001.mp4"; path=root/base
        return path if not path.exists() else RenderService._collision_path(path)

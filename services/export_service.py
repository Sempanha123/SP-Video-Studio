from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from domain.export_request import ExportRequest
from domain.render_output import RenderOutput
from domain.render_settings import RenderSettings
from services.export_filename_service import ExportFilenameService, ExportOutputConflict
from services.export_preset_service import ExportPresetService
from services.export_validation_service import ExportSummary, ExportValidationService
from services.render_service import RenderService
from services.render_validation_service import RenderIssue
from services.subtitle_service import SubtitleService
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.render_output_repository import RenderOutputRepository
from workers.cancellation import CancellationToken


class ExportError(RuntimeError):
    pass


class ExportInvalidPreset(ExportError):
    pass


class ExportInvalidFilename(ExportError):
    pass


class ExportPathUnavailable(ExportError):
    pass


class ExportService:
    """Polished export layer above Phase 15 RenderService.

    It owns preset/request/path/history behavior only. FFmpeg execution remains entirely in
    RenderService/FFmpegRenderer.
    """

    AUDIO_BITRATES={"standard":"160k","high":"224k"}

    def __init__(self,projects:ProjectRepository,render_service:RenderService,subtitle_service:SubtitleService,preset_service:ExportPresetService,filename_service:ExportFilenameService,validation_service:ExportValidationService,outputs:RenderOutputRepository,logger:logging.Logger|None=None)->None:
        self.projects=projects; self.render_service=render_service; self.subtitles=subtitle_service; self.presets=preset_service; self.filenames=filename_service; self.validation=validation_service; self.outputs=outputs; self.logger=logger or logging.getLogger("sp_video_studio.export")

    def default_request(self,project_id:str,preset_id:str="")->ExportRequest:
        project=self._project(project_id); profile=self.presets.profile(project_id)
        if not preset_id and profile and profile.settings:
            try:
                req=ExportRequest.from_dict(profile.settings)
                req.project_id=project_id
                return req
            except Exception:
                pass
        if not preset_id:
            preset_id={"9:16":"generic_vertical","16:9":"generic_landscape","1:1":"generic_square"}.get(project.aspect_ratio,"generic_landscape")
        preset=self.presets.get(preset_id)
        default_track=""
        try:
            tracks=self.subtitles.list_tracks(project_id)
            default=next((t for t in tracks if getattr(t,"is_default",False)),None)
            default_track=default.id if default else ""
        except Exception:
            default_track=""
        mode=preset.subtitle_mode if default_track else "none"
        project_folder=Path(project.project_path)/"renders"; project_folder.mkdir(parents=True,exist_ok=True)
        filename=self.filenames.sanitize(f"{project.title}_{preset.name}.mp4")
        fps=project.fps if preset.metadata.get("useProjectFps") else preset.fps
        return ExportRequest(project_id,preset.id,preset.width,preset.height,fps,preset.quality_profile,"auto",mode,default_track,str(project_folder),filename,"keep_both","fill",True,"high",False,True)

    def apply_preset(self,request:ExportRequest,preset_id:str)->ExportRequest:
        preset=self.presets.get(preset_id); request.preset_id=preset.id; request.width=preset.width; request.height=preset.height; request.fps=preset.fps; request.quality=preset.quality_profile
        request.subtitle_mode=preset.subtitle_mode if request.subtitle_track_id else "none"
        request.filename=self.filenames.sanitize(f"{self._project(request.project_id).title}_{preset.name}.mp4")
        request.metadata={**request.metadata,"platform":preset.platform}
        return request

    def resolve_output(self,request:ExportRequest)->Path:
        request.validate()
        try: root=self.validation.validate_folder(request.output_folder,create=True)
        except Exception as exc: raise ExportPathUnavailable(str(exc)) from exc
        try: return self.filenames.resolve(root,request.filename,request.overwrite_policy)
        except ExportOutputConflict: raise
        except Exception as exc: raise ExportInvalidFilename(str(exc)) from exc

    def build_plan(self,request:ExportRequest):
        request.validate(); project=self._project(request.project_id); output=self.resolve_output(request)
        burn_track=request.subtitle_track_id if request.subtitle_mode=="burn" else ""
        settings=RenderSettings(
            request.width,request.height,request.fps,request.encoder,request.quality,burn_track,str(output),
            audio_codec="aac",audio_bitrate=self.AUDIO_BITRATES.get(request.audio_quality,"224k"),keep_temp=request.keep_temp,
            include_audio=request.audio_enabled,
            metadata={
                "exportPresetId":request.preset_id,
                "subtitleMode":request.subtitle_mode,
                "externalOutput":not self.filenames.is_managed(project.project_path,output),
                "overwritePolicy":request.overwrite_policy,
                "fitMode":request.fit_mode,
                "exportRequest":request.to_dict(),
            },
        )
        plan=self.render_service.build_plan(request.project_id,settings,preset_id=request.preset_id or "custom")
        # Export-level aspect conversion is a snapshot concern; it never mutates scene data.
        for spec in plan.scenes:
            visual=spec.get("visual")
            if isinstance(visual,dict) and visual:
                visual["fitMode"]=request.fit_mode
        plan.metadata.update({"exportPresetId":request.preset_id,"exportRequest":request.to_dict(),"exportOutputManaged":not settings.metadata["externalOutput"]})
        return plan

    def validate(self,request:ExportRequest)->tuple[list[RenderIssue],ExportSummary]:
        project=self._project(request.project_id); preset=self.presets.get(request.preset_id); plan=self.build_plan(request)
        issues=self.render_service.validate_plan(plan)
        issues.extend(self.validation.export_issues(request,project_aspect_ratio=project.aspect_ratio,preset_max_duration_ms=preset.recommended_max_duration_ms,expected_duration_ms=plan.expected_duration_ms))
        estimate=self.validation.estimate_size(plan.expected_duration_ms,request.width,request.height,request.quality,request.audio_enabled,request.audio_quality)
        return issues,ExportSummary(plan.expected_duration_ms,estimate,plan.output_path,self.filenames.is_managed(project.project_path,plan.output_path))

    def export(self,request:ExportRequest,*,cancellation:CancellationToken|None=None,progress_callback=None)->RenderOutput:
        request.validate(); issues,_=self.validate(request)
        blocking=[i for i in issues if i.severity=="error"]
        if blocking: raise ExportError(blocking[0].message)
        # Re-resolve immediately before the immutable render snapshot so Keep Both remains race-safe.
        output=self.resolve_output(request); request.filename=output.name; request.output_folder=str(output.parent)
        burn_track=request.subtitle_track_id if request.subtitle_mode=="burn" else ""
        project=self._project(request.project_id)
        settings=RenderSettings(request.width,request.height,request.fps,request.encoder,request.quality,burn_track,str(output),audio_codec="aac",audio_bitrate=self.AUDIO_BITRATES.get(request.audio_quality,"224k"),keep_temp=request.keep_temp,include_audio=request.audio_enabled,metadata={"exportPresetId":request.preset_id,"subtitleMode":request.subtitle_mode,"externalOutput":not self.filenames.is_managed(project.project_path,output),"overwritePolicy":request.overwrite_policy,"fitMode":request.fit_mode,"exportRequest":request.to_dict()})
        self.logger.info("Export requested preset=%s resolution=%sx%s encoder=%s output=%s",request.preset_id,request.width,request.height,request.encoder,"external" if settings.metadata["externalOutput"] else "managed")
        result=self.render_service.render(request.project_id,settings,preset_id=request.preset_id or "custom",cancellation=cancellation,progress_callback=progress_callback)
        external_files=[]
        if request.subtitle_mode.startswith("external_") and request.subtitle_track_id:
            fmt=request.subtitle_mode.removeprefix("external_")
            track,_,_=self.subtitles.get(request.project_id,request.subtitle_track_id)
            language=(f"{track.language}-{track.secondary_language}" if getattr(track,"is_bilingual",False) and track.secondary_language else track.language)
            destination=Path(result.file_path).with_name(f"{Path(result.file_path).stem}.{language}.{fmt}")
            external_files.append(str(self.subtitles.export(request.project_id,request.subtitle_track_id,fmt,destination)))
        result.metadata.update({"exportPresetId":request.preset_id,"externalOutput":settings.metadata["externalOutput"],"subtitleMode":request.subtitle_mode,"subtitleExportFiles":external_files,"exportRequest":request.to_dict()})
        self.outputs.update(result)
        if request.remember_for_project:self.presets.save_profile(request.project_id,request)
        self.logger.info("Export completed preset=%s",request.preset_id)
        return result

    def encoder_options(self)->list[dict]:
        rows=[{"id":"auto","name":"Auto","hardware":False,"available":True,"runtimeReady":True}]
        for item in self.render_service.encoder_options(validate_hardware=True):
            if not item.get("available"): continue
            if item.get("hardware") and item.get("runtimeReady") is not True: continue
            rows.append(item)
        return rows

    def subtitle_tracks(self,project_id:str)->list[dict]:
        self._project(project_id); rows=[]
        for track in self.subtitles.list_tracks(project_id):
            label=track.name
            if getattr(track,"is_bilingual",False) and getattr(track,"secondary_language",""):
                label=f"{label} ({track.language.upper()} + {track.secondary_language.upper()})"
            elif getattr(track,"language",""):
                label=f"{label} ({track.language.upper()})"
            rows.append({"id":track.id,"name":label,"language":track.language,"bilingual":track.is_bilingual,"default":track.is_default})
        return rows

    def history(self,project_id:str,limit:int=30)->list[RenderOutput]:
        self._project(project_id); return self.outputs.list_for_project(project_id,limit)

    def recent_exports(self,limit:int=12)->list[RenderOutput]:return self.outputs.list_recent(limit)

    def request_from_output(self,project_id:str,output_id:str)->ExportRequest:
        item=self.outputs.get(output_id)
        if item is None or item.project_id!=project_id: raise ExportError("Export history item could not be found.")
        data=item.metadata.get("exportRequest") if isinstance(item.metadata,dict) else None
        if not isinstance(data,dict): raise ExportError("This older render does not contain reusable export settings.")
        req=ExportRequest.from_dict(data); req.project_id=project_id; req.filename=Path(item.file_path).name; req.output_folder=str(Path(item.file_path).parent); req.overwrite_policy="keep_both"; return req

    def remove_history(self,project_id:str,output_id:str)->None:
        item=self.outputs.get(output_id)
        if item is None or item.project_id!=project_id: raise ExportError("Export history item could not be found.")
        self.outputs.delete_record(project_id,output_id)

    def delete_export(self,project_id:str,output_id:str,*,allow_external:bool=False)->None:
        project=self._project(project_id); item=self.outputs.get(output_id)
        if item is None or item.project_id!=project_id: raise ExportError("Export history item could not be found.")
        path=Path(item.file_path)
        external=bool(item.metadata.get("externalOutput",not self.filenames.is_managed(project.project_path,path)))
        if external and not allow_external: raise ExportError("This export is outside the managed project folder. Confirm external-file deletion explicitly.")
        if not external:
            self.render_service.delete_output(project_id,output_id)
        else:
            self.outputs.delete_record(project_id,output_id); path.unlink(missing_ok=True)
            if item.thumbnail_path: Path(item.thumbnail_path).unlink(missing_ok=True)
        for extra in item.metadata.get("subtitleExportFiles",[]) if isinstance(item.metadata,dict) else []:
            try:
                p=Path(str(extra))
                if p.parent.resolve()==path.parent.resolve(): p.unlink(missing_ok=True)
            except OSError: pass

    def _project(self,project_id:str):
        item=self.projects.get_by_id(project_id)
        if item is None: raise ExportError("Project could not be found.")
        return item

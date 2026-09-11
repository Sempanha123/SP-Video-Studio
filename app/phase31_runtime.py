from __future__ import annotations

"""Phase 31 performance layer over the existing Phase 30 architecture."""
import app.phase30_runtime as p30
from app.paths import AppPaths
from services.performance_profile_service import PerformanceProfileService
from services.performance_telemetry_service import PerformanceTelemetryService
from services.preview_request_service import PreviewRequestService
from services.subtitle_lookup_service import SubtitleLookupService
from services.thumbnail_request_service import ThumbnailRequestService
from ui.controllers.performance_controller import PerformanceController


def _install(container):
    p27=p30.p29.p27;p26=p27.p26;p25=p26.p25;p24=p25.p24
    try:paths=container.resolve(AppPaths)
    except Exception:paths=AppPaths.discover();paths.ensure()
    worker_pool=container.resolve(p24.WorkerPool)
    profiles=PerformanceProfileService(paths.settings)
    ai_resources=None
    try:
        from services.ai_resource_manager import AIResourceManager
        ai_resources=container.resolve(AIResourceManager)
        if hasattr(ai_resources,'set_profile'):ai_resources.set_profile(profiles.effective_profile())
    except Exception:pass
    telemetry=PerformanceTelemetryService(worker_pool,profiles)
    previews=PreviewRequestService(worker_pool)
    subtitles=SubtitleLookupService()
    thumbnails=None
    try:
        thumb=container.resolve(p24.ThumbnailService)
        thumbnails=ThumbnailRequestService(thumb,worker_pool)
    except Exception:pass
    for cls,obj in ((PerformanceProfileService,profiles),(PerformanceTelemetryService,telemetry),(PreviewRequestService,previews),(SubtitleLookupService,subtitles)):
        try:container.register_instance(cls,obj)
        except Exception:pass
    if thumbnails is not None:
        try:container.register_instance(ThumbnailRequestService,thumbnails)
        except Exception:pass

    # Hot playback lookup: build each track index once and rebuild only when the
    # subtitle track's updated_at changes. Final subtitle/render data is unchanged.
    mapping_cls=getattr(p24,'TimelineMappingService',None)
    if mapping_cls is not None and not getattr(mapping_cls.get_active_subtitle_cues,'_phase31_fast',False):
        original=mapping_cls.get_active_subtitle_cues
        def fast_active(self,project_id,project_ms):
            try:
                track=self.subtitles.default_for_project(project_id)
                if not track:return []
                key=str(track.id);version=str(getattr(track,'updated_at',''))
                return subtitles.active_repository(self.subtitles,key,int(project_ms),version)
            except Exception:
                return original(self,project_id,project_ms)
        fast_active._phase31_fast=True
        mapping_cls.get_active_subtitle_cues=fast_active

    return profiles,telemetry,previews,subtitles,thumbnails,ai_resources


def run()->int:
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return p30.run()
    original_extend=p30._extend_phase30
    registered={'done':False}
    def extend(container,cache,*,template_apply=None):
        result=original_extend(container,cache,template_apply=template_apply)
        profiles,telemetry,previews,subtitles,thumbnails,ai_resources=_install(container)
        if not registered['done']:
            class RuntimePerformanceController(PerformanceController):
                def __init__(self,parent=None):super().__init__(profiles,telemetry,ai_resources,worker_pool,parent)
            qmlRegisterSingletonType(RuntimePerformanceController,'SPVideoStudio.Phase31',1,0,'Performance')
            registered['done']=True
        return result
    p30._extend_phase30=extend
    try:return p30.run()
    finally:p30._extend_phase30=original_extend

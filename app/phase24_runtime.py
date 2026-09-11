from __future__ import annotations

"""Phase 24 runtime extension layered on Phase 21/22/23 and the authoritative app bootstrap."""

from pathlib import Path

from app import bootstrap
from app.paths import AppPaths
from media.ffmpeg import FFmpegRunner
from media.ffmpeg_locator import FFmpegLocator
from app.phase22_runtime import _extend_phase22, extend_phase21
from services.dubbing_apply_service import DubbingApplyService
from services.dubbing_service import DubbingService
from services.dubbing_validation_service import DubbingValidationService
from services.dubbing_audio_service import DubbingAudioService
from services.export_service import ExportService
from services.export_filename_service import ExportFilenameService
from services.render_service import RenderService
from services.language_service import LanguageService
from services.project_service import ProjectService
from services.scene_service import SceneService
from services.short_caption_service import ShortCaptionService
from services.short_audio_service import ShortAudioService
from services.short_subtitle_range_service import ShortSubtitleRangeService
from services.short_candidate_service import ShortCandidateService
from services.short_materialization_service import ShortMaterializationService
from services.short_reframe_service import ShortReframeService
from services.short_validation_service import ShortsValidationService
from services.shorts_service import ShortsService
from services.subtitle_service import SubtitleService
from services.visual_layer_service import VisualLayerService
from services.timeline_service import TimelineService
from services.word_timing_service import WordTimingService
from services.template_apply_service import TemplateApplyService
from services.template_package_service import TemplatePackageService
from services.template_preview_service import TemplatePreviewService
from services.template_service import TemplateService
from services.template_validation_service import TemplateValidationService
from storage.database import SQLiteDatabase
from storage.repositories.media_repository import MediaRepository
from storage.repositories.phase22_repository import Phase22Repository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.short_repository import ShortRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.dubbing_repository import DubbingRepository
from storage.repositories.template_repository import TemplateRepository
from ui.controllers.dubbing_controller import DubbingController
from ui.controllers.language_controller import LanguageController
from ui.controllers.shorts_controller import ShortsController
from ui.controllers.video_studio_controller import VideoStudioController
from ui.controllers.word_timing_controller import WordTimingController
from ui.controllers.template_controller import TemplateController
from services.speaker_service import SpeakerService
from services.speech_block_service import SpeechBlockService
from services.media_service import MediaService
from services.settings_service import SettingsService
from services.story_outline_service import StoryOutlineService
from services.news_visual_service import NewsVisualService
from services.export_preset_service import ExportPresetService
from workers.worker_pool import WorkerPool


def _extend_phase23(container):
    db=container.resolve(SQLiteDatabase); repository=ShortRepository(db)
    projects=container.resolve(ProjectRepository); media=container.resolve(MediaRepository); transcripts=container.resolve(TranscriptRepository)
    scene_repo=container.resolve(SceneRepository); scenes=container.resolve(SceneService); languages=container.resolve(LanguageService)
    subtitles=container.resolve(SubtitleService); project_service=container.resolve(ProjectService)
    candidates=ShortCandidateService(repository,media,transcripts,scene_repo)
    reframe=ShortReframeService(scene_repo)
    validation=ShortsValidationService(repository,media,scene_repo,subtitles)
    captions=ShortCaptionService(repository,transcripts,subtitles,languages)
    short_audio=ShortAudioService(container.resolve(DubbingAudioService).ffmpeg_path_provider)
    subtitle_ranges=ShortSubtitleRangeService(subtitles)
    dubbing_repository=container.resolve(DubbingRepository)
    materializer=ShortMaterializationService(repository,project_service,projects,media,scenes,scene_repo,transcripts,reframe,dubbing_repository,short_audio,subtitle_ranges)
    export_service=container.resolve(ExportService)
    shorts=ShortsService(repository,projects,candidates,materializer,reframe,validation,subtitles,languages,export_service.presets,container.resolve(TimelineService),dubbing_repository)

    # General project duplication must include Shorts metadata/candidates while keeping writable scene/timeline entities independent.
    if not getattr(project_service,"_phase23_duplicate_patch",False):
        previous=project_service.duplicate_project
        def duplicate_with_shorts(project_id):
            duplicate=previous(project_id)
            candidate_map=repository.duplicate_project(project_id,duplicate.project_id)
            source_media=media.list_by_project(project_id); target_media=media.list_by_project(duplicate.project_id)
            media_map={}
            for source in source_media:
                key=(source.name,source.original_path,source.type,int(source.file_size),int(source.duration_ms or 0))
                match=next((x for x in target_media if (x.name,x.original_path,x.type,int(x.file_size),int(x.duration_ms or 0))==key),None)
                if match: media_map[source.id]=match.id
            source_transcripts=transcripts.list_for_project(project_id); target_transcripts=transcripts.list_for_project(duplicate.project_id)
            transcript_map={}; transcript_segment_map={}
            for index,source in enumerate(source_transcripts):
                key=(source.model_id,source.model_version,source.language_mode,source.source_fingerprint,int(source.duration_ms or 0))
                match=next((x for x in target_transcripts if (x.model_id,x.model_version,x.language_mode,x.source_fingerprint,int(x.duration_ms or 0))==key),None)
                if match is None and index<len(target_transcripts): match=target_transcripts[index]
                if match is None: continue
                transcript_map[source.id]=match.id
                for a,b in zip(transcripts.segments(source.id),transcripts.segments(match.id)):
                    transcript_segment_map[a.id]=b.id
            source_scenes=scene_repo.list_for_project(project_id); target_scenes=scene_repo.list_for_project(duplicate.project_id)
            target_by_order={x.order:x for x in target_scenes}; scene_map={x.id:target_by_order[x.order].id for x in source_scenes if x.order in target_by_order}
            repository.remap_duplicate_sources(project_id,duplicate.project_id,candidate_map,media_map=media_map,transcript_map=transcript_map,transcript_segment_map=transcript_segment_map,scene_map=scene_map)
            return duplicate
        project_service.duplicate_project=duplicate_with_shorts
        project_service._phase23_duplicate_patch=True

    render_service=container.resolve(RenderService)
    if not getattr(render_service,"_phase23_short_audio_patch",False):
        previous_build_plan=render_service.build_plan
        def build_plan_with_short_audio(project_id,settings,*,preset_id="custom",job_id=""):
            plan=previous_build_plan(project_id,settings,preset_id=preset_id,job_id=job_id)
            meta=repository.get_project(project_id)
            override=str(meta.metadata.get("primaryAudioOverride","") or "") if meta is not None else ""
            if override and Path(override).is_file(): plan.primary_audio_override=override
            return plan
        render_service.build_plan=build_plan_with_short_audio
        render_service._phase23_short_audio_patch=True

    for cls,obj in ((ShortRepository,repository),(ShortCandidateService,candidates),(ShortReframeService,reframe),
                    (ShortsValidationService,validation),(ShortCaptionService,captions),(ShortAudioService,short_audio),
                    (ShortSubtitleRangeService,subtitle_ranges),(ShortMaterializationService,materializer),(ShortsService,shorts)):
        container.register_instance(cls,obj)
    return repository,candidates,reframe,captions,shorts


def _extend_phase24(container, phase22_repository, languages, visual, speakers, short_repository):
    db=container.resolve(SQLiteDatabase); paths=container.resolve(AppPaths)
    repository=TemplateRepository(db,paths.templates)
    feature_cache={}
    def feature_probe(feature):
        if feature != "chroma_key": return feature in TemplateValidationService.FEATURE_SET
        if feature in feature_cache: return feature_cache[feature]
        try:
            settings=container.resolve(SettingsService).current; locator=container.resolve(FFmpegLocator)
            ffmpeg_custom=settings.ffmpeg_path if settings.ffmpeg_mode=="custom" else None
            ffprobe_custom=settings.ffprobe_path if settings.ffmpeg_mode=="custom" else None
            info,_=locator.discover(ffmpeg_custom,ffprobe_custom)
            supported=bool(info.available and ({"chromakey","colorkey"} & set(FFmpegRunner(info.path).discover_capabilities().filters)))
        except Exception: supported=False
        feature_cache[feature]=supported; return supported
    validation=TemplateValidationService(languages,feature_probe=feature_probe)
    preview=TemplatePreviewService()
    package=TemplatePackageService(validation,filename_service=container.resolve(ExportFilenameService))
    service=TemplateService(repository,Path(__file__).resolve().parents[1]/"resources"/"templates"/"builtin",paths.templates,validation,preview,package,
                            project_repository=container.resolve(ProjectRepository),scene_repository=container.resolve(SceneRepository),
                            phase22_repository=phase22_repository,subtitle_service=container.resolve(SubtitleService),
                            short_repository=short_repository,export_presets=container.resolve(ExportPresetService))
    apply=TemplateApplyService(container.resolve(ProjectService),container.resolve(ProjectRepository),container.resolve(SceneService),
                               container.resolve(SceneRepository),visual,speakers,container.resolve(SubtitleService),validation,repository,
                               media_service=container.resolve(MediaService),short_repository=short_repository,
                               export_presets=container.resolve(ExportPresetService),timeline_service=container.resolve(TimelineService),
                               story_outline_service=container.resolve(StoryOutlineService),news_visual_service=container.resolve(NewsVisualService))
    for cls,obj in ((TemplateRepository,repository),(TemplateValidationService,validation),(TemplatePreviewService,preview),
                    (TemplatePackageService,package),(TemplateService,service),(TemplateApplyService,apply)):
        container.register_instance(cls,obj)
    return repository,service,apply


def run() -> int:
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return bootstrap.run()

    container=bootstrap.build_container()
    dub_service,dub_apply,dub_validation=extend_phase21(container)
    phase22_repository,languages,visual,speakers,blocks,universal=_extend_phase22(container)
    short_repository,candidates,reframe,captions,shorts=_extend_phase23(container)
    template_repository,templates,template_apply=_extend_phase24(container,phase22_repository,languages,visual,speakers,short_repository)
    worker_pool=container.resolve(WorkerPool); logger=container.resolve("logger")
    transcript_repository=container.resolve(TranscriptRepository); media_repository=container.resolve(MediaRepository)
    scene_repository=container.resolve(SceneRepository); project_repository=container.resolve(ProjectRepository)

    class RuntimeDubbingController(DubbingController):
        def __init__(self,parent=None):
            super().__init__(dub_service,dub_validation,worker_pool,dub_apply,transcript_repository=transcript_repository,
                             media_repository=media_repository,logger=logger,parent=parent)

    class RuntimeLanguageController(LanguageController):
        def __init__(self,parent=None): super().__init__(languages,parent)

    class RuntimeVideoStudioController(VideoStudioController):
        def __init__(self,parent=None):
            super().__init__(universal,visual,speakers,blocks,phase22_repository,media_repository,container.resolve(SceneService),languages,parent,logger)

    class RuntimeWordTimingController(WordTimingController):
        def __init__(self,parent=None): super().__init__(container.resolve(WordTimingService),parent,logger)

    class RuntimeShortsController(ShortsController):
        def __init__(self,parent=None):
            super().__init__(shorts,candidates,captions,reframe,short_repository,media_repository,transcript_repository,
                             scene_repository,project_repository,languages,logger,parent)

    class RuntimeTemplateController(TemplateController):
        def __init__(self,parent=None):
            super().__init__(templates,template_apply,logger,parent)

    qmlRegisterSingletonType(RuntimeDubbingController,"SPVideoStudio.Phase21",1,0,"Dubbing")
    qmlRegisterSingletonType(RuntimeLanguageController,"SPVideoStudio.Phase22",1,0,"LanguageCatalog")
    qmlRegisterSingletonType(RuntimeVideoStudioController,"SPVideoStudio.Phase22",1,0,"VideoStudio")
    qmlRegisterSingletonType(RuntimeWordTimingController,"SPVideoStudio.Phase22",1,0,"WordTiming")
    qmlRegisterSingletonType(RuntimeShortsController,"SPVideoStudio.Phase23",1,0,"Shorts")
    qmlRegisterSingletonType(RuntimeTemplateController,"SPVideoStudio.Phase24",1,0,"Templates")

    original=bootstrap.build_container; bootstrap.build_container=lambda:container
    try:return bootstrap.run()
    finally:bootstrap.build_container=original

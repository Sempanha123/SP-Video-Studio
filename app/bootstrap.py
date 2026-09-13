from __future__ import annotations

import sys
from pathlib import Path

from .config import AppConfig
from .container import DependencyContainer
from .logging_setup import configure_logging
from .paths import AppPaths
from media.ffmpeg_locator import FFmpegLocator
from media.probe import FFprobeService
from media.thumbnails import ThumbnailService
from engines.model_registry import ModelRegistry
from engines.model_sources import HuggingFaceSource
from engines.tts.manager import TTSEngineManager
from engines.stt.faster_whisper_engine import FasterWhisperEngine
from engines.stt.manager import STTEngineManager
from engines.tts.voxcpm2_engine import VoxCPM2Engine
from engines.voice_registry import VoiceRegistry
from engines.translation.manager import TranslationEngineManager
from engines.llm.deterministic_director import DeterministicDirectorProvider
from services.ai_resource_manager import AIResourceManager
from services.media_service import MediaService
from services.model_compatibility_service import ModelCompatibilityService
from services.model_download_service import ModelDownloadService
from services.model_service import ModelService
from services.model_verification_service import ModelVerificationService
from services.playback_service import PlaybackService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from services.project_service import ProjectService
from services.settings_service import SettingsService
from services.system_readiness_service import SystemReadinessService
from services.transcript_analysis_service import TranscriptAnalysisService
from services.transcription_service import TranscriptionService
from services.translation_chunking_service import TranslationChunkingService
from services.translation_review_service import TranslationReviewService
from services.translation_service import TranslationService
from services.subtitle_generation_service import SubtitleGenerationService
from services.subtitle_preset_service import SubtitlePresetService
from services.subtitle_preview_service import SubtitlePreviewService
from services.subtitle_service import SubtitleService
from services.subtitle_timing_service import SubtitleTimingService
from services.subtitle_validation_service import SubtitleValidationService
from services.scene_generation_service import SceneGenerationService
from services.scene_preview_service import ScenePreviewService
from services.scene_service import SceneService
from services.scene_validation_service import SceneValidationService
from services.timeline_mapping_service import TimelineMappingService
from services.timeline_snap_service import TimelineSnapService
from services.timeline_validation_service import TimelineValidationService
from services.timeline_edit_service import TimelineEditService
from services.timeline_service import TimelineService
from services.director_rule_engine import DirectorRuleEngine
from services.director_validation_service import DirectorValidationService
from services.ai_director_service import AIDirectorService
from services.director_apply_service import DirectorApplyService
from services.render_service import RenderService
from services.render_validation_service import RenderValidationService
from services.export_filename_service import ExportFilenameService
from services.export_preset_service import ExportPresetService
from services.export_validation_service import ExportValidationService
from services.export_service import ExportService
from services.news_source_fetch_service import NewsSourceFetchService
from services.news_extraction_service import NewsExtractionService
from services.news_source_service import NewsSourceService
from services.news_claim_service import NewsClaimService
from services.news_brief_service import NewsBriefService
from services.news_validation_service import NewsValidationService
from services.news_script_service import NewsScriptService
from services.news_review_service import NewsReviewService
from services.news_service import NewsService
from services.news_branding_service import NewsBrandingService
from services.news_layout_service import NewsLayoutService
from services.news_graphic_service import NewsGraphicService
from services.news_visual_validation_service import NewsVisualValidationService
from services.news_visual_service import NewsVisualService
from services.story_planner import DeterministicStoryPlanner
from services.story_service import StoryService
from services.story_outline_service import StoryOutlineService
from services.story_script_service import StoryScriptService
from services.story_apply_service import StoryApplyService
from services.story_validation_service import StoryValidationService
from services.tts_chunking_service import TTSChunkingService
from services.tts_service import TTSService
from services.narration_service import NarrationService
from services.voice_service import VoiceService
from storage.database import SQLiteDatabase
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.model_repository import ModelRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.settings_repository import SettingsRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.director_plan_repository import DirectorPlanRepository
from storage.repositories.render_job_repository import RenderJobRepository
from storage.repositories.render_output_repository import RenderOutputRepository
from storage.repositories.export_preset_repository import ExportPresetRepository
from storage.repositories.timeline_repository import TimelineRepository
from storage.repositories.news_repository import NewsRepository
from storage.repositories.news_visual_repository import NewsVisualRepository
from storage.repositories.story_repository import StoryRepository
from storage.repositories.voice_repository import VoiceRepository
from workers.worker_pool import WorkerPool


def build_container() -> DependencyContainer:
    paths = AppPaths.discover()
    paths.ensure()
    config = AppConfig()
    logger = configure_logging(paths.logs, config.log_level)

    settings_repository = SettingsRepository(paths.settings / "settings.json")
    settings_service = SettingsService(settings_repository, paths, logger)
    config.theme = settings_service.current.theme
    config.locale = settings_service.current.language
    config.log_level = "DEBUG" if settings_service.current.debug_logging else "INFO"
    config.project_root = Path(settings_service.current.default_projects_folder)

    database = SQLiteDatabase(paths.database, logger)
    database.initialize()
    repository = ProjectRepository(database)
    media_repository = MediaRepository(database)
    script_repository = ScriptRepository(database)
    model_repository = ModelRepository(database)
    generated_audio_repository = GeneratedAudioRepository(database)
    voice_repository = VoiceRepository(database)
    transcript_repository = TranscriptRepository(database)
    translation_repository = TranslationRepository(database)
    subtitle_repository = SubtitleRepository(database)
    scene_repository = SceneRepository(database)
    director_repository = DirectorPlanRepository(database)
    render_job_repository = RenderJobRepository(database)
    render_output_repository = RenderOutputRepository(database)
    export_preset_repository = ExportPresetRepository(database)
    timeline_repository = TimelineRepository(database)
    news_repository = NewsRepository(database)
    news_visual_repository = NewsVisualRepository(database)
    story_repository = StoryRepository(database)
    project_service = ProjectService(repository, config.project_root, logger)

    ffmpeg_locator = FFmpegLocator()

    def media_tool_paths() -> tuple[str | None, str | None]:
        settings = settings_service.current
        ffmpeg_custom = settings.ffmpeg_path if settings.ffmpeg_mode == "custom" else None
        ffprobe_custom = settings.ffprobe_path if settings.ffmpeg_mode == "custom" else None
        ffmpeg_info, ffprobe_info = ffmpeg_locator.discover(ffmpeg_custom, ffprobe_custom)
        return (
            ffmpeg_info.path if ffmpeg_info.available else None,
            ffprobe_info.path if ffprobe_info.available else None,
        )

    ffprobe_service = FFprobeService(lambda: media_tool_paths()[1])
    thumbnail_service = ThumbnailService(lambda: media_tool_paths()[0])
    media_service = MediaService(
        media_repository,
        repository,
        ffprobe_service,
        thumbnail_service,
        logger=logger,
    )
    project_service.set_media_service(media_service)
    script_analysis_service = ScriptAnalysisService()
    script_service = ScriptService(script_repository, repository, script_analysis_service, logger)
    project_service.set_script_service(script_service)
    playback_service = PlaybackService()

    model_registry = ModelRegistry()
    model_verification_service = ModelVerificationService(logger)
    model_download_service = ModelDownloadService(
        paths.models,
        HuggingFaceSource(),
        model_verification_service,
        logger,
    )
    model_compatibility_service = ModelCompatibilityService()
    model_service = ModelService(
        model_registry,
        model_repository,
        model_download_service,
        model_verification_service,
        model_compatibility_service,
        paths.models,
        logger,
    )

    readiness_service = SystemReadinessService(
        paths,
        settings_provider=lambda: settings_service.current,
        ffmpeg_locator=ffmpeg_locator,
        logger=logger,
        model_status_provider=model_service.family_status,
    )

    tts_manager = TTSEngineManager()
    tts_manager.register(
        "voxcpm2",
        VoxCPM2Engine(model_service.install_path(model_registry.get("voxcpm2")), logger),
    )
    tts_service = TTSService(tts_manager, model_service, readiness_service, settings_service, logger)
    tts_chunking_service = TTSChunkingService()
    narration_service = NarrationService(
        generated_audio_repository,
        repository,
        script_service,
        tts_service,
        tts_chunking_service,
        logger,
    )
    project_service.set_narration_service(narration_service)
    voice_registry = VoiceRegistry()
    voice_service = VoiceService(voice_registry, voice_repository, paths.voices, tts_service.validate_reference, logger)
    project_service.set_voice_service(voice_service)

    ai_resource_manager = AIResourceManager()
    tts_service.set_resource_manager(ai_resource_manager)
    stt_manager = STTEngineManager(FasterWhisperEngine(logger))
    transcript_analysis_service = TranscriptAnalysisService()
    transcription_service = TranscriptionService(
        transcript_repository,
        media_service,
        model_service,
        stt_manager,
        readiness_service,
        settings_service,
        transcript_analysis_service,
        ai_resource_manager,
        logger,
    )
    ai_resource_manager.register("tts", tts_service.unload, lambda: tts_service.active_jobs > 0)
    ai_resource_manager.register("stt", transcription_service.unload, lambda: transcription_service.active_jobs > 0)
    project_service.set_transcription_service(transcription_service)
    translation_manager = TranslationEngineManager()
    translation_chunking_service = TranslationChunkingService()
    translation_review_service = TranslationReviewService()
    translation_service = TranslationService(
        translation_repository,
        repository,
        transcript_repository,
        script_repository,
        model_service,
        translation_manager,
        translation_chunking_service,
        translation_review_service,
        ai_resource_manager,
        logger,
    )
    ai_resource_manager.register(
        "translation", translation_service.unload, lambda: translation_service.active_jobs > 0
    )
    project_service.set_translation_service(translation_service)
    subtitle_generation_service = SubtitleGenerationService(transcript_repository, translation_repository)
    subtitle_preset_service = SubtitlePresetService(subtitle_repository)
    subtitle_validation_service = SubtitleValidationService()
    subtitle_timing_service = SubtitleTimingService()
    subtitle_preview_service = SubtitlePreviewService(lambda: media_tool_paths()[0])
    subtitle_service = SubtitleService(
        subtitle_repository, repository, transcript_repository, translation_repository,
        subtitle_generation_service, subtitle_preset_service, subtitle_validation_service, subtitle_timing_service, logger,
    )
    project_service.set_subtitle_service(subtitle_service)
    scene_generation_service = SceneGenerationService(script_analysis_service, generated_audio_repository)
    scene_validation_service = SceneValidationService(media_repository, generated_audio_repository, subtitle_repository)
    scene_preview_service = ScenePreviewService()
    scene_service = SceneService(
        scene_repository, repository, media_repository, generated_audio_repository, subtitle_repository,
        script_service, transcript_repository, scene_generation_service, scene_validation_service, scene_preview_service, logger,
    )
    project_service.set_scene_service(scene_service)
    timeline_mapping_service = TimelineMappingService(scene_repository, media_repository, generated_audio_repository, subtitle_repository, timeline_repository)
    timeline_snap_service = TimelineSnapService()
    timeline_validation_service = TimelineValidationService()
    from commands.command_stack import CommandStack
    timeline_edit_service = TimelineEditService(scene_service, scene_repository, subtitle_service, subtitle_repository, timeline_repository, CommandStack(150))
    timeline_service = TimelineService(timeline_repository, repository, timeline_mapping_service, timeline_edit_service, timeline_snap_service, timeline_validation_service)
    project_service.set_timeline_service(timeline_service)
    director_rules = DirectorRuleEngine()
    director_provider = DeterministicDirectorProvider(director_rules)
    director_validation = DirectorValidationService(
        lambda: {voice.category for voice in voice_service.list_all()},
        lambda: {str(preset["id"]) for preset in subtitle_preset_service.list_presets()},
    )
    director_service = AIDirectorService(
        director_repository, repository, script_repository, transcript_repository, translation_repository,
        scene_repository, media_repository, script_analysis_service, director_provider, director_validation, logger,
    )
    news_fetch_service = NewsSourceFetchService()
    news_extraction_service = NewsExtractionService()
    news_source_service = NewsSourceService(news_repository, repository, news_fetch_service, logger)
    news_claim_service = NewsClaimService(news_repository, news_extraction_service)
    news_validation_service = NewsValidationService(news_repository)
    news_brief_service = NewsBriefService(news_repository)
    news_script_service = NewsScriptService(
        news_repository, script_service, news_brief_service, news_validation_service,
        translation_service=translation_service, scene_service=scene_service, director_service=director_service,
    )
    news_review_service = NewsReviewService(news_claim_service)
    news_branding_service = NewsBrandingService()
    news_layout_service = NewsLayoutService()
    news_graphic_service = NewsGraphicService()
    news_visual_validation_service = NewsVisualValidationService()
    news_visual_service = NewsVisualService(news_visual_repository, news_repository, scene_service, news_layout_service, news_graphic_service, news_branding_service, news_visual_validation_service, timeline_edit_service.stack)
    news_service = NewsService(
        news_repository, repository, news_source_service, news_claim_service, news_brief_service,
        news_script_service, news_validation_service, logger,
        voice_service=voice_service, narration_service=narration_service, subtitle_service=subtitle_service, visual_service=news_visual_service,
    )
    project_service.set_news_service(news_service)
    project_service.set_news_visual_service(news_visual_service)
    story_planner = DeterministicStoryPlanner()
    story_service = StoryService(story_repository, repository, voice_service, logger)
    story_outline_service = StoryOutlineService(story_repository, story_service, story_planner, logger)
    story_script_service = StoryScriptService(story_repository, script_service, voice_service, logger)
    story_apply_service = StoryApplyService(story_repository, scene_service, script_service, director_service, logger)
    story_validation_service = StoryValidationService(story_repository, script_repository, scene_repository, subtitle_repository, generated_audio_repository, script_analysis_service)
    project_service.set_story_service(story_service)
    director_apply_service = DirectorApplyService(
        director_service, director_repository, director_validation, project_service, scene_service, voice_service, subtitle_preset_service
    )
    project_service.set_director_service(director_service)
    render_validation_service = RenderValidationService()
    render_service = RenderService(
        repository, scene_service, subtitle_service, render_job_repository, render_output_repository,
        lambda: media_tool_paths()[0], lambda: media_tool_paths()[1], thumbnail_service, render_validation_service, logger, timeline_repository,
    )
    export_filename_service = ExportFilenameService()
    export_preset_service = ExportPresetService(export_preset_repository)
    export_validation_service = ExportValidationService(export_filename_service)
    export_service = ExportService(
        repository, render_service, subtitle_service, export_preset_service, export_filename_service,
        export_validation_service, render_output_repository, logger,
    )
    worker_pool = WorkerPool(max_workers=2)

    container = DependencyContainer()
    container.register_instance(AppPaths, paths)
    container.register_instance(AppConfig, config)
    container.register_instance(SQLiteDatabase, database)
    container.register_instance(ProjectRepository, repository)
    container.register_instance(MediaRepository, media_repository)
    container.register_instance(ScriptRepository, script_repository)
    container.register_instance(ModelRepository, model_repository)
    container.register_instance(GeneratedAudioRepository, generated_audio_repository)
    container.register_instance(VoiceRepository, voice_repository)
    container.register_instance(TranscriptRepository, transcript_repository)
    container.register_instance(TranslationRepository, translation_repository)
    container.register_instance(SubtitleRepository, subtitle_repository)
    container.register_instance(SceneRepository, scene_repository)
    container.register_instance(DirectorPlanRepository, director_repository)
    container.register_instance(RenderJobRepository, render_job_repository)
    container.register_instance(RenderOutputRepository, render_output_repository)
    container.register_instance(ExportPresetRepository, export_preset_repository)
    container.register_instance(TimelineRepository, timeline_repository)
    container.register_instance(NewsRepository, news_repository)
    container.register_instance(NewsVisualRepository, news_visual_repository)
    container.register_instance(StoryRepository, story_repository)
    container.register_instance(ProjectService, project_service)
    container.register_instance(FFprobeService, ffprobe_service)
    container.register_instance(ThumbnailService, thumbnail_service)
    container.register_instance(MediaService, media_service)
    container.register_instance(ScriptAnalysisService, script_analysis_service)
    container.register_instance(ScriptService, script_service)
    container.register_instance(PlaybackService, playback_service)
    container.register_instance(ModelRegistry, model_registry)
    container.register_instance(ModelVerificationService, model_verification_service)
    container.register_instance(ModelDownloadService, model_download_service)
    container.register_instance(ModelCompatibilityService, model_compatibility_service)
    container.register_instance(ModelService, model_service)
    container.register_instance(TTSEngineManager, tts_manager)
    container.register_instance(TTSService, tts_service)
    container.register_instance(TTSChunkingService, tts_chunking_service)
    container.register_instance(NarrationService, narration_service)
    container.register_instance(VoiceRegistry, voice_registry)
    container.register_instance(VoiceService, voice_service)
    container.register_instance(STTEngineManager, stt_manager)
    container.register_instance(TranscriptAnalysisService, transcript_analysis_service)
    container.register_instance(TranscriptionService, transcription_service)
    container.register_instance(TranslationEngineManager, translation_manager)
    container.register_instance(TranslationChunkingService, translation_chunking_service)
    container.register_instance(TranslationReviewService, translation_review_service)
    container.register_instance(TranslationService, translation_service)
    container.register_instance(SubtitleGenerationService, subtitle_generation_service)
    container.register_instance(SubtitlePresetService, subtitle_preset_service)
    container.register_instance(SubtitleValidationService, subtitle_validation_service)
    container.register_instance(SubtitleTimingService, subtitle_timing_service)
    container.register_instance(SubtitlePreviewService, subtitle_preview_service)
    container.register_instance(SubtitleService, subtitle_service)
    container.register_instance(SceneGenerationService, scene_generation_service)
    container.register_instance(SceneValidationService, scene_validation_service)
    container.register_instance(ScenePreviewService, scene_preview_service)
    container.register_instance(SceneService, scene_service)
    container.register_instance(TimelineMappingService, timeline_mapping_service)
    container.register_instance(TimelineSnapService, timeline_snap_service)
    container.register_instance(TimelineValidationService, timeline_validation_service)
    container.register_instance(TimelineEditService, timeline_edit_service)
    container.register_instance(TimelineService, timeline_service)
    container.register_instance(DirectorRuleEngine, director_rules)
    container.register_instance(DeterministicDirectorProvider, director_provider)
    container.register_instance(DirectorValidationService, director_validation)
    container.register_instance(AIDirectorService, director_service)
    container.register_instance(DirectorApplyService, director_apply_service)
    container.register_instance(RenderValidationService, render_validation_service)
    container.register_instance(RenderService, render_service)
    container.register_instance(ExportFilenameService, export_filename_service)
    container.register_instance(ExportPresetService, export_preset_service)
    container.register_instance(ExportValidationService, export_validation_service)
    container.register_instance(ExportService, export_service)
    container.register_instance(NewsSourceFetchService, news_fetch_service)
    container.register_instance(NewsExtractionService, news_extraction_service)
    container.register_instance(NewsSourceService, news_source_service)
    container.register_instance(NewsClaimService, news_claim_service)
    container.register_instance(NewsValidationService, news_validation_service)
    container.register_instance(NewsBriefService, news_brief_service)
    container.register_instance(NewsScriptService, news_script_service)
    container.register_instance(NewsReviewService, news_review_service)
    container.register_instance(NewsService, news_service)
    container.register_instance(NewsBrandingService, news_branding_service)
    container.register_instance(NewsLayoutService, news_layout_service)
    container.register_instance(NewsGraphicService, news_graphic_service)
    container.register_instance(NewsVisualValidationService, news_visual_validation_service)
    container.register_instance(NewsVisualService, news_visual_service)
    container.register_instance(DeterministicStoryPlanner, story_planner)
    container.register_instance(StoryService, story_service)
    container.register_instance(StoryOutlineService, story_outline_service)
    container.register_instance(StoryScriptService, story_script_service)
    container.register_instance(StoryApplyService, story_apply_service)
    container.register_instance(StoryValidationService, story_validation_service)
    container.register_instance(AIResourceManager, ai_resource_manager)
    container.register_instance(VoiceRegistry, voice_registry)
    container.register_instance(VoiceService, voice_service)
    container.register_instance(SettingsRepository, settings_repository)
    container.register_instance(SettingsService, settings_service)
    container.register_instance(FFmpegLocator, ffmpeg_locator)
    container.register_instance(SystemReadinessService, readiness_service)
    container.register_instance(WorkerPool, worker_pool)
    container.register_instance("logger", logger)
    return container


def run() -> int:
    try:
        from PySide6.QtCore import QCoreApplication, QTimer, QUrl, Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError as exc:  # pragma: no cover - user environment problem
        print("PySide6 is required. Install dependencies with: pip install -e .", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2

    try:
        container = build_container()
    except Exception as exc:  # pragma: no cover - startup environment failure
        print("SP Video Studio could not initialize its local application data.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    logger = container.resolve("logger")

    QCoreApplication.setOrganizationName("SP Video Studio")
    QCoreApplication.setApplicationName("SP Video Studio")
    # Qt 6 enables high-DPI scaling by default. Preserve fractional Windows
    # scale factors (125/150/200%) instead of forcing integer rounding.
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except (AttributeError, TypeError):
        pass
    app = QGuiApplication(sys.argv)

    from ui.controllers.media_controller import MediaController
    from ui.controllers.model_controller import ModelController
    from ui.controllers.project_controller import ProjectController
    from ui.controllers.playback_controller import PlaybackController
    from ui.controllers.readiness_controller import ReadinessController
    from ui.controllers.script_controller import ScriptController
    from ui.controllers.settings_controller import SettingsController
    from ui.controllers.tts_controller import TTSController
    from ui.controllers.transcription_controller import TranscriptionController
    from ui.controllers.translation_controller import TranslationController
    from ui.controllers.subtitle_controller import SubtitleController
    from ui.controllers.scene_controller import SceneController
    from ui.controllers.timeline_controller import TimelineController
    from ui.controllers.ai_director_controller import AIDirectorController
    from ui.controllers.render_controller import RenderController
    from ui.controllers.export_controller import ExportController
    from ui.controllers.voice_controller import VoiceController
    from ui.controllers.news_controller import NewsController
    from ui.controllers.news_visual_controller import NewsVisualController
    from ui.controllers.story_controller import StoryController

    project_service = container.resolve(ProjectService)
    project_controller = ProjectController(project_service)
    media_controller = MediaController(
        container.resolve(MediaService),
        container.resolve(WorkerPool),
        logger,
    )
    playback_controller = PlaybackController(
        container.resolve(MediaService),
        container.resolve(PlaybackService),
        logger,
    )
    media_controller.mediaAboutToRemove.connect(playback_controller.mediaRemoving)
    script_controller = ScriptController(
        container.resolve(ScriptService),
        container.resolve(ScriptAnalysisService),
        logger,
    )
    settings_controller = SettingsController(
        container.resolve(SettingsService),
        container.resolve(AppPaths),
        project_service,
        container.resolve(FFmpegLocator),
        container.resolve(WorkerPool),
        logger,
    )
    readiness_controller = ReadinessController(
        container.resolve(SystemReadinessService),
        container.resolve(WorkerPool),
        logger,
    )
    model_controller = ModelController(
        container.resolve(ModelService),
        container.resolve(SystemReadinessService),
        container.resolve(WorkerPool),
        logger,
    )
    tts_controller = TTSController(
        container.resolve(NarrationService),
        container.resolve(TTSService),
        container.resolve(WorkerPool),
        logger,
    )
    voice_controller = VoiceController(
        container.resolve(VoiceService),
        project_service,
        container.resolve(ModelService),
        logger,
    )
    transcription_controller = TranscriptionController(
        container.resolve(TranscriptionService),
        container.resolve(WorkerPool),
        logger,
    )
    translation_controller = TranslationController(
        container.resolve(TranslationService),
        container.resolve(WorkerPool),
        logger,
    )
    subtitle_controller = SubtitleController(
        container.resolve(SubtitleService),
        container.resolve(SubtitlePresetService),
        container.resolve(SubtitlePreviewService),
        container.resolve(MediaService),
        container.resolve(WorkerPool),
        logger,
    )
    scene_controller = SceneController(
        container.resolve(SceneService),
        container.resolve(MediaService),
        container.resolve(NarrationService),
        container.resolve(SubtitleService),
        logger,
    )
    timeline_controller = TimelineController(container.resolve(TimelineService), logger)
    director_controller = AIDirectorController(
        container.resolve(AIDirectorService),
        container.resolve(DirectorApplyService),
        container.resolve(VoiceService),
        logger,
    )
    render_controller = RenderController(
        container.resolve(RenderService),
        container.resolve(WorkerPool),
        logger,
    )
    export_controller = ExportController(
        container.resolve(ExportService),
        container.resolve(WorkerPool),
        logger,
    )
    news_controller = NewsController(
        container.resolve(NewsService),
        container.resolve(NewsSourceService),
        container.resolve(NewsClaimService),
        container.resolve(NewsBriefService),
        container.resolve(NewsScriptService),
        container.resolve(NewsValidationService),
        container.resolve(WorkerPool),
        logger,
    )
    news_visual_controller = NewsVisualController(container.resolve(NewsVisualService), logger)
    story_controller = StoryController(
        container.resolve(StoryService), container.resolve(StoryOutlineService), container.resolve(StoryScriptService),
        container.resolve(StoryApplyService), container.resolve(StoryValidationService), logger,
    )

    def flush_for_export() -> bool:
        if not script_controller.flush():
            return False
        if not transcription_controller.saveEdits():
            return False
        if not translation_controller.saveEdits():
            return False
        if not subtitle_controller.flush():
            return False
        return True

    export_controller.set_pre_export_flush(flush_for_export)

    def before_project_change() -> bool:
        if render_controller.busy:
            render_controller.operationFailed.emit("Finish or cancel the active render before changing projects.")
            return False
        if export_controller.busy:
            export_controller.operationFailed.emit("Finish or cancel the active export before changing projects.")
            return False
        if not script_controller.flush():
            return False
        if tts_controller.busy:
            tts_controller.cancel()
            return False
        if transcription_controller.busy:
            transcription_controller.cancel()
            return False
        if not transcription_controller.saveEdits():
            return False
        if translation_controller.busy:
            translation_controller.cancel()
            return False
        if not translation_controller.saveEdits():
            return False
        if not subtitle_controller.flush():
            return False
        return True

    project_controller.set_before_project_change(before_project_change)
    settings_controller.readinessRelevantChanged.connect(readiness_controller.recheck)
    model_controller.modelStateChanged.connect(readiness_controller.recheck)
    tts_controller.modelStateChanged.connect(model_controller.refresh)
    tts_controller.generatedAudioAboutToRemove.connect(playback_controller.externalAudioRemoving)
    tts_controller.modelStateChanged.connect(readiness_controller.recheck)
    tts_controller.previewReady.connect(lambda path, _name, duration: voice_controller.previewGenerated(path, duration))
    model_controller.modelStateChanged.connect(voice_controller.refresh)
    model_controller.modelStateChanged.connect(transcription_controller.modelsChanged.emit)
    media_controller.mediaAboutToRemove.connect(transcription_controller.mediaRemoving)
    project_controller.currentProjectChanged.connect(
        lambda: transcription_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: translation_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: subtitle_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: scene_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: timeline_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: render_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: export_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: news_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: news_visual_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    project_controller.currentProjectChanged.connect(
        lambda: story_controller.setCurrentProject(str(project_controller.currentProject.get("id", "")))
    )
    transcription_controller.playbackRequested.connect(
        lambda media_id, start_ms, autoplay: (
            playback_controller.setMedia(media_id),
            playback_controller.seek(start_ms),
            playback_controller.play() if autoplay else None,
        )
    )
    translation_controller.playbackRequested.connect(
        lambda media_id, start_ms, autoplay: (
            playback_controller.setMedia(media_id),
            playback_controller.seek(start_ms),
            playback_controller.play() if autoplay else None,
        )
    )
    subtitle_controller.playbackRequested.connect(
        lambda media_id, start_ms, autoplay: (
            playback_controller.setMedia(media_id),
            playback_controller.seek(start_ms),
            playback_controller.play() if autoplay else None,
        )
    )
    scene_controller.playbackRequested.connect(
        lambda media_id, start_ms, autoplay: (
            playback_controller.setMedia(media_id),
            playback_controller.seek(start_ms),
            playback_controller.play() if autoplay else None,
        )
    )
    scene_controller.audioPlaybackRequested.connect(
        lambda path, name, duration_ms: (
            playback_controller.setExternalAudio(path, name, duration_ms),
            playback_controller.play(),
        )
    )
    render_controller.playRequested.connect(
        lambda path, name, duration_ms: (
            playback_controller.setExternalVideo(path, name, duration_ms),
            playback_controller.play(),
        )
    )
    export_controller.playRequested.connect(
        lambda path, name, duration_ms: (
            playback_controller.setExternalVideo(path, name, duration_ms),
            playback_controller.play(),
        )
    )
    timeline_controller.playbackRequested.connect(
        lambda media_id, start_ms, autoplay: (
            playback_controller.setMedia(media_id),
            playback_controller.seek(start_ms),
            playback_controller.play() if autoplay else None,
        )
    )
    timeline_controller.togglePlaybackRequested.connect(playback_controller.togglePlayback)
    playback_controller.playbackChanged.connect(lambda: subtitle_controller.setPlayhead(playback_controller.position))
    playback_controller.playbackChanged.connect(lambda: timeline_controller.setPreviewLocalPosition(playback_controller.position))
    scene_controller.scenesChanged.connect(timeline_controller.refresh)
    scene_controller.sceneChanged.connect(timeline_controller.refresh)
    scene_controller.scenesChanged.connect(news_visual_controller.refresh)
    scene_controller.sceneChanged.connect(news_visual_controller.refresh)
    subtitle_controller.trackChanged.connect(timeline_controller.refresh)
    subtitle_controller.tracksChanged.connect(timeline_controller.refresh)
    project_controller.currentProjectChanged.connect(lambda: voice_controller.setCurrentProject(str(project_controller.currentProject.get("id", ""))))
    script_controller.selectedSectionChanged.connect(lambda: voice_controller.setCurrentSection(str(script_controller.selectedSection.get("id", ""))))

    container.register_instance(ProjectController, project_controller)
    container.register_instance(MediaController, media_controller)
    container.register_instance(PlaybackController, playback_controller)
    container.register_instance(ScriptController, script_controller)
    container.register_instance(SettingsController, settings_controller)
    container.register_instance(ReadinessController, readiness_controller)
    container.register_instance(ModelController, model_controller)
    container.register_instance(TTSController, tts_controller)
    container.register_instance(VoiceController, voice_controller)
    container.register_instance(TranscriptionController, transcription_controller)
    container.register_instance(TranslationController, translation_controller)
    container.register_instance(SubtitleController, subtitle_controller)
    container.register_instance(SceneController, scene_controller)
    container.register_instance(TimelineController, timeline_controller)
    container.register_instance(AIDirectorController, director_controller)
    container.register_instance(RenderController, render_controller)
    container.register_instance(ExportController, export_controller)
    container.register_instance(NewsController, news_controller)
    container.register_instance(NewsVisualController, news_visual_controller)
    container.register_instance(StoryController, story_controller)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("projectController", project_controller)
    engine.rootContext().setContextProperty("mediaController", media_controller)
    engine.rootContext().setContextProperty("playbackController", playback_controller)
    engine.rootContext().setContextProperty("scriptController", script_controller)
    engine.rootContext().setContextProperty("settingsController", settings_controller)
    engine.rootContext().setContextProperty("readinessController", readiness_controller)
    engine.rootContext().setContextProperty("modelController", model_controller)
    engine.rootContext().setContextProperty("ttsController", tts_controller)
    engine.rootContext().setContextProperty("voiceController", voice_controller)
    engine.rootContext().setContextProperty("transcriptionController", transcription_controller)
    engine.rootContext().setContextProperty("translationController", translation_controller)
    engine.rootContext().setContextProperty("subtitleController", subtitle_controller)
    engine.rootContext().setContextProperty("sceneController", scene_controller)
    engine.rootContext().setContextProperty("timelineController", timeline_controller)
    engine.rootContext().setContextProperty("directorController", director_controller)
    engine.rootContext().setContextProperty("renderController", render_controller)
    engine.rootContext().setContextProperty("exportController", export_controller)
    engine.rootContext().setContextProperty("newsController", news_controller)
    engine.rootContext().setContextProperty("newsVisualController", news_visual_controller)
    engine.rootContext().setContextProperty("storyController", story_controller)
    qml_file = Path(__file__).resolve().parents[1] / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        logger.error("Failed to load QML application shell from %s", qml_file)
        return 1

    QTimer.singleShot(0, model_controller.refresh)
    if container.resolve(SettingsService).current.readiness_check_on_startup:
        QTimer.singleShot(0, readiness_controller.recheck)

    app.aboutToQuit.connect(script_controller.flush)
    app.aboutToQuit.connect(tts_controller.cancel)
    app.aboutToQuit.connect(transcription_controller.cancel)
    app.aboutToQuit.connect(transcription_controller.saveEdits)
    app.aboutToQuit.connect(translation_controller.cancel)
    app.aboutToQuit.connect(translation_controller.saveEdits)
    app.aboutToQuit.connect(subtitle_controller.flush)
    app.aboutToQuit.connect(render_controller.cancel)
    app.aboutToQuit.connect(export_controller.cancel)
    app.aboutToQuit.connect(container.resolve(TTSService).unload)
    app.aboutToQuit.connect(container.resolve(TranscriptionService).unload)
    app.aboutToQuit.connect(container.resolve(TranslationService).unload)
    app.aboutToQuit.connect(lambda: model_controller.cancelDownload(model_controller.activeModelId) if model_controller.activeModelId else None)
    app.aboutToQuit.connect(playback_controller.clear)
    app.aboutToQuit.connect(container.resolve(WorkerPool).shutdown)
    logger.info("SP Video Studio started")
    return app.exec()

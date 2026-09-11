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
from engines.tts.voxcpm2_engine import VoxCPM2Engine
from engines.voice_registry import VoiceRegistry
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
        from PySide6.QtCore import QCoreApplication, QTimer, QUrl
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
    app = QGuiApplication(sys.argv)

    from ui.controllers.media_controller import MediaController
    from ui.controllers.model_controller import ModelController
    from ui.controllers.project_controller import ProjectController
    from ui.controllers.playback_controller import PlaybackController
    from ui.controllers.readiness_controller import ReadinessController
    from ui.controllers.script_controller import ScriptController
    from ui.controllers.settings_controller import SettingsController
    from ui.controllers.tts_controller import TTSController
    from ui.controllers.voice_controller import VoiceController

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

    def before_project_change() -> bool:
        if not script_controller.flush():
            return False
        if tts_controller.busy:
            tts_controller.cancel()
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
    app.aboutToQuit.connect(container.resolve(TTSService).unload)
    app.aboutToQuit.connect(lambda: model_controller.cancelDownload(model_controller.activeModelId) if model_controller.activeModelId else None)
    app.aboutToQuit.connect(playback_controller.clear)
    app.aboutToQuit.connect(container.resolve(WorkerPool).shutdown)
    logger.info("SP Video Studio started")
    return app.exec()

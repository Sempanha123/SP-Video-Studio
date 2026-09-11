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
from services.media_service import MediaService
from services.project_service import ProjectService
from services.settings_service import SettingsService
from services.system_readiness_service import SystemReadinessService
from storage.database import SQLiteDatabase
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.settings_repository import SettingsRepository
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

    readiness_service = SystemReadinessService(
        paths,
        settings_provider=lambda: settings_service.current,
        ffmpeg_locator=ffmpeg_locator,
        logger=logger,
    )
    worker_pool = WorkerPool(max_workers=2)

    container = DependencyContainer()
    container.register_instance(AppPaths, paths)
    container.register_instance(AppConfig, config)
    container.register_instance(SQLiteDatabase, database)
    container.register_instance(ProjectRepository, repository)
    container.register_instance(MediaRepository, media_repository)
    container.register_instance(ProjectService, project_service)
    container.register_instance(FFprobeService, ffprobe_service)
    container.register_instance(ThumbnailService, thumbnail_service)
    container.register_instance(MediaService, media_service)
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
    from ui.controllers.project_controller import ProjectController
    from ui.controllers.readiness_controller import ReadinessController
    from ui.controllers.settings_controller import SettingsController

    project_service = container.resolve(ProjectService)
    project_controller = ProjectController(project_service)
    media_controller = MediaController(
        container.resolve(MediaService),
        container.resolve(WorkerPool),
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
    settings_controller.readinessRelevantChanged.connect(readiness_controller.recheck)

    container.register_instance(ProjectController, project_controller)
    container.register_instance(MediaController, media_controller)
    container.register_instance(SettingsController, settings_controller)
    container.register_instance(ReadinessController, readiness_controller)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("projectController", project_controller)
    engine.rootContext().setContextProperty("mediaController", media_controller)
    engine.rootContext().setContextProperty("settingsController", settings_controller)
    engine.rootContext().setContextProperty("readinessController", readiness_controller)
    qml_file = Path(__file__).resolve().parents[1] / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        logger.error("Failed to load QML application shell from %s", qml_file)
        return 1

    if container.resolve(SettingsService).current.readiness_check_on_startup:
        QTimer.singleShot(0, readiness_controller.recheck)

    app.aboutToQuit.connect(container.resolve(WorkerPool).shutdown)
    logger.info("SP Video Studio started")
    return app.exec()

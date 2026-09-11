from __future__ import annotations

import sys
from pathlib import Path

from .config import AppConfig
from .container import DependencyContainer
from .logging_setup import configure_logging
from .paths import AppPaths
from services.project_service import ProjectService
from storage.database import SQLiteDatabase
from storage.repositories.project_repository import ProjectRepository


def build_container() -> DependencyContainer:
    paths = AppPaths.discover()
    paths.ensure()
    config = AppConfig()
    logger = configure_logging(paths.logs, config.log_level)

    database = SQLiteDatabase(paths.database, logger)
    database.initialize()
    repository = ProjectRepository(database)
    project_root = config.project_root or paths.default_projects_root
    project_service = ProjectService(repository, project_root, logger)

    container = DependencyContainer()
    container.register_instance(AppPaths, paths)
    container.register_instance(AppConfig, config)
    container.register_instance(SQLiteDatabase, database)
    container.register_instance(ProjectRepository, repository)
    container.register_instance(ProjectService, project_service)
    container.register_instance("logger", logger)
    return container


def run() -> int:
    try:
        from PySide6.QtCore import QCoreApplication, QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError as exc:  # pragma: no cover - user environment problem
        print("PySide6 is required. Install dependencies with: pip install -e .", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2

    try:
        container = build_container()
    except Exception as exc:  # pragma: no cover - startup environment failure
        print("SP Video Studio could not initialize its local database.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    logger = container.resolve("logger")

    QCoreApplication.setOrganizationName("SP Video Studio")
    QCoreApplication.setApplicationName("SP Video Studio")
    app = QGuiApplication(sys.argv)

    from ui.controllers.project_controller import ProjectController

    project_controller = ProjectController(container.resolve(ProjectService))
    container.register_instance(ProjectController, project_controller)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("projectController", project_controller)
    qml_file = Path(__file__).resolve().parents[1] / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        logger.error("Failed to load QML application shell from %s", qml_file)
        return 1

    logger.info("SP Video Studio started")
    return app.exec()

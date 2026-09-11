from __future__ import annotations

import sys
from pathlib import Path

from .config import AppConfig
from .container import DependencyContainer
from .logging_setup import configure_logging
from .paths import AppPaths


def build_container() -> DependencyContainer:
    paths = AppPaths.discover()
    paths.ensure()
    config = AppConfig()
    logger = configure_logging(paths.logs, config.log_level)
    container = DependencyContainer()
    container.register_instance(AppPaths, paths)
    container.register_instance(AppConfig, config)
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

    container = build_container()
    logger = container.resolve("logger")

    QCoreApplication.setOrganizationName("SP Video Studio")
    QCoreApplication.setApplicationName("SP Video Studio")
    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()
    qml_file = Path(__file__).resolve().parents[1] / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        logger.error("Failed to load QML application shell from %s", qml_file)
        return 1

    logger.info("SP Video Studio started")
    return app.exec()

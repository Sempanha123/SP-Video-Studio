import os
from pathlib import Path
import pytest

PySide6 = pytest.importorskip("PySide6")


def test_qml_application_shell_loads():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    main = Path(__file__).resolve().parents[1] / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main)))
    assert engine.rootObjects(), "Main.qml failed to load"
    engine.clearComponentCache()
    app.processEvents()

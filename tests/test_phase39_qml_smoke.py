from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.qml_smoke
ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "ui" / "qml"

MAJOR_SURFACES = {
    "Home": "pages/HomePage.qml",
    "Create": "pages/CreatePage.qml",
    "Projects": "pages/ProjectsPage.qml",
    "Video Studio": "pages/ProjectWorkspacePage.qml",
    "News": "news/NewsStudio.qml",
    "Story": "story/StoryStudio.qml",
    "Dub": "dubbing/DubSetup.qml",
    "Shorts": "shorts/ShortsStudio.qml",
    "Voices": "pages/VoicesPage.qml",
    "Templates": "pages/TemplatesPage.qml",
    "Assets": "pages/AssetsPage.qml",
    "Batch": "pages/BatchPage.qml",
    "Models": "pages/ModelsPage.qml",
    "Settings": "pages/SettingsPage.qml",
    "Diagnostics": "diagnostics/DiagnosticsPage.qml",
}


def _full_qml_tree_available() -> bool:
    return (QML / "pages/CreatePage.qml").is_file() and (QML / "news/NewsStudio.qml").is_file()


def _balanced(text: str) -> bool:
    # Lightweight static guard for CI environments without Qt tooling. It is not
    # a replacement for qmllint/live Windows smoke, which is covered separately.
    return text.count("{") == text.count("}") and text.count("[") == text.count("]")


def test_major_qml_surfaces_exist_and_are_structurally_balanced():
    if not _full_qml_tree_available():
        pytest.skip("Complete QML source tree is not present in this partial sandbox checkout")
    missing = []
    for label, relative in MAJOR_SURFACES.items():
        path = QML / relative
        if not path.is_file():
            missing.append(f"{label}: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        assert "import QtQuick" in text, relative
        assert _balanced(text), relative
    assert not missing, "Missing major QML surfaces: " + ", ".join(missing)


def test_light_dark_theme_and_accessibility_contracts_remain_present():
    main = QML / "Main.qml"
    settings = QML / "pages/SettingsPage.qml"
    if not main.is_file() or not settings.is_file():
        pytest.skip("Main/Settings QML are unavailable")
    combined = main.read_text(encoding="utf-8") + "\n" + settings.read_text(encoding="utf-8")
    assert "Theme.setMode" in combined
    assert "accessibleName" in combined or "Accessible.name" in combined
    assert "reduceMotion" in combined
    assert "interfaceTextSize" in combined
    assert "keyboard" in combined.casefold() or "shortcut" in combined.casefold()


def test_qmllint_major_surfaces_when_tool_is_available():
    qmllint = shutil.which("qmllint")
    if not qmllint:
        pytest.skip("qmllint is not installed in this environment")
    if not _full_qml_tree_available():
        pytest.skip("Complete QML source tree is not present")
    # Lint a representative shell/workflow subset. Project-specific singleton
    # imports can produce environment warnings, so fail only on syntax errors.
    targets = [QML / "Main.qml", QML / "pages/HomePage.qml", QML / "news/NewsStudio.qml", QML / "story/StoryStudio.qml"]
    for target in targets:
        done = subprocess.run([qmllint, str(target)], cwd=ROOT, capture_output=True, text=True, timeout=30, shell=False)
        output = (done.stdout + "\n" + done.stderr).casefold()
        assert "syntax error" not in output, f"{target}: {done.stdout}\n{done.stderr}"


def test_critical_interaction_surfaces_have_controller_hooks():
    if not _full_qml_tree_available():
        pytest.skip("Complete QML source tree is not present")
    sources = "\n".join(path.read_text(encoding="utf-8") for path in QML.rglob("*.qml"))
    # Critical interactions requested for release QA. These assertions protect
    # the wiring contract; click-through remains in the Windows manual matrix.
    for token in ("createProject", "split", "Speech", "voice", "export", "pause", "Recovery", "CommandPalette"):
        assert token.casefold() in sources.casefold(), token

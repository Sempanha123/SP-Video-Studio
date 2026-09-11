from pathlib import Path

QML_ROOT = Path(__file__).resolve().parents[1] / "ui" / "qml"


def test_required_phase1_pages_exist():
    expected = {
        "HomePage.qml", "CreatePage.qml", "ProjectsPage.qml", "BatchPage.qml",
        "VoicesPage.qml", "TemplatesPage.qml", "AssetsPage.qml", "ModelsPage.qml", "SettingsPage.qml",
        "ProjectWorkspacePage.qml",
    }
    assert expected <= {p.name for p in (QML_ROOT / "pages").glob("*.qml")}


def test_required_design_tokens_exist():
    expected = {"Theme.qml", "Colors.qml", "Typography.qml", "Spacing.qml", "Radius.qml", "AnimationTokens.qml"}
    assert expected <= {p.name for p in (QML_ROOT / "theme").glob("*.qml")}


def test_main_uses_native_qml_shell():
    text = (QML_ROOT / "Main.qml").read_text(encoding="utf-8")
    assert "ApplicationWindow" in text
    assert "WebView" not in text
    assert "Electron" not in text


def test_phase2_project_ui_is_wired():
    main = (QML_ROOT / "Main.qml").read_text(encoding="utf-8")
    create = (QML_ROOT / "pages" / "CreatePage.qml").read_text(encoding="utf-8")
    projects = (QML_ROOT / "pages" / "ProjectsPage.qml").read_text(encoding="utf-8")
    assert "ProjectWorkspacePage.qml" in main
    assert "projectController.createProject" in create
    assert "projectController.openProject" in projects
    assert "projectController.deleteProject" in projects

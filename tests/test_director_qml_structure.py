from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_director_qml_files_and_workspace_wiring():
    for path in [
        "ui/qml/director/AIDirectorPage.qml",
        "ui/qml/director/DirectorSetup.qml",
        "ui/qml/director/DirectorPlanReview.qml",
        "ui/qml/director/DirectorScenePlan.qml",
        "ui/qml/director/DirectorRecommendationCard.qml",
        "ui/qml/director/DirectorApplyDialog.qml",
        "ui/controllers/ai_director_controller.py",
    ]:
        assert (ROOT / path).is_file(), path
    workspace = read("ui/qml/pages/ProjectWorkspacePage.qml")
    assert 'text: "Director"' in workspace
    assert 'workspaceMode === "director"' in workspace
    assert "AIDirectorPage" in workspace
    assert "directorController.setCurrentProject" in workspace


def test_director_ui_is_structured_not_chat_and_exposes_offline_apply_controls():
    page = read("ui/qml/director/AIDirectorPage.qml")
    setup = read("ui/qml/director/DirectorSetup.qml")
    review = read("ui/qml/director/DirectorPlanReview.qml")
    apply = read("ui/qml/director/DirectorApplyDialog.qml")
    assert "AI Director" in page
    assert "Create Plan" in setup
    assert "Content Source" in setup
    assert "Offline planning" in setup
    assert "Recommendations" in review and "Scene Plan" in review
    assert "Regenerate Unlocked" in review
    assert "Apply Settings Only" in apply and "Replace Existing Scenes" in apply
    assert "chat" not in page.lower()


def test_bootstrap_registers_director_services_and_context():
    bootstrap = read("app/bootstrap.py")
    assert "AIDirectorService" in bootstrap
    assert "DirectorApplyService" in bootstrap
    assert 'setContextProperty("directorController"' in bootstrap

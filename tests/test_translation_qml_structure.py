from pathlib import Path


def test_translation_workspace_and_components_are_wired():
    workspace = Path("ui/qml/pages/ProjectWorkspacePage.qml").read_text(encoding="utf-8")
    assert 'text: "Translation"' in workspace
    assert "TranslationPage" in workspace
    assert "translationController.setCurrentProject" in workspace
    assert "translationController.saveEdits" in workspace
    assert 'text: "Subtitles"' in workspace


def test_translation_review_is_side_by_side_and_protects_human_review_actions():
    page = Path("ui/qml/editor/TranslationPage.qml").read_text(encoding="utf-8")
    row = Path("ui/qml/editor/TranslationSegmentRow.qml").read_text(encoding="utf-8")
    toolbar = Path("ui/qml/editor/TranslationToolbar.qml").read_text(encoding="utf-8")
    setup = Path("ui/qml/editor/TranslationSetupDialog.qml").read_text(encoding="utf-8")
    for token in ("TranslationSegmentRow", "Sync with Source", "Approve", "Export"):
        assert token in page or token in toolbar
    assert "SOURCE" in row and "TRANSLATION" in row
    assert "Mark Reviewed" in row or "reviewed" in row
    assert "Lock" in row or "locked" in row
    assert "Reset" in row and "Retranslate" in row
    assert "Local Translation" in setup or "provider" in setup.lower()
    assert "Manual Translation" in setup or "providers" in setup


def test_models_page_has_translation_filter_and_no_future_phase_ui():
    text = Path("ui/qml/pages/ModelsPage.qml").read_text(encoding="utf-8")
    assert 'text: "Translation"' in text
    assert 'item.purpose === "translation"' in text
    for prohibited in ("Subtitle Studio", "Dubbing Studio", "Timeline Editor"):
        assert prohibited not in text


def test_bootstrap_exposes_translation_controller_and_resource_manager():
    text = Path("app/bootstrap.py").read_text(encoding="utf-8")
    assert 'setContextProperty("translationController"' in text
    assert '"translation", translation_service.unload' in text
    assert "TranslationService" in text and "TranslationRepository" in text

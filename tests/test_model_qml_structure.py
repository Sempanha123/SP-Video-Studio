from pathlib import Path


def test_models_page_uses_real_controller_and_model_components():
    page = Path("ui/qml/pages/ModelsPage.qml").read_text(encoding="utf-8")
    assert "modelController.models" in page
    assert "modelController.install" in page
    assert "modelController.verify" in page
    assert "modelController.repair" in page
    assert "modelController.remove" in page
    assert "ModelCard" in page
    assert "System Compatibility" in page
    assert "Model installation will be available in a later phase" not in page


def test_model_cards_expose_status_specific_actions():
    card = Path("ui/qml/components/ModelCard.qml").read_text(encoding="utf-8")
    for text in ("Install", "Resume", "Cancel", "Verify", "Repair", "Open Folder", "Remove"):
        assert text in card
    assert "ModelDownloadProgress" in card
    assert "CompatibilityBadge" in card


def test_main_exposes_model_download_status_and_toasts():
    main = Path("ui/qml/Main.qml").read_text(encoding="utf-8")
    assert "modelController" in main
    assert "1 Model Download" in main
    settings = Path("ui/qml/pages/SettingsPage.qml").read_text(encoding="utf-8")
    assert "AI Model Storage" in settings

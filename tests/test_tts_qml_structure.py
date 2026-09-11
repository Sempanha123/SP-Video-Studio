from pathlib import Path


def test_tts_panel_is_connected_to_script_workspace():
    editor = Path("ui/qml/editor/ScriptEditor.qml").read_text(encoding="utf-8")
    panel = Path("ui/qml/editor/TTSPanel.qml").read_text(encoding="utf-8")
    workspace = Path("ui/qml/pages/ProjectWorkspacePage.qml").read_text(encoding="utf-8")
    assert "TTSPanel" in editor
    assert "Generate Full Narration" in panel
    assert "Generate Section Voice" in panel
    assert "Generate Preview" in panel
    assert "I have permission to use this voice recording." in panel
    assert "ttsController.setCurrentProject" in workspace


def test_tts_panel_reuses_shared_playback_controller():
    panel = Path("ui/qml/editor/TTSPanel.qml").read_text(encoding="utf-8")
    controller = Path("ui/controllers/playback_controller.py").read_text(encoding="utf-8")
    assert "setExternalAudio" in panel
    assert "def setExternalAudio" in controller

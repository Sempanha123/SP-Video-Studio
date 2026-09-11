from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_voice_studio_replaces_placeholder_and_reuses_tts():
    page = read("ui/qml/pages/VoicesPage.qml")
    assert "Voice Studio" in page
    assert "Voice Library" in page
    assert "Designed Voice" in page
    assert "Reference Voice" in page
    assert "Use for Project" in page
    assert "Use for Section" in page
    assert "ttsController.generatePreview" in page
    assert "ttsController.generateSection" in page
    assert "ttsController.generateFull" in page
    assert "Narration Takes" in page
    assert "setActiveGenerated" in page


def test_script_workspace_exposes_voice_assignment_without_rebuilding_tts():
    editor = read("ui/qml/editor/ScriptEditor.qml")
    panel = read("ui/qml/editor/TTSPanel.qml")
    workspace = read("ui/qml/pages/ProjectWorkspacePage.qml")
    assert "property var voiceController" in editor
    assert "Narration voice" in editor
    assert 'navigateRequested("voices", "")' in editor
    assert "voiceController: root.voiceController" in editor
    assert "resolvedConfig" in panel
    assert "generateAssignedSection" in panel
    assert "generateAssignedFull" in panel
    assert 'voiceController: typeof voiceController !== "undefined" ? voiceController : null' in workspace


def test_voice_ui_has_no_human_avatar_dependency():
    page = read("ui/qml/pages/VoicesPage.qml")
    card = read("ui/qml/components/VoiceCard.qml")
    assert "speaker portrait" not in page.lower()
    assert "avatar" not in card.lower()
    assert 'iconName: "mic"' in page or 'name: "mic"' in page

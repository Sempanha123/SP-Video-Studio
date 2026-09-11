from pathlib import Path


def test_script_editor_qml_has_required_manual_workflow():
    qml = Path("ui/qml/editor/ScriptEditor.qml").read_text(encoding="utf-8")
    toolbar = Path("ui/qml/editor/ScriptToolbar.qml").read_text(encoding="utf-8")
    for expected in (
        "Outline",
        "Write narration for this section",
        "setLanguage",
        "setPace",
        "updateSectionContent",
        "deleteSection",
        "moveSection",
        "setSectionEnabled",
        "StandardKey.Save",
    ):
        assert expected in qml
    for expected in ("Import TXT", "Export TXT", "Copy Full Script"):
        assert expected in toolbar
    assert "Generate Hook" not in qml + toolbar


def test_workspace_exposes_only_media_and_script_as_functional_modules():
    qml = Path("ui/qml/pages/ProjectWorkspacePage.qml").read_text(encoding="utf-8")
    assert 'text: "Media"' in qml
    assert 'text: "Script"' in qml
    assert "ScriptEditor" in qml
    assert "scriptController.flush()" in qml
    for unfinished in ('text: "Voice"', 'text: "Subtitles"', 'text: "Scenes"', 'text: "Timeline"'):
        assert unfinished not in qml


def test_script_editor_avoids_word_processor_rich_text_features():
    qml = Path("ui/qml/editor/ScriptEditor.qml").read_text(encoding="utf-8")
    forbidden = ["RichText", "font.bold", "font.italic", "textColorPicker", "html"]
    assert not any(item in qml for item in forbidden)

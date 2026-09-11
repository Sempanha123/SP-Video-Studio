from pathlib import Path


def test_workspace_exposes_transcription_without_future_phase_features():
    workspace = Path("ui/qml/pages/ProjectWorkspacePage.qml").read_text(encoding="utf-8")
    assert 'text: "Transcription"' in workspace
    assert "TranscriptionPanel" in workspace
    assert "transcriptionController.setMedia" in workspace
    assert "transcriptionController.saveEdits" in workspace
    for future in ('text: "Timeline"',):
        assert future not in workspace


def test_transcription_panel_keeps_basic_flow_simple_and_advanced_collapsed():
    panel = Path("ui/qml/editor/TranscriptionPanel.qml").read_text(encoding="utf-8")
    for expected in (
        "Speech Recognition",
        "Auto Detect",
        "English",
        "Khmer",
        "Word timestamps",
        "Remove long silences",
        "Advanced",
        "Re-transcribe",
        "Open Models",
    ):
        assert expected in panel
    assert "showSetup" in panel
    assert "transcriptChanged();" not in panel


def test_transcript_editor_has_edit_search_reset_export_and_playback_actions():
    editor = Path("ui/qml/editor/TranscriptEditor.qml").read_text(encoding="utf-8")
    row = Path("ui/qml/editor/TranscriptSegmentRow.qml").read_text(encoding="utf-8")
    toolbar = Path("ui/qml/editor/TranscriptToolbar.qml").read_text(encoding="utf-8")
    combined = editor + row + toolbar
    for expected in (
        "Copy Full Transcript",
        "Export TXT",
        "Reset to Generated Text",
        "playSegment",
        "editSegment",
        "setSearch",
    ):
        assert expected in combined
    assert "speaker diarization" not in combined.lower()

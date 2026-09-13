from __future__ import annotations

import time
from pathlib import Path

from domain.command import Command, CommandCategory
from domain.settings import AppSettings
from domain.shortcut_context import ShortcutContext, contexts_overlap
from services.command_service import CommandService
from services.shortcut_conflict_service import ShortcutConflictService
from services.shortcut_service import ShortcutService, default_commands, normalize_sequence


class _Settings:
    def __init__(self, root: Path):
        self.current = AppSettings.defaults(root)
        self.updates = []

    def update(self, **changes):
        self.current = self.current.with_changes(**changes)
        self.updates.append(changes)
        return self.current


def _shortcuts(tmp_path: Path):
    commands = CommandService(default_commands())
    settings = _Settings(tmp_path)
    service = ShortcutService(commands, settings, ShortcutConflictService())
    return commands, settings, service


def test_command_ids_are_unique():
    ids = [item.id for item in default_commands()]
    assert len(ids) == len(set(ids))


def test_central_defaults_include_required_global_shortcuts():
    rows = {item.id: item.default_shortcut for item in default_commands()}
    assert rows["app.save"] == "Ctrl+S"
    assert rows["edit.undo"] == "Ctrl+Z"
    assert rows["edit.redo"] == "Ctrl+Y"
    assert rows["app.command_palette"] == "Ctrl+Shift+P"


def test_timeline_shortcuts_are_central():
    rows = {item.id: item.default_shortcut for item in default_commands()}
    assert rows["timeline.split"] == "Ctrl+B"
    assert rows["timeline.delete"] == "Delete"
    assert rows["timeline.duplicate"] == "Ctrl+D"
    assert rows["timeline.marker"] == "M"
    assert rows["timeline.snap"] == "S"
    assert rows["timeline.fit"] == "Shift+F"


def test_speech_shortcuts_are_central():
    rows = {item.id: item.default_shortcut for item in default_commands()}
    assert rows["speech.generate"] == "Ctrl+Enter"
    assert rows["speech.find"] == "Ctrl+F"
    assert rows["speech.delete"] == "Delete"
    assert rows["speech.previous"] == "Alt+Up"
    assert rows["speech.next"] == "Alt+Down"


def test_audio_mappings_avoid_timeline_m_s_conflict():
    rows = {item.id: item.default_shortcut for item in default_commands()}
    assert rows["audio.mute"] == "Shift+M"
    assert rows["audio.solo"] == "Shift+S"


def test_normalization_handles_literal_zoom_keys():
    assert normalize_sequence("+") == "+"
    assert normalize_sequence("-") == "-"


def test_context_specific_duplicate_can_reuse_ctrl_d(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Ctrl+D", "timeline").id == "timeline.duplicate"
    assert service.command_for_sequence("Ctrl+D", "speech_editor").id == "speech.duplicate"


def test_timeline_m_is_marker(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("M", "timeline").id == "timeline.marker"


def test_source_range_i_o_x_are_context_scoped(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("I", "source_range").id == "range.in"
    assert service.command_for_sequence("O", "source_range").id == "range.out"
    assert service.command_for_sequence("X", "source_range").id == "range.clear"
    assert service.command_for_sequence("I", "timeline") is None


def test_project_playback_is_available_in_timeline(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Space", "timeline").id == "playback.toggle"


def test_project_playback_is_available_in_speech(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Space", "speech_editor").id == "playback.toggle"


def test_text_focus_blocks_space_playback(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Space", "speech_editor", text_editing=True) is None


def test_text_focus_blocks_delete_entity(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Delete", "speech_editor", text_editing=True) is None
    assert service.command_for_sequence("Delete", "timeline", text_editing=True) is None


def test_text_focus_blocks_copy_paste_cut(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    for key in ("Ctrl+C", "Ctrl+V", "Ctrl+X"):
        assert service.command_for_sequence(key, "timeline", text_editing=True) is None


def test_text_focus_blocks_global_project_undo(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Ctrl+Z", "speech_editor", text_editing=True) is None


def test_text_focus_blocks_speech_generate(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Ctrl+Enter", "speech_editor", text_editing=True) is None


def test_text_focus_blocks_source_range_letters(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    for key in ("I", "O", "X"):
        assert service.command_for_sequence(key, "source_range", text_editing=True) is None


def test_modal_dialog_suppresses_background_shortcuts(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.bindings("timeline", modal_open=True) == []


def test_no_project_disables_project_editing_commands(tmp_path):
    _, _, service = _shortcuts(tmp_path)
    assert service.command_for_sequence("Ctrl+B", "timeline", project_open=False) is None
    assert service.command_for_sequence("Ctrl+Enter", "speech_editor", project_open=False) is None
    assert service.command_for_sequence("Ctrl+Shift+P", "global", project_open=False).id == "app.command_palette"


def test_global_and_timeline_assignments_conflict():
    assert contexts_overlap(ShortcutContext.GLOBAL, ShortcutContext.TIMELINE)


def test_timeline_and_speech_can_share_same_sequence():
    assert not contexts_overlap(ShortcutContext.TIMELINE, ShortcutContext.SPEECH_EDITOR)


def test_custom_shortcut_persists_by_command_id(tmp_path):
    commands, settings, service = _shortcuts(tmp_path)
    assert service.assign("timeline.split", "Ctrl+Shift+B") == []
    assert settings.current.shortcut_overrides == {"timeline.split": "Ctrl+Shift+B"}
    restored = ShortcutService(CommandService(default_commands()), settings, ShortcutConflictService())
    assert restored.commands.get("timeline.split").current_shortcut == "Ctrl+Shift+B"
    assert restored.command_for_sequence("Ctrl+B", "timeline") is None


def test_conflict_requires_explicit_replace(tmp_path):
    commands, _, service = _shortcuts(tmp_path)
    conflicts = service.assign("timeline.split", "Ctrl+D")
    assert conflicts
    assert commands.get("timeline.split").current_shortcut == "Ctrl+B"


def test_replace_conflict_clears_previous_command(tmp_path):
    commands, _, service = _shortcuts(tmp_path)
    service.assign("timeline.split", "Ctrl+D", replace=True)
    assert commands.get("timeline.split").current_shortcut == "Ctrl+D"
    assert commands.get("timeline.duplicate").current_shortcut == ""


def test_reset_command_restores_default(tmp_path):
    commands, _, service = _shortcuts(tmp_path)
    service.assign("timeline.split", "Ctrl+Shift+B")
    service.reset("timeline.split")
    assert commands.get("timeline.split").current_shortcut == "Ctrl+B"


def test_reset_all_restores_defaults(tmp_path):
    commands, settings, service = _shortcuts(tmp_path)
    service.assign("timeline.split", "Ctrl+Shift+B")
    service.assign("speech.generate", "Ctrl+G")
    service.reset_all()
    assert commands.get("timeline.split").current_shortcut == "Ctrl+B"
    assert commands.get("speech.generate").current_shortcut == "Ctrl+Enter"
    assert settings.current.shortcut_overrides == {}


def test_settings_round_trip_preserves_shortcuts(tmp_path):
    item = AppSettings.defaults(tmp_path).with_changes(
        shortcut_overrides={"timeline.split": "Ctrl+Shift+B", "speech.generate": "Ctrl+G"}
    )
    restored = AppSettings.from_dict(item.to_dict(), tmp_path)
    assert restored.shortcut_overrides == item.shortcut_overrides


def test_palette_search_is_context_aware(tmp_path):
    commands, _, _ = _shortcuts(tmp_path)
    results = commands.search("generate speech", "speech_editor", project_open=True)
    assert results and results[0].id in {"speech.generate", "speech.generate_outdated"}
    assert all(item.context in {ShortcutContext.SPEECH_EDITOR, ShortcutContext.PROJECT, ShortcutContext.GLOBAL} for item in results)


def test_palette_hides_project_commands_without_project(tmp_path):
    commands, _, _ = _shortcuts(tmp_path)
    ids = {item.id for item in commands.search("split", "global", project_open=False)}
    assert "timeline.split" not in ids


def test_1000_command_search_is_lightweight():
    many = [
        Command(f"mock.{i}", f"Mock Command {i}", "Synthetic registry search item", CommandCategory.GENERAL)
        for i in range(1000)
    ]
    service = CommandService(many)
    started = time.perf_counter()
    rows = service.search("mock command 999", "global", limit=25)
    elapsed = time.perf_counter() - started
    assert rows and rows[0].id == "mock.999"
    assert elapsed < 0.5


def test_phase33_runtime_layers_phase32():
    text = Path("app/phase33_runtime.py").read_text(encoding="utf-8")
    assert "app.manual_speech_runtime as p32" in text
    assert "p32.run()" in text
    assert "ProductivitySpeechController" in text


def test_single_qml_shortcut_router_owns_shortcut_objects():
    router = Path("ui/qml/shortcuts/ShortcutRouter.qml").read_text(encoding="utf-8")
    timeline = Path("ui/qml/timeline/TimelineEditor.qml").read_text(encoding="utf-8")
    speech = Path("ui/qml/speech/SpeechEditor.qml").read_text(encoding="utf-8")
    assert "delegate: Shortcut" in router
    assert "Shortcut { sequence" not in timeline
    assert "Shortcut { sequence" not in speech


def test_qml_router_detects_text_editors_and_inactive_window():
    text = Path("ui/qml/shortcuts/ShortcutRouter.qml").read_text(encoding="utf-8")
    assert '"cursorPosition" in item' in text
    assert "Commands.setTextEditing" in text
    assert "Commands.setWindowActive(window.active)" in text


def test_qml_modal_dialogs_gate_shortcuts():
    palette = Path("ui/qml/shortcuts/CommandPalette.qml").read_text(encoding="utf-8")
    settings = Path("ui/qml/shortcuts/ShortcutSettings.qml").read_text(encoding="utf-8")
    assert "Commands.setModalOpen(true)" in palette
    assert "Commands.setModalOpen(true)" in settings


def test_timeline_qml_routes_required_actions():
    text = Path("ui/qml/timeline/TimelineEditor.qml").read_text(encoding="utf-8")
    for command in ("timeline.split", "timeline.delete", "timeline.duplicate", "timeline.marker", "timeline.snap", "edit.undo", "edit.redo"):
        assert command in text


def test_speech_qml_routes_required_actions():
    text = Path("ui/qml/speech/SpeechEditor.qml").read_text(encoding="utf-8")
    for command in ("speech.generate", "speech.find", "speech.delete", "speech.duplicate", "speech.previous", "speech.next", "speech.edit"):
        assert command in text


def test_shorts_qml_scopes_in_out_commands():
    text = Path("ui/qml/shorts/ShortsStudio.qml").read_text(encoding="utf-8")
    assert 'Commands.setContext("source_range")' in text
    assert 'commandId==="range.in"' in text
    assert 'commandId==="range.out"' in text
    assert 'commandId==="range.clear"' in text


def test_audio_qml_uses_non_ambiguous_mute_solo_commands():
    text = Path("ui/qml/audio/AudioMixer.qml").read_text(encoding="utf-8")
    assert 'commandId==="audio.mute"' in text
    assert 'commandId==="audio.solo"' in text
    assert "Shift+M mute · Shift+S solo" in text


def test_main_has_palette_help_and_shortcut_settings():
    text = Path("ui/qml/Main.qml").read_text(encoding="utf-8")
    assert "CommandPalette" in text
    assert "KeyboardShortcutHelp" in text
    assert "ShortcutSettings" in text
    assert "ShortcutRouter" in text


def test_documentation_lists_focus_protection():
    text = Path("docs/PHASE33_KEYBOARD_SHORTCUTS_PRODUCTIVITY.md").read_text(encoding="utf-8")
    assert "Text inputs" in text
    assert "Ctrl+Shift+P" in text
    assert "cross-project" in text.lower()


def test_reserved_editing_shortcut_warns_for_unrelated_command():
    conflicts = ShortcutConflictService()
    assert conflicts.reserved_warning("Ctrl+C", "asset.preview")
    assert conflicts.reserved_warning("Ctrl+C", "timeline.copy") == ""


def test_shortcut_settings_search_can_match_sequence(tmp_path):
    commands, _, _ = _shortcuts(tmp_path)
    matches = [item for item in commands.all() if "ctrl+enter" in item.current_shortcut.casefold()]
    assert any(item.id == "speech.generate" for item in matches)

from __future__ import annotations

import logging
from collections.abc import Iterable

from domain.command import Command, CommandCategory
from domain.shortcut import PROTECTED_TEXT_SEQUENCES, ShortcutBinding
from domain.shortcut_context import ShortcutContext, context_priority
from services.command_service import CommandService
from services.shortcut_conflict_service import ShortcutConflictService

try:
    from PySide6.QtGui import QKeySequence
except Exception:  # pragma: no cover - pure model tests can run without Qt
    QKeySequence = None


def normalize_sequence(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if text in {"+", "-"}:
        return text
    if QKeySequence is not None:
        normalized = QKeySequence(text).toString(QKeySequence.PortableText)
        return normalized or text
    aliases = {
        "DEL": "Delete", "ESC": "Escape", "RETURN": "Enter",
        "CTRL": "Ctrl", "CONTROL": "Ctrl", "SHIFT": "Shift", "ALT": "Alt",
        "LEFT": "Left", "RIGHT": "Right", "UP": "Up", "DOWN": "Down",
        "SPACE": "Space", "HOME": "Home", "END": "End",
    }
    parts = [part.strip() for part in text.split("+") if part.strip()]
    out: list[str] = []
    for part in parts:
        upper = part.upper()
        out.append(aliases.get(upper, part.upper() if len(part) == 1 else part.title()))
    modifiers = [p for p in ("Ctrl", "Alt", "Shift", "Meta") if p in out]
    keys = [p for p in out if p not in modifiers]
    return "+".join(modifiers + keys)


def default_commands() -> list[Command]:
    C = Command
    G = ShortcutContext
    K = CommandCategory
    project = {"requiresProject": True}
    return [
        C("app.save", "Save", "Flush the current autosave state.", K.GENERAL, "Ctrl+S", context=G.GLOBAL),
        C("edit.undo", "Undo", "Undo the latest project edit.", K.EDITING, "Ctrl+Z", context=G.PROJECT, metadata=project),
        C("edit.redo", "Redo", "Redo the latest project edit.", K.EDITING, "Ctrl+Y", context=G.PROJECT, metadata=project),
        C("edit.redo_alt", "Redo", "Alternative redo shortcut.", K.EDITING, "Ctrl+Shift+Z", context=G.PROJECT, metadata=project),
        C("app.command_palette", "Command Palette", "Search and run available commands.", K.GENERAL, "Ctrl+Shift+P", context=G.GLOBAL),
        C("project.open", "Open Project", "Open the Projects workspace.", K.PROJECT, "Ctrl+O", context=G.GLOBAL),
        C("project.new", "New Project", "Open the Create workspace.", K.PROJECT, "Ctrl+N", context=G.GLOBAL),
        C("app.settings", "Settings", "Open application settings.", K.GENERAL, "Ctrl+,", context=G.GLOBAL),
        C("app.shortcuts", "Keyboard Shortcuts", "Open keyboard shortcut settings and help.", K.GENERAL, "F1", context=G.GLOBAL),
        C("app.escape", "Cancel / Close", "Close a popup, cancel the active interaction, or clear selection.", K.GENERAL, "Escape", context=G.GLOBAL),
        C("playback.toggle", "Play / Pause", "Toggle editor preview playback.", K.PLAYBACK, "Space", context=G.PROJECT, metadata=project),
        C("playback.start", "Go to Project Start", "Seek to the project start.", K.PLAYBACK, "Home", context=G.PROJECT, metadata=project),
        C("playback.end", "Go to Project End", "Seek to the project end.", K.PLAYBACK, "End", context=G.PROJECT, metadata=project),
        C("playback.seek_back", "Seek Backward", "Seek backward by the normal step.", K.PLAYBACK, "Left", context=G.PROJECT, metadata=project),
        C("playback.seek_forward", "Seek Forward", "Seek forward by the normal step.", K.PLAYBACK, "Right", context=G.PROJECT, metadata=project),
        C("playback.seek_back_large", "Seek Backward More", "Seek backward by the larger step.", K.PLAYBACK, "Shift+Left", context=G.PROJECT, metadata=project),
        C("playback.seek_forward_large", "Seek Forward More", "Seek forward by the larger step.", K.PLAYBACK, "Shift+Right", context=G.PROJECT, metadata=project),
        C("playback.frame_previous", "Previous Frame", "Step using project FPS quantization.", K.PLAYBACK, "Alt+Left", context=G.PROJECT, metadata=project),
        C("playback.frame_next", "Next Frame", "Step using project FPS quantization.", K.PLAYBACK, "Alt+Right", context=G.PROJECT, metadata=project),
        C("timeline.split", "Split at Playhead", "Split the selected timeline scene at the playhead.", K.TIMELINE, "Ctrl+B", context=G.TIMELINE, metadata=project),
        C("timeline.delete", "Delete Selected", "Delete the selected timeline item safely.", K.TIMELINE, "Delete", context=G.TIMELINE, metadata=project),
        C("timeline.duplicate", "Duplicate Selected", "Duplicate the selected timeline item.", K.TIMELINE, "Ctrl+D", context=G.TIMELINE, metadata=project),
        C("timeline.copy", "Copy", "Copy the selected timeline entity to the internal project clipboard.", K.TIMELINE, "Ctrl+C", context=G.TIMELINE, metadata=project),
        C("timeline.cut", "Cut", "Copy and remove the selected timeline entity.", K.TIMELINE, "Ctrl+X", context=G.TIMELINE, metadata=project),
        C("timeline.paste", "Paste at Playhead", "Paste a compatible copied entity near the playhead.", K.TIMELINE, "Ctrl+V", context=G.TIMELINE, metadata=project),
        C("timeline.select_all", "Select All Timeline Items", "Select all compatible items in the active timeline context.", K.TIMELINE, "Ctrl+A", context=G.TIMELINE, metadata=project),
        C("timeline.clear_selection", "Clear Timeline Selection", "Clear the active timeline selection.", K.TIMELINE, "", context=G.TIMELINE, metadata=project),
        C("timeline.marker", "Add Marker", "Add a marker at the playhead.", K.TIMELINE, "M", context=G.TIMELINE, metadata=project),
        C("timeline.snap", "Toggle Snap", "Toggle timeline snapping.", K.TIMELINE, "S", context=G.TIMELINE, checkable=True, metadata=project),
        C("timeline.zoom_in", "Timeline Zoom In", "Increase timeline zoom.", K.VIEW, "+", context=G.TIMELINE, metadata=project),
        C("timeline.zoom_out", "Timeline Zoom Out", "Decrease timeline zoom.", K.VIEW, "-", context=G.TIMELINE, metadata=project),
        C("timeline.fit", "Fit Timeline", "Fit the project timeline to the visible width.", K.VIEW, "Shift+F", context=G.TIMELINE, metadata=project),
        C("timeline.trim_start", "Trim Start to Playhead", "Trim the selected scene start when safe.", K.TIMELINE, "Q", context=G.TIMELINE, metadata=project),
        C("timeline.trim_end", "Trim End to Playhead", "Trim the selected scene end when safe.", K.TIMELINE, "W", context=G.TIMELINE, metadata=project),
        C("speech.generate", "Generate Selected Speech", "Generate current or selected SpeechBlock audio.", K.SPEECH_TTS, "Ctrl+Enter", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.find", "Find & Replace Speech", "Focus speech search and replace.", K.SPEECH_TTS, "Ctrl+F", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.delete", "Delete Selected Speech", "Delete selected SpeechBlocks.", K.SPEECH_TTS, "Delete", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.duplicate", "Duplicate Selected Speech", "Duplicate selected SpeechBlock where valid.", K.SPEECH_TTS, "Ctrl+D", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.select_all", "Select All Speech", "Select all SpeechBlocks.", K.SPEECH_TTS, "Ctrl+A", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.previous", "Previous SpeechBlock", "Move selection to the previous SpeechBlock.", K.NAVIGATION, "Alt+Up", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.next", "Next SpeechBlock", "Move selection to the next SpeechBlock.", K.NAVIGATION, "Alt+Down", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.edit", "Edit Speech Text", "Edit the selected SpeechBlock text.", K.SPEECH_TTS, "Enter", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.generate_outdated", "Generate All Outdated Speech", "Generate only outdated SpeechBlocks.", K.SPEECH_TTS, "", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.set_voice", "Set Voice for Selected SpeechBlocks", "Assign a Voice Studio profile to selected speech.", K.SPEECH_TTS, "", context=G.SPEECH_EDITOR, metadata=project),
        C("speech.set_speaker", "Set Speaker for Selected", "Assign a project speaker to selected speech.", K.SPEECH_TTS, "", context=G.SPEECH_EDITOR, metadata=project),
        C("subtitle.commit", "Commit Subtitle Edit", "Commit the active subtitle edit.", K.SUBTITLES, "Ctrl+Enter", context=G.SUBTITLE_EDITOR, metadata=project),
        C("subtitle.find", "Search Subtitles", "Search subtitle cues.", K.SUBTITLES, "Ctrl+F", context=G.SUBTITLE_EDITOR, metadata=project),
        C("subtitle.replace", "Find & Replace Subtitles", "Find and replace subtitle cue text.", K.SUBTITLES, "Ctrl+Shift+F", context=G.SUBTITLE_EDITOR, metadata=project),
        C("subtitle.split", "Split Subtitle Cue", "Split a subtitle cue where safe.", K.SUBTITLES, "Ctrl+B", context=G.SUBTITLE_EDITOR, metadata=project),
        C("subtitle.delete", "Delete Subtitle Cue", "Delete the selected subtitle cue.", K.SUBTITLES, "Delete", context=G.SUBTITLE_EDITOR, metadata=project),
        C("subtitle.duplicate", "Duplicate Subtitle Cue", "Duplicate the selected subtitle cue.", K.SUBTITLES, "Ctrl+D", context=G.SUBTITLE_EDITOR, metadata=project),
        C("word.previous", "Previous Word", "Move to the previous word timing item.", K.NAVIGATION, "Alt+Left", context=G.WORD_TIMING, metadata=project),
        C("word.next", "Next Word", "Move to the next word timing item.", K.NAVIGATION, "Alt+Right", context=G.WORD_TIMING, metadata=project),
        C("media.import", "Import Media", "Import media into the current project.", K.MEDIA, "Ctrl+I", context=G.MEDIA_LIBRARY, metadata=project),
        C("media.remove", "Remove Selected Media", "Remove selected media from the project safely.", K.MEDIA, "Delete", context=G.MEDIA_LIBRARY, metadata=project),
        C("media.preview", "Preview Selected Media", "Preview the selected project asset.", K.MEDIA, "Enter", context=G.MEDIA_LIBRARY, metadata=project),
        C("media.search", "Search Media", "Focus media search.", K.MEDIA, "Ctrl+F", context=G.MEDIA_LIBRARY, metadata=project),
        C("asset.import", "Import Global Assets", "Import files into the Global Asset Library.", K.MEDIA, "Ctrl+I", context=G.ASSET_LIBRARY),
        C("asset.preview", "Preview Global Asset", "Preview the selected Global Asset.", K.MEDIA, "Enter", context=G.ASSET_LIBRARY),
        C("asset.search", "Search Global Assets", "Focus Global Asset search.", K.MEDIA, "Ctrl+F", context=G.ASSET_LIBRARY),
        C("asset.remove", "Remove Global Asset", "Remove the selected Global Asset using the normal confirmation flow.", K.MEDIA, "Delete", context=G.ASSET_LIBRARY, dangerous=True),
        C("audio.mute", "Mute Selected Audio", "Mute the selected mixer item.", K.AUDIO, "Shift+M", context=G.AUDIO_MIXER, metadata=project),
        C("audio.solo", "Solo Selected Track", "Solo the selected mixer track.", K.AUDIO, "Shift+S", context=G.AUDIO_MIXER, metadata=project),
        C("range.in", "Set In", "Set range In at the current source position.", K.EDITING, "I", context=G.SOURCE_RANGE, metadata=project),
        C("range.out", "Set Out", "Set range Out at the current source position.", K.EDITING, "O", context=G.SOURCE_RANGE, metadata=project),
        C("range.clear", "Clear In / Out", "Clear the current source range.", K.EDITING, "X", context=G.SOURCE_RANGE, metadata=project),
        C("workspace.media", "Focus Media Panel", "Focus the project media panel.", K.NAVIGATION, "", context=G.PROJECT, metadata=project),
        C("workspace.preview", "Focus Preview", "Focus the project preview.", K.NAVIGATION, "", context=G.PROJECT, metadata=project),
        C("workspace.inspector", "Focus Inspector", "Focus the active inspector.", K.NAVIGATION, "", context=G.PROJECT, metadata=project),
        C("workspace.timeline", "Focus Timeline", "Focus the Timeline.", K.NAVIGATION, "", context=G.PROJECT, metadata=project),
        C("workspace.speech", "Focus Speech Editor", "Focus the Speech/TTS editor.", K.NAVIGATION, "", context=G.PROJECT, metadata=project),
    ]


class ShortcutService:
    def __init__(
        self,
        commands: CommandService | None = None,
        settings_service=None,
        conflict_service: ShortcutConflictService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.commands = commands or CommandService(default_commands())
        self.settings_service = settings_service
        self.conflicts = conflict_service or ShortcutConflictService()
        self.logger = logger or logging.getLogger("sp_video_studio.shortcuts")
        self._apply_overrides()

    def _apply_overrides(self) -> None:
        overrides = {}
        if self.settings_service is not None:
            overrides = dict(getattr(self.settings_service.current, "shortcut_overrides", {}) or {})
        for command in self.commands.all():
            command.current_shortcut = normalize_sequence(
                overrides.get(command.id, command.default_shortcut)
            )

    def bindings(
        self,
        context: str | ShortcutContext,
        *,
        text_editing: bool = False,
        modal_open: bool = False,
        project_open: bool = True,
    ) -> list[ShortcutBinding]:
        if modal_open:
            return []
        priorities = set(context_priority(context))
        result: list[ShortcutBinding] = []
        for command in self.commands.all():
            sequence = normalize_sequence(command.current_shortcut)
            if not sequence or command.context not in priorities:
                continue
            if command.metadata.get("requiresProject", False) and not project_open:
                continue
            if text_editing and sequence in PROTECTED_TEXT_SEQUENCES:
                # Native TextField/TextArea behavior always wins.
                continue
            result.append(ShortcutBinding(command.id, sequence, command.context, command.enabled))
        return result

    def command_for_sequence(
        self,
        sequence: str,
        context: str | ShortcutContext,
        *,
        text_editing: bool = False,
        modal_open: bool = False,
        project_open: bool = True,
    ) -> Command | None:
        normalized = normalize_sequence(sequence)
        if not normalized:
            return None
        bindings = self.bindings(
            context,
            text_editing=text_editing,
            modal_open=modal_open,
            project_open=project_open,
        )
        priorities = context_priority(context)
        for priority in priorities:
            for binding in bindings:
                if binding.sequence == normalized and binding.context == priority:
                    return self.commands.get(binding.command_id)
        return None

    def assign(self, command_id: str, sequence: str, *, replace: bool = False) -> list:
        command = self.commands.get(command_id)
        if command is None:
            raise KeyError(command_id)
        normalized = normalize_sequence(sequence)
        conflicts = self.conflicts.conflicts(normalized, command_id, self.commands.all())
        if conflicts and not replace:
            return conflicts
        if replace:
            for conflict in conflicts:
                other = self.commands.get(conflict.command_id)
                if other is not None:
                    other.current_shortcut = ""
        command.current_shortcut = normalized
        self._persist()
        if self.logger:
            self.logger.info("Custom shortcut changed: %s -> %s", command_id, normalized or "(none)")
        return []

    def reset(self, command_id: str) -> None:
        command = self.commands.get(command_id)
        if command is None:
            raise KeyError(command_id)
        command.current_shortcut = normalize_sequence(command.default_shortcut)
        self._persist()

    def reset_all(self) -> None:
        for command in self.commands.all():
            command.current_shortcut = normalize_sequence(command.default_shortcut)
        self._persist()

    def _persist(self) -> None:
        if self.settings_service is None:
            return
        overrides = {
            item.id: item.current_shortcut
            for item in self.commands.all()
            if normalize_sequence(item.current_shortcut) != normalize_sequence(item.default_shortcut)
        }
        self.settings_service.update(shortcut_overrides=overrides)

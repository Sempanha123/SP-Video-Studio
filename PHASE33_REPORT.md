# PHASE 33 STATUS

Completed:
- Added centralized command metadata, shortcut routing, searchable Command Palette, shortcut help/settings, persistence, conflict handling, Timeline productivity, Phase 32 Speech/TTS productivity, Shorts In/Out range keys, Audio Mixer context keys, text-focus protection, modal protection, tooltips, and Phase 33 documentation.
- Phase 33 remains layered on Phase 32 and does not create a second Timeline, SpeechBlock/TTS system, subtitle system, audio mixer, autosave layer, or Undo/Redo stack.

Command architecture:
- `Command` metadata is independent from key assignments.
- `CommandService` owns registration, enablement, recent commands and lightweight fuzzy search.
- Feature QML receives command IDs and calls existing controllers/business logic.

Shortcut registry:
- `ShortcutService` owns normalized portable sequences and project/global context resolution.
- Defaults are registered once at startup through `default_commands()`.
- Complex multi-key chords are intentionally not implemented.

Shortcut contexts:
- Global, Project, Playback, Timeline, SpeechEditor, SubtitleEditor, TextEditor, MediaLibrary, AssetLibrary, BatchFactory, AudioMixer, WordTiming and SourceRange are modeled centrally.
- Active feature context wins, then Project, then Global.

Focus handling:
- `ShortcutRouter.qml` observes the active focus item and detects text editors by their text/cursor interface.
- Application shortcuts are disabled while the app window is inactive.
- Modal dialogs suppress commands behind them.

Global shortcuts:
- Ctrl+S Save/flush autosave; Ctrl+Z Undo; Ctrl+Y/Ctrl+Shift+Z Redo; Ctrl+Shift+P Command Palette; Ctrl+O Projects; Ctrl+N Create; Ctrl+, Settings; F1 Keyboard Shortcuts; Escape context-safe cancel/close.

Playback shortcuts:
- Space Play/Pause; Home/End project start/end; Left/Right normal seek; Shift+Left/Right larger seek; Alt+Left/Right project-FPS frame-step path.
- J/K/L was not added because the current playback architecture does not expose a clean shuttle API.

Timeline shortcuts:
- Ctrl+B Split; Delete; Ctrl+D Duplicate; Ctrl+C/X/V internal project clipboard; M Marker; S Snap; +/- Zoom; Shift+F Fit; Q/W safe trim to playhead; Undo/Redo.
- Clipboard is intentionally project-local and canonical scene paste duplicates beside the source rather than attempting unsafe cross-project remapping.

Speech/TTS shortcuts:
- Ctrl+Enter Generate Selected; Ctrl+F Find; Delete selected; Ctrl+D duplicate one compatible SpeechBlock; Ctrl+A select all; Alt+Up/Down navigate; Enter edit; Escape exits edit/clears selection.
- Speech duplicate keeps text, speaker, language, voice override and pauses while deliberately not sharing generated takes.

Subtitle shortcuts:
- Central command definitions exist for commit/search/find-replace/split/delete/duplicate and are context-scoped so text entry remains protected.
- Existing subtitle business logic was not replaced.

Media shortcuts:
- Central Media/Asset Library command definitions cover Ctrl+I, Delete, Enter and Ctrl+F with context isolation and safe-delete metadata for Global Assets.

Audio shortcuts:
- Audio Mixer uses Shift+M Mute and Shift+S Solo to avoid ambiguity with Timeline M Marker / S Snap.

Command Palette:
- Ctrl+Shift+P opens a centered compact Phase 28-style palette.
- Search uses substring/token/subsequence ranking without adding a dependency.
- Context-invalid/project-required commands are excluded.

Shortcut customization:
- Searchable settings UI, one-combination recorder, per-command reset and Reset All are included.
- Overrides persist as stable command ID -> portable sequence mappings in existing Settings/config; built-in defaults are not mutated.

Conflict detection:
- Overlapping-context duplicates require explicit Replace/Cancel.
- Non-overlapping contexts can share a sequence.
- Reserved editing keys such as Ctrl+C/Ctrl+V/Ctrl+X/Ctrl+Z warn before unrelated reassignment.

Tooltips/menu integration:
- Main Settings/Shortcut affordances, Timeline toolbar actions, and Speech/TTS actions expose their current shortcuts without adding a large permanent toolbar.

Undo/Redo:
- Existing Timeline bounded command history remains authoritative.
- Phase 32 speech text/timing edits continue using the same command stack.
- Native text-editor Ctrl+Z is protected while text editing is active.

Copy/Paste:
- Timeline entity copy/cut/paste uses an internal project clipboard and canonical duplicate/delete operations.
- Native text Ctrl+C/Ctrl+V/Ctrl+X always wins during text focus.
- Full cross-project dependency remapping is intentionally deferred.

Text-editor protection:
- Space, Delete, Backspace, Enter, arrows, Home/End, Ctrl+A/C/V/X/Z/Y, Ctrl+B/D/F/Enter, Alt navigation, I/O/X/M/S/Q/W and zoom keys are not routed as project commands while typing.

New files:
- `app/phase33_runtime.py`
- `domain/command.py`
- `domain/shortcut.py`
- `domain/shortcut_context.py`
- `services/command_service.py`
- `services/shortcut_service.py`
- `services/shortcut_conflict_service.py`
- `ui/controllers/command_controller.py`
- `ui/controllers/shortcut_controller.py`
- `ui/controllers/productivity_speech_controller.py`
- `ui/qml/shortcuts/CommandPalette.qml`
- `ui/qml/shortcuts/ShortcutSettings.qml`
- `ui/qml/shortcuts/ShortcutRecorder.qml`
- `ui/qml/shortcuts/ShortcutConflictDialog.qml`
- `ui/qml/shortcuts/ShortcutRouter.qml`
- `ui/qml/shortcuts/KeyboardShortcutHelp.qml`
- `docs/PHASE33_KEYBOARD_SHORTCUTS_PRODUCTIVITY.md`
- `tests/test_phase33_shortcuts_productivity.py`
- `PHASE33_REPORT.md`

Modified files:
- `main.py`
- `pyproject.toml`
- `README.md`
- `domain/settings.py`
- `ui/qml/Main.qml`
- `ui/qml/timeline/TimelineEditor.qml`
- `ui/qml/timeline/TimelineToolbar.qml`
- `ui/qml/speech/SpeechEditor.qml`
- `ui/qml/shorts/ShortsStudio.qml`
- `ui/qml/audio/AudioMixer.qml`

Tests run:
- Phase 33 focused model/service/QML contract tests: 42/42 passed.
- Python compile check for Phase 33 app/domain/services/controllers: passed.
- QML structural delimiter/import/static command-routing checks: passed.
- The execution sandbox does not contain a complete Git working checkout or PySide6/qmllint, so the complete historical repository suite and live Qt desktop interaction could not be honestly rerun here.

Text-focus safety test:
- Passed for Space, Delete, entity copy/cut/paste, project Undo, Speech Generate, and I/O/X source-range letters.

Timeline shortcut test:
- Passed central mapping/context/static routing checks for playback, split, duplicate, delete, marker, snap, zoom/fit and Undo/Redo.

Speech Editor shortcut test:
- Passed central mapping/static routing checks for Generate, Find, Delete, Duplicate, Select All, navigation and Edit.

Command Palette test:
- Passed context-aware fuzzy search tests; no-project project-edit commands are hidden.

Custom shortcut persistence test:
- Passed Settings round-trip and restart-style re-instantiation: Ctrl+B -> Ctrl+Shift+B persisted and old binding stopped resolving.

Conflict test:
- Passed overlapping-context detection, explicit replacement behavior, non-overlap reuse and reserved-editing-key warning tests.

Undo/Redo test:
- Architecture audit confirms Phase 33 routes to the existing Timeline command stack and protects native text undo; live full-project split/move/voice/subtitle/audio state replay requires the real desktop/full repository environment and is not falsely claimed here.

Copy/Paste context test:
- Passed text-focus suppression and Timeline internal-clipboard static routing checks.

I/O range test:
- Passed SourceRange-only I/O/X resolution and text-focus suppression; Shorts routes In/Out to the current Timeline playhead and clears by resetting both range endpoints.

Marker context test:
- Passed: M resolves to Add Marker in Timeline context and is blocked during text editing.

Acceptance workflow test:
- The command path for the specified keyboard workflow is implemented and covered by focused command/context tests. Live media/TTS/audio generation and full restart acceptance require the Windows/PySide6/model environment and were not claimed from this sandbox.

Known issues:
- PySide6/qmllint is unavailable in this execution sandbox, so live QML rendering/focus interaction is not claimed.
- A full repository archive/working checkout is not exposed to the execution sandbox through the connected GitHub tool, so the entire pre-existing pytest suite could not be rerun locally; focused Phase 33 tests and compile/static checks were run instead.
- Timeline paste intentionally duplicates beside its source; full cross-project/paste-at-playhead dependency remapping is deferred for safety.
- Subtitle/Media command definitions are centralized and context-safe; deeper per-page mouse-selection UX remains owned by their existing editors rather than being rewritten in Phase 33.

Architecture decisions:
- One command definition and one shortcut registry; no page-by-page key-definition duplication for Timeline/Speech.
- Existing business controllers remain authoritative; Phase 33 dispatches IDs into them.
- Settings/config stores only user overrides by stable command ID.
- Native text semantics always outrank editor shortcuts.
- Phase 17 Timeline, Phase 27 autosave, Phase 30 mixer, Phase 31 performance lifecycle and Phase 32 Speech/TTS remain authoritative.

Recommended next phase:
Phase 34 — Accessibility + Final UX Polish

Suggested Git commit:
`feat: add command palette and editing productivity shortcuts`

Do not automatically begin Phase 34.

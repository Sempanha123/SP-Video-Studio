# Phase 33 — Keyboard Shortcuts & Editing Productivity

Phase 33 adds one lightweight application command registry and one shortcut service above the existing editor controllers. It does not replace Timeline, SpeechBlock, subtitles, autosave, the Phase 30 mixer, or the existing bounded Undo/Redo stack.

## Command architecture

Commands are stable metadata (`id`, name, description, category, default/current shortcut, context, enabled/checkable/dangerous flags and metadata). Shortcut assignment is separate from command execution. `CommandService` owns registration/fuzzy search/recent commands; `ShortcutService` owns Qt-compatible normalized sequences and persisted overrides; `ShortcutConflictService` owns overlapping-context validation.

The QML `ShortcutRouter` is the only application-wide `Shortcut` producer. Feature pages listen for command IDs and invoke their existing controller operations. This removes the Phase 32 page-local shortcut definitions from Timeline and Speech/TTS.

## Contexts and focus

Contexts are Global, Project, Timeline, Speech Editor, Subtitle Editor, Text Editor, Media Library, Asset Library, Batch Factory, Audio Mixer, Word Timing and Source Range. The active feature context has priority, then Project, then Global.

`ShortcutRouter` watches the active QML focus item. Text inputs are recognized by their text/cursor interface and protected before routing. While typing, Space, Delete, Enter, arrows, Ctrl+A/C/V/X/Z/Y, Ctrl+F, Ctrl+Enter, I/O/M/S/Q/W and related editor keys are left to the native text control. Modal dialogs suppress background shortcuts, and application shortcuts are disabled when the window is inactive.

## Default shortcuts

- Ctrl+S — save / flush autosave
- Ctrl+Z — Undo; Ctrl+Y or Ctrl+Shift+Z — Redo
- Ctrl+Shift+P — Command Palette
- Ctrl+O — Projects; Ctrl+N — Create; Ctrl+, — Settings; F1 — Keyboard Shortcuts
- Space — Play/Pause while a project editor is active
- Home / End — project start/end
- Left / Right — seek; Shift+Left / Shift+Right — larger seek
- Alt+Left / Alt+Right — frame step using the existing project-FPS quantization path
- Ctrl+B — split selected Timeline scene
- Delete — context-safe delete
- Ctrl+D — context-safe duplicate
- Ctrl+C / Ctrl+X / Ctrl+V — Timeline internal project clipboard operations
- M — add Timeline marker; S — toggle Timeline snap
- + / - — Timeline zoom; Shift+F — fit Timeline
- Q / W — trim start/end to playhead when the selected scene supports it
- Ctrl+Enter — generate selected Speech/TTS
- Ctrl+F — Speech find/search
- Alt+Up / Alt+Down — previous/next SpeechBlock
- Enter — edit selected SpeechBlock
- Ctrl+I — import in media/library contexts
- Shift+M / Shift+S — Audio Mixer mute/solo command definitions to avoid Timeline M/S ambiguity
- I / O / X — Source/Shorts range In, Out and Clear only in the source-range context

## Command Palette

Ctrl+Shift+P opens a compact Phase 28-themed palette. Search is implemented with a small substring/token/subsequence scorer rather than a dependency. The registry is lightweight and already resident; heavy feature work runs only after command execution. Context-invalid commands are not returned.

## Shortcut customization

Keyboard Shortcut settings provide search, one-combination recording, per-command reset and Reset All. Overrides are stored in application Settings as stable command ID → portable key-sequence mappings; translated labels are never used as storage IDs. Built-in defaults remain unchanged.

When a shortcut overlaps another active context, replacement requires an explicit conflict decision. The same sequence may exist in clearly non-overlapping contexts. Complex multi-key chords are intentionally deferred.

## Timeline productivity

Timeline command routing reuses `TimelineController` and the Phase 17/31 edit paths for playback, split, duplicate, delete, marker, snap, zoom, fit, safe trim, Undo and Redo. The internal Timeline clipboard is project-local; cross-project dependency remapping is intentionally not attempted. Scene paste uses the canonical duplicate operation, which inserts beside its source, preserving project ownership and undo behavior.

## Speech/TTS productivity

Phase 32 remains canonical. Ctrl+Enter generates selected speech, Ctrl+F focuses find, Delete deletes selected blocks outside text editing, Ctrl+D duplicates one SpeechBlock through the existing `SpeechBlockService`, Ctrl+A selects all, Alt+Up/Down navigates, and Enter enters text editing. Duplicates preserve text, speaker, language, voice override, pauses and non-generated metadata while deliberately not sharing generated takes.

## Undo/Redo

Timeline commands continue through the existing bounded Timeline command stack. Phase 32 speech text/timing commands already push into the same stack and continue to do so. Native TextField/TextArea Ctrl+Z is protected while text focus is active; committed edits remain coherent project commands where the existing architecture supports it.

## Tooltips and beginner workflow

Important existing buttons now expose shortcut text where Phase 33 touches them, while mouse actions remain unchanged. The Command Palette and shortcut help are optional; users do not need to memorize shortcuts.

## Performance and logging

Dispatch is metadata lookup over a small registry. No expensive repository scan runs per keypress. Search remains responsive when mocked with 1,000 commands. Keypresses are never logged; only custom shortcut changes and command failures/conflict-related actions are candidates for logging.

## Boundaries

Phase 33 does not add a database migration, full cross-project clipboard remapping, complex chord sequences, fake frame-accuracy claims, or a second undo system. Exact frame stepping continues to use the existing timeline project-FPS quantization behavior. Full accessibility work remains Phase 34.

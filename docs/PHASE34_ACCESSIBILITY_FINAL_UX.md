# Phase 34 — Accessibility + Final UX Polish

Phase 34 refines the existing Phase 28 creator UI without redesigning the product. It keeps Phase 17 Timeline, Phase 27 recovery/autosave, Phase 31 performance work, Phase 32 `SpeechBlock` editing, and Phase 33 command routing authoritative. The phase adds accessibility preferences, predictable focus behavior, semantic control metadata, stronger contrast, multilingual typography safeguards, high-DPI setup, and clearer empty/error/progress states.

## Accessibility architecture

Accessibility preferences are stored in the existing application settings document. `AccessibilitySettings` defines validated Reduce Motion, Interface Text Size, and Stronger Focus Indicator values. `AccessibilityService` resolves persisted preferences and performs a best-effort Windows system animation query for Follow System. `FocusNavigationService` contains small deterministic helpers for keyboard row/list movement. No second settings database or UI state store is introduced.

The QML theme receives resolved preferences before the main window is shown. Shared Phase 28 controls then consume semantic focus, typography, contrast, animation, control-height, and tooltip tokens so feature pages do not need independent accessibility themes.

## Accessible names and roles

Shared buttons, icon buttons, switches, text fields, combo boxes, cards, search controls, progress controls, status badges, and dialogs expose `Accessible.name` and an appropriate QML accessibility role where practical. Domain-specific rows add concise descriptions rather than one giant paragraph. Important icon-only actions include a text alternative and tooltip.

Examples include Timeline clip name/track/start/duration, Speech speaker/language/voice/status, Subtitle cue text/timing, Asset type/subtype/duration, Template category/features, Batch item stage/progress/status, and Audio Mixer gain/mute/solo/pan.

## Keyboard navigation and focus

Tab/Shift+Tab continues to follow normal visual control order. Dialogs use the shared `AppDialog`, which captures the previous focus item, puts focus inside the modal, and restores sensible focus on close. Background Phase 33 commands remain suppressed while a modal is active.

Timeline is intentionally one keyboard editing region instead of putting every clip in the Tab chain. Left/Right retain the existing playhead behavior and Phase 33 command routing; Up/Down moves clip selection through a bounded list. Speech/TTS supports row navigation with Up/Down, Enter to begin editing, Escape to leave editing/clear selection, and normal Tab movement among editable fields. Subtitle rows support keyboard selection and retain native text-editing semantics.

Focus is not selection. A selected clip/row keeps its existing selected state; keyboard focus adds a separate soft accent outline. The optional Stronger Focus Indicator increases outline width without adding glow or animation.

## Contrast and status semantics

Light and dark semantic tokens were adjusted to avoid unreadably pale secondary text. Focus, selected states, badges, inputs, Timeline text, and dialog text retain the low-saturation Phase 28 identity. Static contrast tests target approximately 4.5:1 for normal semantic text where practical; this is an engineering target, not a formal WCAG certification.

Status meaning never depends only on color. Shared status badges combine symbol + label + color (for example Ready, Needs Review, Failed, Outdated). Feature-specific statuses in News, Dub, Batch, Speech, Assets, and other audited surfaces expose readable text.

## Reduced motion

Settings → Accessibility provides Follow System, On, and Off. When reduced motion is effective, shared animation durations collapse for non-essential UI motion such as fades and hover transitions. Essential media playback and job progress remain functional. Follow System uses the Windows client-area-animation preference when available and safely falls back to normal motion when it cannot be read.

No continuous decorative animation or rapidly flashing content is added.

## Interface text size and DPI

Interface Text Size provides Default and Large. Large is deliberately bounded to a 1.12 scale so compact desktop layouts remain usable. Shared control heights grow only modestly with the text scale. Qt high-DPI startup preserves fractional scale factors rather than rounding 125%/150% Windows scaling.

The implementation is designed around desktop-class windows with a 1366×768 minimum audit target and normal 1920×1080/2560×1440 use. Static layout checks cover compact navigation and major editor minimums. Live visual validation at 100/125/150/200% still requires a Windows/PySide6 environment.

## Multilingual typography

Shared typography and the Speech/Subtitle surfaces use increased line height where multilingual text is likely. Phase 34 test fixtures include Khmer, Thai, and Vietnamese strings and preserve all Unicode/diacritics. Long names use wrap/elide plus accessible full values or tooltips rather than silently discarding important editable content.

The current architecture does not assume Latin-only widths. Full RTL layout is not claimed in Phase 34.

## Timeline accessibility

The Timeline exposes a readable playhead string in addition to the graphical playhead. Clips expose name, track, start, duration, type/status, and missing-media information. Track identity remains visible through labels rather than color alone. Timeline zoom and editing controls use accessible names/tooltips while Phase 33 remains the authoritative shortcut layer.

## Speech/TTS accessibility

Phase 32 remains canonical. Phase 34 adds row-level semantic descriptions, labeled Start/End time fields, keyboard row navigation, visible focus, larger multilingual row text, actionable empty state, and symbol+text audio/timing status. Speaker and Voice remain separate terms. No second TTS or SpeechBlock model is introduced.

## Subtitle accessibility

Subtitle cues expose text/timing/selection information, use keyboard-selectable rows, and preserve multilingual text. Subtitle preview rendering remains a media-preview concern and is not converted into a general UI theme surface.

## Audio Mixer accessibility

Mixer track, bus, and master controls expose names and numeric gain/pan values. Faders are keyboard adjustable. Mute and Solo controls include descriptive labels, and meters expose numeric peak information in addition to moving visual meters. Phase 30 mixer state and render behavior remain unchanged.

## Forms, empty states, errors, and progress

Project creation adds inline validation for the project name. Important empty states in Speech, Assets, Templates, and Batch explain what the area contains and the next action. Shared error toasts avoid presenting obvious traceback/SQLite/FFmpeg-filter internals as the primary normal-user message; technical logging remains available to the application.

Long-running Export states distinguish preparing, progress, cancelling, failure, and completion. Indeterminate work does not invent a percentage. Cancellation remains “Cancelling…” until the controller actually reports a safe stop. Completion uses a compact “Export complete” state with useful follow-up actions.

## Manual-first behavior

Accessibility polish does not turn unavailable AI into a broken application state. Existing manual editing/import/record/translation paths remain available. Phase 34 does not auto-play template or asset previews on hover and does not add arbitrary UI sounds.

## Performance boundaries

Focus indicators are borders, not heavy shadows. Accessibility metadata is static/lightweight. No additional polling loop, model load, background scanner, or per-frame animation is introduced. Existing virtualized lists remain virtualized. This preserves the Phase 31 performance architecture.

## Validation

Focused Phase 34 model/service/QML contract tests cover preference persistence, reduced motion, focus restoration, focus rings, contrast tokens, high-DPI setup, 1366-class layout contracts, multilingual text, Timeline/Speech/Subtitle keyboard behavior, Audio Mixer keyboard controls, status semantics, error sanitization, empty states, Settings, and Export states.

A selected Phase 28/31/32/33 + Phase 34 regression set currently reports eight legacy static failures; running the same pre-Phase-34 set on the Phase 33 baseline reports the same eight failures. They assert superseded page-local Phase 32 shortcuts/entrypoints or other pre-existing static assumptions. Phase 34 therefore introduces no additional failure in that comparison.

Live PySide6 rendering, Windows Narrator, full modal Tab traversal, and real 100/125/150/200% Windows DPI inspection are not available in this execution environment and are not claimed as passed.

## Known accessibility limitations

- No formal WCAG certification is claimed.
- Complete Windows Narrator compatibility has not been verified.
- Full RTL layout is not implemented.
- Advanced crop/drag operations are not all keyboard-only; the essential workflow receives keyboard alternatives where practical.
- Live 4K/200% DPI and multilingual glyph-clipping validation still needs a real Windows/PySide6 session.
- Some legacy static tests describe pre-Phase-33 shortcut placement and need separate maintenance; Phase 34 does not restore duplicate local shortcuts merely to satisfy those assertions.

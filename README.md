
## Phase 30 — Professional Audio Mixer

Phase 30 adds a persistent multi-track video-production mixer without creating a second timeline or renderer. Existing Timeline/Scene/SpeechBlock/GeneratedAudio/MediaAsset/Dub records remain canonical; mixer metadata adds track/bus routing, dB gain, pan, mute/multi-solo, fades, simple crossfades, ordered basic effects, timing-based ducking, master limiting, loudness guidance, lazy waveform cache, and rendered mix preview.

The existing `FFmpegRenderer` accepts an optional `AudioMixSpec`; projects with Phase 30 audio render one temporary 48 kHz stereo mix through `AudioRenderService`, while legacy projects keep the previous source/override path. Phase 21 Dub settings migrate lazily, Phase 22 speakers keep their IDs/languages, Phase 25 Music/SFX assets route by subtype, Phase 24 templates store semantic mixer roles, Phase 26 Batch inherits those template settings, Phase 27 remains responsible for project recovery, and Phase 29 owns waveform/mix-preview cache cleanup.

See `docs/PHASE30_PROFESSIONAL_AUDIO_MIXER.md` for signal flow, routing, effects, ducking, waveform/cache behavior, migration, Template/Batch integration, renderer details, safety boundaries, and performance notes.

## Phase 31 — Performance Optimization

Phase 31 keeps the existing creator architecture and final renderer intact while optimizing measured editor hot paths. Asset metadata is bulk-fetched instead of using per-card N+1 queries, subtitle playback uses bounded indexed lookup, Batch counters use aggregate SQL, unchanged media metadata reuses a bounded FFprobe cache, and Phase 30 waveform generation deduplicates concurrent requests and supports cached density levels.

The shared WorkerPool is now bounded and priority-aware (Interactive / Normal / Background), stale preview/thumbnail requests carry request versions so late work cannot replace current UI state, and Settings → Performance exposes Auto / Low Memory / Balanced / Maximum Quality plus preview quality and worker limits. Phase 31 does not preload VoxCPM2, Whisper, or translation models and does not change final render resolution/quality.

See `docs/performance.md` for the profiling method, measured before/after numbers, cache/index strategy, worker/model lifecycle, memory-scope results, and target-machine measurements that still require a real Windows/PySide6/CUDA environment.

## Phase 32 — Manual Speech & TTS Editor

Phase 32 adds one reusable, virtualized Manual Speech/TTS workspace across Timeline, News, Story, Translate & Dub, and Shorts. `SpeechBlock` remains canonical; generated takes remain `GeneratedAudio`; the existing Phase 22 TTS/AI resource lifecycle, Phase 17 Timeline, Phase 27 autosave/recovery state, and Phase 30 Audio Mixer remain authoritative.

Manual text/timing/speaker/voice/language edits invalidate only affected rows and preserve prior takes. Users can generate selected/outdated/all rows, reactivate older takes, perform Unicode find/replace, split/merge speech, synchronize explicitly with subtitles, and create speech from transcript/translation segments. The editor uses recycled ListView delegates so large 1,000-row projects do not instantiate 1,000 text editors.

See `docs/PHASE32_MANUAL_SPEECH_TTS_EDITOR.md` for schema compatibility, timing/take behavior, workflow reuse, subtitle safety, autosave integration, and performance notes.

## Phase 33 — Keyboard Shortcuts & Editing Productivity

Phase 33 adds one centralized command/shortcut registry, context-aware dispatch, a searchable Command Palette, customizable persisted shortcuts, conflict detection and text-focus protection. Timeline and Phase 32 Speech/TTS no longer own duplicate page-local shortcut definitions; they receive command IDs and keep their existing controllers/business logic authoritative.

The shortcut router protects native text editing, blocks background shortcuts behind modal dialogs and inactive windows, and keeps mouse workflows unchanged. Timeline playback/editing, Speech/TTS navigation/generation, source-range commands, media/audio command definitions and project Undo/Redo are exposed through the shared command layer.

See `docs/PHASE33_KEYBOARD_SHORTCUTS_PRODUCTIVITY.md` for command architecture, contexts, default shortcuts, focus rules, customization/conflicts, Timeline/Speech integration, Undo/Redo behavior and tests.

## Phase 34 — Accessibility + Final UX Polish

Phase 34 refines the existing Phase 28 desktop UI instead of redesigning it. Shared controls now expose accessible names/roles, predictable soft focus indicators, delayed tooltips, stronger light/dark contrast, semantic status labels, bounded interface text scaling, reduced-motion preferences, and high-DPI-friendly startup behavior. Modal focus restoration and keyboard navigation build on the centralized Phase 33 command layer without duplicating shortcuts.

Timeline, Speech/TTS, Subtitle, Audio Mixer, Assets, Templates, Batch, News, Story, Dub, Shorts, Export, Recovery, Storage and Settings receive targeted accessibility semantics and clearer empty/error/progress states. Khmer, Thai and Vietnamese typography is explicitly covered by Phase 34 contract tests. No formal WCAG or complete screen-reader certification is claimed without a real Windows accessibility audit.

See `docs/PHASE34_ACCESSIBILITY_FINAL_UX.md` for architecture, focus/navigation rules, contrast/status semantics, reduced motion, text/DPI behavior, multilingual typography, feature-specific accessibility and known limitations.

## Phase 35 — Onboarding + First-Run Experience

Phase 35 adds a short, optional first-run experience without changing the existing editor or requiring AI. Explicit onboarding state/version is persisted separately from normal preferences, while language, theme, accessibility, project-folder and performance choices continue through the existing Settings, Language Registry, System Readiness, Model Manager and Phase 31 performance services. Existing configured installations migrate to completed onboarding instead of being forced through a new-user wizard.

The setup flow covers content language, appearance, projects folder, system readiness, optional AI features, and a quick first-project path. Model installation is never automatic: onboarding hands explicit install/manage actions to the existing Model Manager, and Continue Without AI always remains available. Getting Started and a compact Quick Guide can be reopened later without resetting projects, assets or models.

See `docs/PHASE35_ONBOARDING_FIRST_RUN.md` for first-run detection, onboarding versioning, readiness/model behavior, safe rerun rules, first-project integration, contextual tips and known limitations.

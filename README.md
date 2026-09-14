
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

## Phase 36 — Diagnostics + Support Tools

Phase 36 adds one local diagnostics/support layer over the existing System Readiness, Phase 29 storage, Model Manager, project integrity, render, recovery, template and batch architecture. Quick Check is deliberately lightweight and never loads AI models. Full Diagnostics runs through the shared worker pool and may perform model-file verification, SQLite integrity checks and tiny FFmpeg capability/smoke probes. CPU-only and fully offline editing remain supported.

Support bundles are local-only, fixed allow-list ZIPs. They contain sanitized system/settings summaries, diagnostic results, bounded redacted logs, model status and database schema metadata; they exclude project databases, scripts, transcripts, subtitles, News sources, voices/reference recordings, recovery snapshots and all media. Secret fields and personal home-path prefixes are redacted before display, copy or packaging, and no telemetry/upload/remote-control behavior is introduced.

See `docs/PHASE36_DIAGNOSTICS_SUPPORT_TOOLS.md` for check orchestration, FFmpeg/database/model/project diagnostics, render categorization, log redaction, support-bundle privacy boundaries, safe repair actions and test coverage.

## Phase 37 — Security + Privacy Review

Phase 37 is a release-hardening pass, not a product-feature expansion. It centralizes managed-root path safety for destructive/app-owned operations, strengthens `.mmovtemplate` ZIP validation with streaming limits and compression-ratio checks, rejects executable/symlink/unsigned package payloads, hardens managed model downloads and News-source network boundaries, and tightens export filename/path handling. Existing FFmpeg rendering keeps argv-based `shell=False` execution and ASS/file-based Unicode text handling.

Settings → Privacy now explains current Local versus Online actions without making a misleading "100% private" claim. Diagnostics/support bundles remain local and allow-list only; reference voice recordings are treated as sensitive media and are excluded from support/template packages. No cloud AI provider is added by this phase, and any future online provider must present a clear first-use data-transmission notice.

See `docs/security-threat-model.md` and `docs/security-review-phase37.md` for the threat model, reviewed surfaces, fixes, dependency/license notes, accepted limitations, vulnerability-scan status and security test coverage.

## Phase 38 — Database + Project Migrations

Phase 38 adds safe forward-only upgrades for the existing application database, project metadata/data, settings and Recovery snapshots. The application DB now has explicit version/application bookkeeping and backup-first startup migration; projects carry their own schema version and migrate before open/duplicate with protected SQLite + metadata backups, crash markers, foreign-key/integrity validation and newer-version rejection. Unknown project/settings fields and unknown language values are preserved rather than guessed or silently discarded.

Legacy Script content can seed the existing SpeechBlock model, old Dub/source/narration volume settings map to the existing Phase 30 Audio Mixer, active Batch work is safely interrupted across upgrades, Recovery payloads migrate in memory, and template upgrades continue to use the Phase 24 template migrator. Migration failure keeps the original project unchanged and exposes Diagnostics/backup actions; a project created by a newer version is never modified.

See `docs/PHASE38_DATABASE_PROJECT_MIGRATIONS.md` for schema/version contracts, backup/rollback rules, legacy mapping behavior, validation, user-facing failure handling and future migration-author rules.

## Phase 39 — Full Test Suite + End-to-End QA

Phase 39 adds a release-grade QA architecture over the completed product without introducing a new runtime layer. Tests are organized into FAST, INTEGRATION, E2E, REAL_ENGINE_OPTIONAL and PACKAGING_SMOKE profiles. Deterministic fake TTS, STT, translation and Director providers plus tiny generated FFmpeg media allow complete creator workflows to run without downloading large AI models. Every Phase 39 workflow uses temporary databases/project roots and generated fixtures rather than user LocalAppData or committed media.

The mandatory E2E suite covers Normal Video, Reporter News, Interview, Story, Translate & Dub, Shorts, Templates, Asset Library, Batch Factory, Recovery and legacy Migration-to-render. Release regression also covers English/Khmer/Thai/Vietnamese content, Phase 31 scale/resource sanity, Phase 34 accessibility contracts, Phase 37 security, Phase 38 migrations, failure injection, libx264 rendering and privacy-safe machine/human test summaries. Optional real-engine tests remain capability-driven and skipped when models are not installed.

See `docs/PHASE39_RELEASE_QA.md`, `docs/manual-qa-checklist.md` and `docs/known-issues.md` for profile commands, E2E coverage, Windows/manual acceptance, release gates and tracked limitations.

## Phase 40 — Windows Packaging

Phase 40 adds a reproducible Windows 11 x64 standalone build around the existing application instead of changing creator workflows. The selected release architecture is CPython 3.11 + PySide6 + Nuitka in a one-folder layout. QML and static resources are included explicitly, the executable carries Windows product/version metadata and a multi-size icon, and packaged runtime data stays under `%LOCALAPPDATA%\MMOVideoStudio` rather than Program Files.

Release builds use a staged, reviewed FFmpeg/FFprobe pair copied into the controlled `bin/` directory; the app never downloads FFmpeg silently at runtime. Model weights remain external and Model Manager continues to own `%LOCALAPPDATA%\MMOVideoStudio\models`. CPU-capable AI runtimes can be bundled separately from model weights, with CPU PyTorch as the default packaging baseline and no NVIDIA driver stack embedded. The build emits `build-manifest.json`, scans for development/secret files, supports optional certificate-based signing, and includes a Windows clean-profile/no-Python verification flow.

See `docs/PHASE40_WINDOWS_PACKAGING.md` and `packaging/windows/README.md` for the exact Python/Nuitka/PySide6 pins, FFmpeg staging rules, resource/plugin policy, build commands, fresh-profile checks, signing preparation and the Windows-only acceptance gates that must be executed before a public release artifact is considered verified.


## Phase 41 — Windows Installer

Phase 41 adds a safe per-user Windows 11 x64 installer/uninstaller around the verified Phase 40 one-folder application. The selected installer is Inno Setup 7.1.0 x64 with a stable AppId, non-elevated install under `%LOCALAPPDATA%\Programs\MMO Video Studio`, Start Menu shortcut, optional unchecked Desktop shortcut, running-app protection, numeric downgrade blocking, standard install logs, optional external code signing, and SHA-256 sidecars.

Application binaries remain separate from `%LOCALAPPDATA%\MMOVideoStudio`, so normal upgrades and uninstall preserve settings, models, Asset Library data, templates, cache, recovery, logs and managed exports. Interactive uninstall offers an explicit **No-by-default** managed-data removal confirmation; projects or exports outside the managed LocalAppData root are never part of that deletion. No project file association or URL protocol handler is added.

See `docs/PHASE41_WINDOWS_INSTALLER.md`, `packaging/windows/installer/README.md`, `scripts/build_windows_installer.ps1`, and `scripts/verify_windows_installer.ps1` for installer architecture, build/sign/hash commands and the mandatory Windows fresh-install/upgrade/uninstall acceptance matrix.


## Phase 42 — Update Architecture

Phase 42 adds a secure, user-controlled Stable update path over the existing Phase 40 package and Phase 41 installer. Production update metadata/installers are HTTPS-only, manifests reject executable command fields, downloads use managed LocalAppData staging with progress/cancel/retry, installer size and SHA-256 are mandatory, and optional Windows Authenticode verification is enforced when an expected publisher identity is configured. The Setup EXE is revalidated before a one-argument `shell=False` launch; the running application is never overwritten directly.

Settings → Updates now exposes the current version, manual checks and a persisted lightweight automatic-check preference. Update checks never auto-download installers. Install is blocked while shared background/render/model work, Batch, or migration activity is present, and Phase 27 autosave/recovery must flush before handoff. Phase 29 Update Temp cleanup, Phase 36 diagnostics and Phase 38 post-update migration startup are integrated through their existing shared services rather than duplicated.

See `docs/PHASE42_UPDATE_ARCHITECTURE.md` for manifest/trust rules, privacy, staging, validation/signing limitations, active-work protection, recovery, post-update behavior and release acceptance requirements.

## Phase 43 — Final Production Audit

Phase 43 freezes feature scope and audits release readiness across workflows, security/privacy, storage/recovery, migrations, packaging, installer, updates, accessibility, multilingual behavior, performance and release-artifact hygiene. It adds no new application runtime layer. Automated source/configuration gates remain green, but the audit deliberately separates those results from native Windows/manual acceptance.

**Current release recommendation: NOT READY — BLOCKERS REMAIN.** There are no known open P0 issues in the audited source/configuration gates, but Phase 44 is blocked until the real Windows 11 x64 clean-machine release/installer/update matrix is completed and owner-approved public application/distribution terms are supplied. See `docs/production-audit-phase43.md`, `docs/known-issues.md`, and the expanded `docs/manual-qa-checklist.md`.

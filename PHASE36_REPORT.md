PHASE 36 STATUS

Completed:
- Phase 36 Diagnostics + Support Tools implemented only; Phase 37 was not started.
- Added a local Diagnostics workspace with Quick Check, Full Diagnostics, cancellation, Current Project diagnosis, bounded Logs, Copy Report, Support Bundle review/creation, and safe repair/navigation actions.
- Preserved manual/offline workflows; no telemetry, remote control, automatic upload, automatic model installation, or automatic AI inference was added.
- Added direct "Diagnose Render" affordance to the existing Render dialog without changing render execution or creating a second renderer.

Diagnostics architecture:
- Added `DiagnosticResult`/status model, lightweight `DiagnosticCheck` descriptor, and `SupportBundle` domain model.
- `DiagnosticsService` orchestrates existing System Readiness, Phase 29 Disk Monitor, SQLite database, Model Manager/verifier, Project/ProjectIntegrity, Asset Library, Templates, Batch, Recovery, FFmpeg and render-failure information.
- `EnvironmentReportService` emits strict allow-listed environment/settings/model/database summaries.
- `LogRedactionService` centralizes text/dictionary/URL/path sanitization.
- `SupportBundleService` creates fixed-file allow-list ZIPs only.
- `DiagnosticsPreferencesService` persists bounded log severity/limit preferences in `phase36_diagnostics.json`.
- Phase 36 runtime layers on Phase 35 and registers one `SPVideoStudio.Diagnostics` singleton; no duplicate bootstrap, renderer, model manager or project system was created.

Quick Check:
- Checks app version, OS/platform, CPU/RAM/GPU/CUDA state through existing readiness, app/project/cache writability and disk state, FFmpeg/FFprobe, SQLite basic query/schema/pending migrations, model registry/install state, and separate TTS/STT/Translation configuration state.
- Does not load VoxCPM2, faster-whisper or translation models.
- No model install/download method is called by diagnostics.

Full Diagnostics:
- Runs through the existing shared `WorkerPool` and supports cancellation between checks/model verifications.
- Adds FFmpeg capability/smoke probes, SQLite integrity/foreign-key/transaction checks, installed-model manifest/file/checksum verification, model compatibility reporting, managed storage roots, Asset/Template/Batch/Recovery checks, Rendering/Media state and optional selected-project diagnosis.
- Does not automatically run AI inference smoke tests and does not use private project content for AI diagnostics.

FFmpeg diagnostics:
- Detects FFmpeg/FFprobe version/path, scale/crop/overlay/chromakey/colorkey, volume/afade/amix, subtitles/libass, h264/aac decoder basics, and libx264/NVENC/QSV/AMF encoder listings.
- Uses tiny generated black-frame probes; hardware encoders are never treated as usable from listing alone.
- Real sandbox Full FFmpeg probe: Ready in 2.83 s; required filters/decoders passed; libx264 listed + smoke passed; h264_nvenc and h264_qsv listed but smoke failed/unavailable on this CPU environment; h264_amf not listed.
- Raw bounded FFmpeg listings remain under Technical Details.

Database diagnostics:
- Reuses the central `SQLiteDatabase` (resolved directly or through the authoritative ProjectRepository database).
- Quick Check runs `SELECT 1`, schema version and pending migration count.
- Full check runs `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, and a TEMP-table transaction probe that is rolled back.
- No database reset, replacement or project DB bundling is performed.

Model diagnostics:
- Reports registry entry, expected install path/existence, installed state, version, existing verifier manifest/required-file/checksum result, disk size, compatibility assessment, verified state and `Load Tested: no` separately.
- Missing models are optional/not configured; corrupt models route to the existing Model Manager Repair workflow.
- Large models are not loaded just to prove installation.

GPU/CPU diagnostics:
- Reports CPU/RAM, detected GPU/VRAM/readiness data, CUDA state and engine-managed/automatic device mode.
- Missing GPU, CUDA or `nvidia-smi` is not fatal; CPU workflows remain supported.

Project diagnostics:
- Checks selected project library-record/folder consistency, `project.json` identity/version, project-scoped DB file-path references for missing files, and existing ProjectIntegrity/foreign-key state.
- Missing project media is reported without opening, replacing or deleting it.
- Asset Library full diagnostics checks missing global asset files independently when the Phase 25 service is available.

Render diagnostics:
- Categorizes Missing Media, Unsupported Filter, Encoder Failure, Disk Full, Invalid Audio Graph, Subtitle/Font Problem and Unknown FFmpeg Failure.
- The existing Render dialog now offers `Diagnose Render` after a failed render.
- Technical failure text is redacted and kept inside collapsed Technical Details.
- Local `RND-YYYYMMDD-XXXX` references are written to local logs with redacted context; they do not imply remote tracking.

Storage diagnostics:
- Reuses Phase 29 disk thresholds when `DiskMonitorService` is available.
- Checks project/cache/model/Asset/Recovery/Exports/Temporary roots, real writability via a short app-owned probe file, free-space state and missing app-owned roots.
- Safe self-repair can recreate only missing app-owned directories.

Support bundle:
- Creates local `MMOVideoStudio-support-YYYYMMDD-HHMMSS.zip` files under app-owned support storage by default.
- Fixed files: `manifest.json`, `environment.json`, `settings-summary.json`, `diagnostics.json`, `ffmpeg-summary.json`, `model-status.json`, `database-summary.json`, `logs/recent.log`.
- Includes app/system info, allow-listed sanitized settings, diagnostic results, collected FFmpeg details, bounded recent redacted logs, model state, DB schema summary and error summaries.
- Explicitly excludes project/project DB content, media, scripts, transcripts, subtitles, News sources, voices/reference recordings, recovery snapshots, arbitrary provider headers and raw settings.
- Nothing is uploaded automatically; file list is shown after creation.

Redaction:
- Covers Authorization/Bearer, X-API/API keys, generic provider `key`, access/secret/private keys, password/passwd, cookies, session/access/refresh/auth tokens, client secrets, nested sensitive dictionary keys and secret-bearing URL query values.
- Replaces practical Windows user-profile / Unix home prefixes with `%USERPROFILE%` / `$HOME`.
- GitHub code search for current default-branch `Authorization` and `api_key` logging patterns returned no source matches, so there was no identified source logger secret emission to patch in this phase; UI/bundle redaction remains defense in depth.

Log viewer:
- Adds Diagnostics > Logs with persisted severity filter, refresh, bounded recent tail, sanitized display/copy and Open Logs Folder.
- Never renders millions of lines; per-file reading is capped to a recent 1 MiB tail and UI results are capped to the configured 50–2000 range (default 400).

Repair actions:
- Routes Open Models/Repair Model, Storage, FFmpeg Settings, Projects/Locate Media, Recheck and Logs to existing systems.
- Safe app-folder repair only calls the existing app-path ensure behavior.
- No destructive model/media/database/recovery action is performed automatically.

New files:
- `PHASE36_REPORT.md`
- `PHASE36_MANIFEST.json`
- `app/phase36_runtime.py`
- `docs/PHASE36_DIAGNOSTICS_SUPPORT_TOOLS.md`
- `domain/diagnostic_check.py`
- `domain/diagnostic_result.py`
- `domain/support_bundle.py`
- `services/diagnostics_preferences_service.py`
- `services/diagnostics_service.py`
- `services/environment_report_service.py`
- `services/log_redaction_service.py`
- `services/support_bundle_service.py`
- `tests/test_phase36_diagnostics.py`
- `ui/controllers/diagnostics_controller.py`
- `ui/qml/diagnostics/DiagnosticCheckCard.qml`
- `ui/qml/diagnostics/DiagnosticDetails.qml`
- `ui/qml/diagnostics/DiagnosticsPage.qml`
- `ui/qml/diagnostics/LogViewer.qml`
- `ui/qml/diagnostics/SupportBundleDialog.qml`

Modified files:
- `README.md`
- `main.py`
- `pyproject.toml`
- `ui/qml/Main.qml`
- `ui/qml/render/RenderDialog.qml`

Tests run:
- Pre-change Phase 35 focused baseline: 28/28 passed.
- Phase 36 focused suite: 43/43 passed.
- Combined Phase 35 + Phase 36 focused regression: 71/71 passed.
- Changed Python `compileall`: passed.
- QML structural delimiter check: 7/7 passed.
- `ruff` and `qmllint` are not installed in this sandbox.

Secret-redaction test:
- PASSED.
- Mandatory fake values `SECRET123`, `TOPSECRET`, and `hello` were injected through Authorization/Bearer, API-key, password, query-token, result metadata and log paths.
- None survived in generated support-bundle reports, included logs, filenames or bundle metadata.

Support-bundle privacy test:
- PASSED.
- Test project contained Khmer, Thai and Vietnamese text, reference-voice metadata, News-source metadata, media bytes and a project database.
- None of those project/private payloads or media/database files were present in the default support bundle.
- ZIP member names are fixed, traversal-safe and CRC-valid.

FFmpeg smoke test:
- PASSED.
- Real installed FFmpeg: `7.1.5-0+deb13u1`.
- Generated-source smoke passed.
- Full capability probe reported Ready; libx264 smoke passed while listed NVENC/QSV correctly failed hardware smoke in this environment and were not claimed usable.

Database health test:
- PASSED.
- Basic connection/query, schema/pending migration behavior, integrity check, foreign-key check and rolled-back TEMP read/write transaction were covered.
- Broken-database behavior returns a friendly failed diagnostic instead of crashing.

Project diagnostic test:
- PASSED.
- Missing Unicode media paths and invalid project relational references are detected while leaving project content untouched.

Unicode test:
- PASSED.
- Khmer/Thai/Vietnamese project paths and Unicode app/log roots remained readable and bundle-safe.

Known issues:
- The sandbox no longer has a full `.git` checkout, so a literal local `git status` and the entire historical repository test suite could not be rerun. GitHub `main` was verified at Phase 35 commit `a00c3e46e27a103786da4a6baaaab91c7496a815`, and the still-runnable Phase 35 focused baseline passed before Phase 36 changes.
- PySide6 is not installed here, so a live Windows/PySide/QML launch and screen-reader/high-DPI interaction test cannot be claimed. QML structural checks passed, but `qmllint` is unavailable.
- Optional direct TTS/STT/Translation inference smoke buttons were not added; Phase 36 deliberately keeps AI inference out of automatic diagnostics. Model installation/verification/compatibility are diagnosable and normal feature UIs remain the explicit way to exercise inference.
- No provider-specific remote diagnostic adapter exists in the current architecture; Network Providers is clearly reported as not configured/offline and sends no project content.
- Project semantic diagnosis relies on existing database foreign-key constraints, project/path references and feature services; opaque metadata JSON that has no schema/foreign-key/path field is not destructively interpreted or rewritten.
- Cancellation is checked between checks/model verifications; an individual existing checksum verification or bounded subprocess cannot be interrupted mid-call.

Architecture decisions:
- Reuse System Readiness, Disk Monitor, Model Manager/ModelVerification, SQLiteDatabase, ProjectIntegrity, Asset/Template/Batch/Recovery and WorkerPool rather than introducing second systems.
- Keep all subprocess/filesystem/database work out of QML and Full Diagnostics off the UI thread.
- Use a separate tiny diagnostics-preferences file instead of widening normal app settings with support-tool UI state.
- Build bundles from a generated fixed allow-list rather than filtering an arbitrary folder after the fact.
- Treat redaction as defense in depth: source logging should avoid secrets, and display/copy/bundle paths sanitize again.
- Preserve CPU-only/offline operation as a supported state, not an error.

Recommended next phase:
Phase 37 — Security + Privacy Review

Suggested Git commit:
feat: add diagnostics and privacy-safe support tools

Do not automatically begin Phase 37.

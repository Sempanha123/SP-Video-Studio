# Phase 36 — Diagnostics + Support Tools

Phase 36 adds a local, privacy-first diagnostics layer without replacing the existing readiness, storage, model, project, rendering, recovery, template or batch systems.

## Architecture

`DiagnosticsService` is the orchestrator. It consumes existing Phase 3 System Readiness, Phase 29 `DiskMonitorService`, the Phase 7 Model Manager/verifier, the central `SQLiteDatabase`, `ProjectService`/`ProjectIntegrityService`, and optional Asset/Template/Batch/Recovery services. Checks return `DiagnosticResult`; UI only renders results and dispatches explicit actions.

`EnvironmentReportService` creates a deliberately allow-listed machine/app/settings/model summary. It never serializes raw settings. `LogRedactionService` sanitizes credential patterns, secret query parameters and home-directory prefixes. `SupportBundleService` creates a fixed-filename ZIP from allow-listed generated documents only. `DiagnosticsPreferencesService` persists bounded log-viewer preferences separately in `settings/phase36_diagnostics.json`.

Phase 36 runtime layers on Phase 35 by wrapping the same Phase 31 install hook. It registers a single `SPVideoStudio.Diagnostics 1.0` QML controller; no second startup/bootstrap path is created.

## Quick Check

Quick Check reports application/platform state, writable storage/project/cache roots, free disk state, FFmpeg/FFprobe discovery, a basic SQLite query/schema/pending-migration status, model-registry installation state and selected local AI-family configuration. It does **not** load VoxCPM2, faster-whisper or translation engines.

## Full Diagnostics

Full Diagnostics runs through the existing bounded `WorkerPool`. It extends Quick Check with FFmpeg filter/encoder/decoder inspection and tiny generated-source/encoder probes, SQLite `integrity_check`/foreign-key checking plus a rolled-back TEMP-table transaction probe, installed-model manifest/file/checksum verification, managed storage roots, Assets/Templates/Batch/Recovery checks, and optional current-project diagnosis. Cancellation is checked between diagnostic units and between model verifications; an individual subprocess/hash operation is bounded or delegated to the existing verifier.

AI inference smoke tests are intentionally not automatic. Phase 36 does not use private project text/audio for diagnostics.

## FFmpeg

The full FFmpeg check looks for scale/crop/overlay/chromakey/colorkey, volume/afade/amix, subtitle/libass filters, common decoders and libx264/NVENC/QSV/AMF encoders. Hardware encoders are not reported as usable merely because `-encoders` lists them: a tiny generated black-frame encode is attempted. Raw listing output stays under Technical Details.

## Database

Quick Check uses the existing `SQLiteDatabase` connection and schema version. Full Diagnostics runs SQLite integrity/foreign-key checks and a safe TEMP-table read/write transaction that is rolled back. It does not reset, migrate destructively, copy or bundle the project database.

## Models and engines

Managed models are reported separately as registered/installed/verified/load-tested. Full Diagnostics calls the existing `ModelVerificationService` only for present model directories, including configured manifest size/hash checks. It never loads a large model merely to prove the directory exists. Repair actions route the user back to the existing Model Manager.

## Project and render diagnostics

Current-project diagnosis compares the library record, folder and `project.json`, then safely introspects project-scoped DB path columns to report missing referenced files without modifying them. Existing project-integrity checks provide the relational reference signal when available.

Render stderr can be categorized into Missing Media, Unsupported Filter, Encoder Failure, Disk Full, Invalid Audio Graph, Subtitle/Font Problem or Unknown FFmpeg Failure. Technical stderr is redacted and remains collapsed. Generated `RND-YYYYMMDD-XXXX` references are local convenience IDs only; they do not imply remote tracking.

## Support bundle privacy boundary

Default bundle name: `MMOVideoStudio-support-YYYYMMDD-HHMMSS.zip`.

Allowed generated files are fixed to:

- `manifest.json`
- `environment.json`
- `settings-summary.json`
- `diagnostics.json`
- `model-status.json`
- `database-summary.json`
- `logs/recent.log`

Default bundles do **not** include projects/project DBs, scripts, transcripts, subtitles, News sources, private source URLs, voice/reference recordings, images/video/audio, recovery snapshots, arbitrary settings files, cookies/provider headers, tokens/passwords/API keys, or arbitrary user filenames. The bundle is local only and is never uploaded automatically.

## Redaction and path privacy

Redaction covers Authorization/Bearer headers, API keys, passwords, cookies, session/access/refresh/auth tokens, client secrets and secret-bearing URL query values. Nested dictionaries are sanitized by sensitive key as well as text patterns. Windows user-profile and Unix home prefixes are replaced with `%USERPROFILE%` / `$HOME` where practical. Code search during Phase 36 did not find a current default-branch logger call explicitly emitting Authorization/Bearer/API-key/password/cookie/session fields; source logging remains expected to avoid secrets, with bundle/UI redaction as defense in depth.

## Logs and repairs

The Diagnostics > Logs view reads at most a bounded tail from a few recent log files, filters by severity, sanitizes before display/copy and can open the log folder. Diagnostics never renders the entire log history.

Safe repair is limited to recreating missing app-owned directories and routing users to existing Models/Storage/Projects/Settings actions. Phase 36 does not overwrite media, reset databases, delete recovery data or reinstall the application.

## Offline behavior

All core checks work offline. The Network Providers category is explicitly reported as not configured/skipped unless a provider-specific adapter exists; no project content is transmitted.

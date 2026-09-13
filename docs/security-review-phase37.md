# Phase 37 — Security + Privacy Review

Baseline: GitHub `main` commit `538f06fff1ae67fa78a0423ab6a2c6f2e137c4bb` (`feat: add diagnostics and privacy-safe support tools`). The sandbox did not contain a `.git` working tree, so a literal local `git status` could not be executed. GitHub `main` was used as the authoritative Phase 36 source baseline. The pre-change Phase 36 focused suite passed 43/43.

## Reviewed areas

- App-owned project/cache/template/model/asset/recovery/output filesystem operations and deletion/copy/move patterns.
- Phase 24 `.mmovtemplate` packaging/import.
- FFmpeg/FFprobe process execution, filter-path escaping and ASS user text handling.
- Phase 18 News source URL policy, redirects, DNS, time/size limits and response parsing.
- Managed Hugging Face model catalog/download/staging/manifest verification.
- Output filename/path construction.
- Phase 36 log redaction and support-bundle allow-list/privacy gate.
- Reference voice/template/support privacy boundaries.
- Batch CSV/JSON/JSONL input validation.
- Central SQLite/repository parameterization patterns and application-defined migrations.
- Current engine/provider architecture and Settings privacy disclosure.
- Current `pyproject.toml` dependencies/version ranges and available environment metadata.
- Future updater/custom-provider security requirements, without adding those product features.

## Fixed issues

1. **Shared managed-path contract.** Added canonical managed-root helpers for traversal/absolute/UNC/ADS/reserved-device checks and destructive symlink/reparse rejection.
2. **Template ZIP bomb defense.** Added suspicious compression-ratio, encrypted/special-file, streaming per-file byte and aggregate extraction defenses on top of existing member/file-size/count limits.
3. **Template active-content rejection.** Expanded unsafe package extensions to script/executable/HTML/SVG/active document forms and reject sensitive reference-voice assets from export.
4. **Template integrity coverage.** Semantic template/assets/docs payloads require checksums. New preview exports are checksummed while older inert preview compatibility is preserved.
5. **Managed template cleanup.** Staging/backup deletion goes through managed-root deletion rather than raw broad removal.
6. **Model source redirects/TLS.** Managed model URLs are HTTPS-only, redirect hosts stay in the trusted Hugging Face/hf.co family, catalog reads are bounded and expected download size cannot be exceeded.
7. **Model staging cleanup.** Partial/backup removal uses managed-root containment.
8. **News defense in depth.** Added bounded concurrency, final-URL revalidation and best-effort connected-peer public-IP validation in addition to existing DNS/per-redirect SSRF checks.
9. **Output filename path rejection.** `../`, separators, UNC/drive paths, ADS-style colons, NULs and Windows device names are rejected rather than silently reduced to a basename. Dots inside names no longer truncate later Unicode content.
10. **Redaction expansion.** Phase 36 text redaction now covers Proxy-Authorization/X-Auth-Token, Set-Cookie, credential and signature-style key/value forms while retaining URL query redaction.
11. **Privacy disclosure.** Settings > Privacy distinguishes Local and Online operations, explains support/diagnostic/reference-voice boundaries and exposes existing cleanup/diagnostic/voice destinations. It does not claim that the application is “100% private.”
12. **Safe security events.** Added a constrained security event sink that redacts metadata and never falls back to raw metadata after a redaction failure.

## Retained controls found already secure

- Phase 24 package import did not use `ZipFile.extractall()` and already rejected traversal, absolute paths, symlinks, executable extensions, oversize members/count/aggregate size, and checksum mismatch before atomic finalization.
- Project deletion already validates `project.json`, project identity and known root containment, stages the folder by rename, commits the DB delete, and restores on DB-step failure.
- Phase 29 cleanup already refuses symlinks, checks resolved containment, avoids following symlink directories, protects user/external/recovery/active data and deletes only cache/regeneratable categories.
- Asset-library deletion explicitly does not remove externally referenced files by default.
- FFmpeg/FFprobe execution uses argv arrays and `shell=False`; short probes are time bounded, render cancellation is supported, and stderr retention is bounded.
- User text is emitted via escaped ASS instead of direct drawtext interpolation. Filter filenames use a dedicated FFmpeg parser escape helper.
- Batch JSON/CSV imports already enforce file/row/depth bounds and never deserialize Python objects.
- SQLite critical repository queries use DB-API parameters rather than concatenating user values; migrations are application code rather than imported/user SQL.
- Phase 36 support ZIP is fixed allow-list, local-only and excludes project DBs/media/scripts/transcripts/subtitles/News sources/reference voices/recovery/credentials.

## Secret storage

No active cloud/custom provider credential field was found in current `AppSettings` or the current deterministic/local LLM architecture. Phase 37 therefore does **not** add a plaintext secret store and does not pretend secrets are encrypted. Before any future provider persists an API key/token, implementation must choose an OS-backed credential mechanism where practical (for Windows, Credential Manager or an acceptable keychain abstraction), or a clearly separate local secret store with permissions and an explicit “not encrypted” limitation. Provider secrets must never be stored in project files.

## Cloud/provider privacy

Current local engines are shown as Local. News source fetching and model downloads are shown as Online because they make explicit outbound requests. Cloud AI Providers are shown as Online / Not configured. The policy model marks cloud LLM, cloud translation, cloud TTS and custom-online providers as requiring a first-use transmission notice. No cloud feature was added by Phase 37.

## Database security

The central SQLite manager uses fixed application SQL and repository methods bind user identifiers/values using `?` parameters. Phase 37 attack-string tests bind an SQL-injection-shaped value and verify it remains data and does not alter schema/rows. The security pass did not add raw SQL from projects/templates/imports or execute user-supplied migrations.

## Dependency review

Current `pyproject.toml` strategy is bounded ranges rather than unpinned latest versions:

| Dependency group | Packages | Purpose / review note |
| --- | --- | --- |
| runtime | `PySide6>=6.10.2,<7` | Qt desktop/QML runtime; major version constrained. Release licensing/Qt redistribution terms require normal product review. |
| runtime | `psutil>=7.2,<8` | system readiness/process/memory information; major version constrained. Sandbox metadata reports BSD-3-Clause. |
| runtime | `Pillow>=12,<13` | image/media utility dependency; major version constrained. Verify installed package license metadata in the release environment. |
| dev | pytest / pytest-cov / ruff | test/lint tooling only; not required at runtime. Sandbox `pytest-cov` metadata reports MIT. |
| AI | faster-whisper / ctranslate2 | optional local speech-to-text/runtime; not installed in this sandbox. Verify release metadata/license before distribution. |
| TTS | voxcpm / soundfile | optional local voice generation/audio IO; `soundfile` sandbox metadata reports BSD 3-Clause. VoxCPM package/model license must be reviewed separately. |
| translation | transformers / torch / sentencepiece | optional local translation/model runtime; sandbox `torch` metadata reports BSD-3-Clause. Model licenses can differ from library licenses and must be reviewed per registered model. |

No dependency is blindly upgraded in Phase 37. No security scanner is added as a runtime dependency. Model registry `license` metadata remains the source for model-specific review; “unknown”/unreviewed licenses should block a release claim until manually reviewed. This report records engineering follow-up only and makes no legal conclusion.

`python -m pip check` in this shared sandbox reported an **environment-level** conflict: installed `moviepy 2.2.1` requests `pillow<12` while the sandbox has Pillow 12.3.0. `moviepy` is not listed in this project’s current `pyproject.toml`, so this is not treated as proof of a project dependency conflict; release CI should check a clean project environment/lock.

## Vulnerability scan

`pip-audit` is not installed in this execution environment (`No module named pip_audit`), so no vulnerability-scan result is claimed. Phase 37 does not install a scanner into runtime dependencies. Recommended release follow-up: run `pip-audit` (or organization-approved equivalent) against the clean locked release environment, review each finding before changing versions, and re-run the regression suite after any upgrade.

## Remaining risks / accepted limitations

- No complete local Git checkout is available in this sandbox, so the entire historical repository test suite and local `git status` cannot be executed here. Focused Phase 35/36/37 regression sources available in `/mnt/data` are run instead.
- PySide6/qmllint is unavailable in the sandbox; QML is structurally/static checked, not live-rendered here.
- Windows junction/reparse defense is implemented using `st_file_attributes` where exposed, but final release should repeat attack tests on real Windows/NTFS including junctions, UNC roots and long paths.
- News connected-peer validation depends on urllib implementation details; mandatory DNS and redirect target validation remains the primary SSRF control.
- Separate connect/read timeout values are not exposed by urllib; the configured socket timeout bounds connect and subsequent socket operations. There is no infinite wait.
- No OS-backed credential store exists because no current product path persists provider secrets. This becomes mandatory design work before such a provider feature is introduced.
- No updater exists yet. Future update downloads need authenticated/integrity-checked artifacts, controlled staging, rollback and no template/project-triggered execution.
- Managed model libraries can still contain complex native/model parsers. Model files are never executed by template import, but upstream library/model-format vulnerabilities remain supply-chain risk.

## Dependencies needing follow-up

- Run vulnerability scanning in a clean locked release environment.
- Verify distribution/license metadata for PySide6/Qt and every optional AI/model dependency actually shipped.
- Review every model registry license/source before bundling or redistributing model weights.
- Decide secure credential-storage dependency/strategy before implementing persisted online provider credentials.
- Add release CI Windows junction/UNC/long-path security tests.

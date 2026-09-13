PHASE 37 STATUS

Completed:
- Phase 37 Security + Privacy Review implemented only; Phase 38 was not started.
- Baseline verified against GitHub `main` commit `538f06fff1ae67fa78a0423ab6a2c6f2e137c4bb` (`feat: add diagnostics and privacy-safe support tools`).
- A literal local `git status` could not be run because this sandbox does not contain a `.git` checkout; the clean Phase 36 GitHub commit was used as the source baseline.
- Pre-change Phase 36 focused suite: 43/43 passed.
- Added systematic hardening for managed filesystem paths, hostile ZIP/template packages, model-download redirects/staging, News SSRF defense in depth, output path handling, secret redaction, reference-voice packaging policy, privacy disclosure and safe security events.
- No cloud provider, updater, project-package import, crawler, telemetry, remote support, or other unrelated product feature was added.

Threat model:
- Added `docs/security-threat-model.md` covering projects/media/scripts/transcripts/reference voices/credentials/models/templates/exports.
- Covers template ZIPs, filenames, News URLs, provider endpoints, model downloads, subprocess args, local DB, support bundles and a future updater boundary.
- Covers traversal, arbitrary deletion, command injection, SSRF, secret leakage, malicious ZIPs, symlink/junction escape, unsafe schemes, malicious filenames, model/package tampering and executable template content.
- Documents trust boundaries, current controls and residual risks rather than claiming perfect security.

Filesystem security:
- Added `ManagedRoot`, `canonicalize_path()`, `is_within_managed_root()`, `safe_copy_destination()` and `safe_delete()` in a shared safe-path service.
- Relative managed destinations reject traversal, absolute/drive/UNC injection, NULs, ADS-style colons and Windows reserved device names.
- Destructive operations refuse the managed root itself and reject symlink/reparse/junction entries instead of following them.
- Windows comparisons use normalized case on Windows; long paths are not truncated.
- Existing Phase 29 cleanup and staged project deletion were audited and retained because they already perform containment/protection checks and avoid deleting external references.

Template/package security:
- Reaudited Phase 24 `.mmovtemplate` rather than replacing it.
- Keeps pre-extraction traversal/absolute-path/symlink/executable checks and adds encrypted/special-file/active-document rejection.
- Semantic `template.json`, assets and docs require checksum coverage and verification.
- Sensitive/reference-voice assets are rejected from template export.
- Extraction uses controlled staging, safe destinations, streaming byte limits and atomic finalization; `extractall()` is not used.
- Older inert cosmetic preview images remain import-compatible without mandatory checksum coverage; new exports checksum previews when present.

ZIP bomb protection:
- Member-count limit: 512.
- Per-member uncompressed limit: 96 MiB.
- Declared total uncompressed limit: 512 MiB.
- Package size limit: 256 MiB.
- Suspicious compression-ratio limit: 200:1 for members at least 1 MiB.
- Independent streaming per-file and aggregate extraction limits prevent relying only on ZIP metadata.
- Duplicate archive members are rejected.

Subprocess security:
- Existing FFmpeg/FFprobe execution remains list-argv with explicit executable paths and `shell=False`.
- No Phase 37 `shell=True` path was added; static unsafe-pattern audit passed.
- Short probe/discovery operations remain time bounded; long renders remain cancellable because a fixed global render timeout would break legitimate user media.
- FFmpeg stderr retention remains bounded.
- Security attack strings are verified as single argv/data values, not commands.

FFmpeg escaping:
- Retained ASS/file-based overlay/subtitle rendering instead of direct untrusted drawtext interpolation.
- Retained the dedicated FFmpeg filter-path escape helper for quotes, colons, brackets, commas and semicolons.
- Tests cover quotes/shell metacharacters plus English/Khmer/Thai/Vietnamese Unicode and confirm it remains data.

News SSRF:
- Retained HTTP/HTTPS-only policy, credential-in-URL rejection, localhost/internal-name rejection and global-IP DNS validation.
- Direct private IPv4, IPv6 loopback, link-local/non-global and metadata-service targets remain blocked.
- Redirect destinations are revalidated on every hop.
- Added bounded concurrent News requests and final-response URL revalidation.
- Added best-effort connected-peer IP validation to reduce obvious DNS-rebinding/private-peer bypass where urllib exposes the peer socket.
- No crawler or automatic News crawling was added.

Network/TLS:
- News and model requests use bounded request/socket timeouts; response sizes and redirect counts are bounded.
- Standard Python HTTPS certificate verification remains enabled; no unverified SSL context or `verify=False` shortcut exists.
- Managed model redirects cannot downgrade to HTTP or leave the trusted Hugging Face/hf.co host family.
- Custom/local provider behavior is not conflated with public News SSRF rules; no custom provider product feature was added in this phase.

Model download security:
- Managed source remains a trusted configured Hugging Face HTTPS source.
- Catalog reads are capped at 4 MiB.
- Redirect scheme/host and final response URL are validated.
- Downloaded bytes cannot exceed a known expected file size.
- Existing manifest/required-file/SHA-256 verification is retained before atomic finalization.
- Partial/backup cleanup now uses managed-root safe deletion.
- Downloaded model files are not executed by template/package import.
- Model/native-library parser risk is documented as a remaining supply-chain risk.

Secret storage:
- Current `AppSettings` and current deterministic/local LLM architecture contain no persisted cloud/custom provider credential feature.
- Phase 37 therefore does not add a plaintext secrets file and does not pretend credentials are encrypted.
- Before future persisted provider credentials are implemented, they must use an OS-backed credential mechanism where practical or a clearly separate permission-limited local secret store documented as unencrypted; project files/AppSettings must not contain provider secrets.

Secret redaction:
- Reuses and extends Phase 36 `LogRedactionService` rather than creating a second redactor.
- Added text coverage for Proxy-Authorization, X-Auth-Token, Set-Cookie, credential and signature-style key/value forms while preserving Authorization/Bearer/API-key/password/token/cookie/query redaction.
- Added `SecurityEventService`, which redacts metadata before logging and falls back to a generic redaction-error event rather than raw metadata.
- Phase 36 support-bundle privacy gate and fixed allow-list remain in force.

Reference voice privacy:
- Reference voice recordings remain classified as sensitive user media.
- Phase 36 support bundle allow-list contains no voice/reference/media/project payloads.
- Phase 37 template-package export rejects reference/sensitive voice assets.
- No automatic reference-voice upload path was added.
- Settings > Privacy explicitly explains reference-voice handling.

Cloud-provider privacy:
- Added a read-only privacy policy/service/controller and Settings > Privacy panel.
- Current VoxCPM2, Whisper and managed translation workflows are shown as Local.
- News source fetching and model downloads are shown as Online explicit network actions.
- Cloud AI Providers are shown as Online / Not configured; no cloud provider was implemented.
- Policy marks cloud LLM/translation/TTS/custom-online provider kinds as requiring a first-use notice describing data transmission.
- No “100% private” marketing claim was added.

Database security:
- Reviewed central SQLite/repository patterns: critical project lookup/write queries use DB-API bound parameters rather than user-input SQL concatenation.
- Migrations remain application-defined code; imported JSON/templates do not supply executable SQL.
- Attack-string test binds SQL-injection-shaped text and confirms it remains data and cannot drop/change the table.
- No database reset/replacement behavior was added.

Import validation:
- `.mmovtemplate` gets hostile-archive checks before extraction, JSON-object validation, schema/domain validation and checksums.
- Existing Batch CSV/JSON/JSONL importer was reviewed: it bounds file size (64 MiB), row count (100,000), JSON nesting depth and object structure and never deserializes Python objects.
- Malformed JSON attack test fails safely.
- Existing media probing remains authoritative; Phase 37 does not add extension-only trust or a full project-package format.

Dependency audit:
- Reviewed current `pyproject.toml`; major runtime/optional dependency families remain upper-bounded and were not blindly upgraded.
- Runtime: PySide6, psutil, Pillow. Dev: pytest, pytest-cov, ruff. Optional AI: faster-whisper/ctranslate2, voxcpm/soundfile, transformers/torch/sentencepiece.
- Sandbox metadata observed psutil BSD-3-Clause, soundfile BSD 3-Clause, torch BSD-3-Clause and pytest-cov MIT; optional/uninstalled packages and all model licenses still require release-environment verification.
- Model-library licenses and model-weight licenses are separate review items. No legal conclusion is claimed.
- `python -m pip check` found a shared-sandbox conflict between installed `moviepy 2.2.1` and Pillow 12.3.0; MoviePy is not listed in this project’s current pyproject, so this is recorded as environment follow-up rather than a project dependency change.

Vulnerability scan:
- `pip-audit` is unavailable in this environment (`No module named pip_audit`), so no vulnerability-scan result is claimed.
- The scanner was not added as a runtime dependency.
- Release follow-up: run `pip-audit` or the approved equivalent against a clean locked release environment, review findings, then rerun regressions before upgrading packages.

New files:
- `PHASE37_REPORT.md`
- `app/phase37_runtime.py`
- `docs/security-threat-model.md`
- `docs/security-review-phase37.md`
- `services/archive_security_service.py`
- `services/privacy_service.py`
- `services/safe_path_service.py`
- `services/security_event_service.py`
- `tests/test_phase37_security.py`
- `ui/controllers/privacy_controller.py`
- `ui/qml/privacy/PrivacySettingsPanel.qml`

Modified files:
- `README.md`
- `engines/model_sources.py`
- `main.py`
- `pyproject.toml`
- `services/export_filename_service.py`
- `services/log_redaction_service.py`
- `services/model_download_service.py`
- `services/news_source_fetch_service.py`
- `services/template_package_service.py`
- `ui/qml/pages/SettingsPage.qml`

Tests run:
- Pre-change Phase 36 focused baseline: 43/43 passed.
- Phase 37 focused security suite after implementation: 63/63 passed.
- Phase 36 + Phase 37 overlay regression: 106/106 passed.
- Available Phase 35 + Phase 36 + Phase 37 combined overlay regression: 134/134 passed.
- Phase 35 focused suite separately: 28/28 passed.
- Changed Python compileall: passed.
- Changed/new QML structural balance: 2/2 passed.
- Unsafe-pattern audit for `shell=True`, `verify=False`, and `extractall(` in changed product code: no matches.
- PySide6/qmllint are unavailable in this sandbox, so no live QML desktop launch is claimed.

Path-traversal test:
- Passed for `../../outside.txt`, drive/UNC injections, NUL/ADS/reserved Windows names and deletion outside a managed root.
- Symlink escape test passed on this host; Windows junction/reparse logic is implemented but should also be repeated on real Windows/NTFS.

ZIP-security tests:
- Passed traversal/absolute path rejection, file-count limit, compression-ratio bomb, per-member streaming limit, executable/script rejection, symlink member rejection and checksum mismatch tests.
- Template source static test confirms `extractall()` is not used.

Command-injection test:
- Passed with `"; calc.exe & echo "`, `$(whoami)`, `%TEMP%\evil` and mixed Khmer/Thai/Vietnamese text.
- FFmpeg receives attack-shaped text as one argv/data element with `shell=False`; filter paths preserve Unicode while escaping FFmpeg parser delimiters.

SSRF tests:
- Passed `file://`, `ftp://`, `gopher://`, `data:`, localhost, private IPv4, IPv4 loopback, IPv6 loopback, redirect-to-private and private connected-peer/DNS-rebinding-style cases.
- Public test address remains allowed.

Secret-leak tests:
- Passed Authorization/Bearer, Set-Cookie and secret-bearing URL redaction.
- Safe security-event logging test confirms API key/token values do not appear in logs.
- Support-bundle privacy gate rejects an unredacted API-key form.
- Existing Phase 36 mandatory real bundle tests also pass in the 106/106 and 134/134 regression gates.

Reference-voice privacy test:
- Passed sensitive template-asset classification/rejection policy.
- Support-bundle allow-list test confirms no reference voice/media/project payload filename category exists.
- Existing Phase 36 private-project/reference-voice bundle exclusion regression remains passing.

Output-path security test:
- Passed traversal, absolute Windows drive, UNC, NUL, ADS colon and reserved-device rejection.
- Fixed a discovered Unicode edge case: a dot inside shell-looking filename text no longer causes later Khmer/Thai/Vietnamese text to be mistaken for an extension and truncated.

Known risks:
- No local `.git` checkout: literal `git status` and the entire historical repo test suite cannot be run in this sandbox.
- No PySide6/qmllint: live Windows/QML launch is not claimed.
- Windows junction/UNC/long-path attacks need final native Windows/NTFS verification despite reparse/canonical-path safeguards and Linux symlink coverage.
- urllib connected-peer inspection is best effort because it is not a stable public API; DNS/per-hop redirect policy remains mandatory.
- urllib exposes one socket timeout rather than separately configured connect/read values; it still prevents infinite network waits.
- No OS-backed secret store exists because no current cloud/provider secret persistence exists; it becomes mandatory before such a feature is added.
- `pip-audit` was unavailable; a clean locked release environment still requires vulnerability scanning.
- Native/model parsing supply-chain risk cannot be eliminated solely by application-level path/checksum controls.
- Future updater security is documented but no updater exists or is tested in Phase 37.

Architecture decisions:
- Extend existing Phase 24 template packages, Phase 18 News fetch, Phase 7 model manager/verifier, Phase 29 cleanup/storage and Phase 36 diagnostics/redaction/support instead of duplicating them.
- Centralize new managed-path/archive rules in reusable services; keep filesystem/network/subprocess logic out of QML.
- Keep FFmpeg argv + ASS/file approach; do not introduce shell quoting or direct user-text filter interpolation.
- Treat public News SSRF and explicitly configured custom-provider privacy as separate policies.
- Do not invent cloud providers or secret storage merely to satisfy a security review; document the mandatory boundary before those features exist.
- Preserve offline/manual/local workflows and Unicode behavior.

Recommended next phase:
Phase 38 — Database + Project Migrations

Suggested Git commit:
security: harden filesystem network imports and private data handling

Do not automatically begin Phase 38.

PHASE 42 STATUS

Completed:
- Phase 42 secure, user-controlled Stable update architecture is complete as a source/configuration patch over the committed Phase 41 baseline `ef616713b8498d55163dcb8b58c60859228e375c`.
- The stable packaged entrypoint remains Phase 40 so Phase 40/41 packaging and installer contracts are preserved; Phase 40 delegates through the Phase 42 runtime layer and then the existing Phase 38 migration runtime.
- No Phase 43 work was started.

Update architecture:
- Added domain manifest/state models, trusted manifest/download/validation/state/update services, a QML controller, update UI, build-level trust configuration, release-manifest generator, diagnostics/storage integration, and deterministic security tests.
- Existing Phase 27 recovery/autosave, Phase 29 cleanup, Phase 31 worker pool, Phase 36 diagnostics, Phase 38 migrations, Phase 40 packaging, and Phase 41 installer remain authoritative.
- No duplicate project, migration, storage, installer, job, or recovery subsystem was created.

Versioning:
- Reuses the Phase 40 central `APP_VERSION`.
- Implements SemVer release/prerelease precedence and ignores build metadata for ordering.
- Same/older manifests do not trigger downgrade.
- `minimum_supported_version` is parsed for future security architecture but Phase 42 does not enforce forced lockout.

Manifest:
- Stable schema v1 validates channel, version, minimum supported version, ISO timestamp, HTTPS URLs, SHA-256, positive installer size, optional Authenticode metadata, and optional minimum project schema.
- Future manifest schemas and Beta manifests are rejected.
- Command/script/argument/executable fields are explicitly forbidden.
- `packaging/windows/update-manifest.example.json` and `scripts/generate_update_manifest.py` provide the release contract.

Update check:
- Manual Check for Updates is available under Settings → Updates.
- A persisted Automatically Check preference performs only a lightweight delayed manifest GET on startup.
- Update checks never download the installer automatically.
- Build-level official manifest configuration cannot be overridden by projects/templates/imported content.

Offline behavior:
- Network/HTTP failures are non-fatal and become `Could not check for updates.`.
- Editing/manual/offline workflows continue without interruption.

Download:
- Uses managed `%LOCALAPPDATA%\MMOVideoStudio\updates` staging through `AppPaths`.
- Streams to `.part`, reports progress, supports cancellation and retry, uses a generated semantic-version filename, and never writes over the running application.
- Payloads exceeding the manifest size are aborted while streaming and removed.

Validation:
- Requires managed staging containment, `.exe`, exact expected size, exact SHA-256, and optional expected-publisher Authenticode verification.
- The staged installer is revalidated immediately before launch to detect post-download replacement.
- Validation failure removes the staged executable and never launches it.

Checksum:
- SHA-256 is mandatory in schema v1.
- The mandatory altered-installer attack test serves changed bytes with the original expected digest and verifies the installer is deleted/rejected and the launcher is never called.

Signature verification:
- When `EXPECTED_UPDATE_SIGNER_SUBJECT` is configured, Windows Authenticode must report a valid signature from the expected publisher.
- Deterministic tests cover valid expected publisher and wrong-publisher rejection.
- When no publisher is configured, signature status is explicitly `not configured`; the application does not claim HTTPS + same-origin hash cryptographically proves publisher identity.

Staging:
- URL filenames/path traversal are ignored; the filename is generated as `MMO-Video-Studio-<version>-Setup.exe` inside the managed staging root.
- Old update files are age-cleaned only when no update is downloading/validating/installing.
- Phase 29 now classifies Update Temporary Files as `SAFE_TO_CLEAR`; Phase 42 extends the existing `CleanupService` instance so active downloading/validating/ready/installing state or a pending-update marker vetoes Storage cleanup.
- `pending-update.json` and `last-update.json` are not exposed as disposable Update Temp entries.

Installer handoff:
- Reuses the Phase 41 Setup EXE.
- Launch uses exactly one installer-path argv element with `shell=False`; no manifest-provided executable arguments are accepted.
- The app exits only after installer process launch succeeds.
- Launch failure removes the pending marker and returns the updater to Ready so the current application remains usable.

Active-job protection:
- Install Now is blocked while the shared worker pool has active/pending work, Batch is active, or migration markers indicate migration activity.
- This conservative shared-worker gate covers render/model/background work without duplicating those job systems.
- The mandatory active-work test begins mocked render + Batch work, verifies no launch/flush happens, then verifies the same validated installer launches only after work clears.

Autosave/recovery integration:
- Reuses Phase 27 `AutosaveService`, `RecoverySnapshotService`, and `RecoveryService`.
- Dirty projects receive best-effort `pre_update` recovery snapshots before `flush_all(reason="application_update")`.
- If autosave flush fails, the installer is not launched and a safe visible error is retained.

Post-update migrations:
- Phase 40 remains the console entrypoint and delegates Phase 42 over the existing Phase 38 runtime, so normal Phase 38 database/project migration startup remains authoritative.
- A pending update marker is finalized into `last-update.json` only after startup reaches the Phase 42 container extension and only when the running version is newer than the source and satisfies the intended target version.
- Automatic rollback/downgrade is intentionally not implemented because newer project schemas may not be readable by older application versions.

Update settings:
- Added a real Settings sidebar `Updates` section.
- Shows Current Version, Check for Updates, Automatically Check, and Channel: Stable.
- Available-update dialog supports View Changes, Download Update, Later, progress, Cancel, retry behavior through the controller, active-work guidance, safe errors, and Install Now after validation.
- Release notes are rendered as plain text; external HTTPS notes open only on user action.

Diagnostics integration:
- Phase 36 Application diagnostics report current version, last update check, update state, and sanitized last update error.
- No project/media/script/transcript/subtitle/voice data is added to update diagnostics.

New files:
- `PHASE42_REPORT.md`
- `app/phase42_runtime.py`
- `app/update_config.py`
- `docs/PHASE42_UPDATE_ARCHITECTURE.md`
- `domain/update_manifest.py`
- `domain/update_state.py`
- `packaging/windows/update-manifest.example.json`
- `scripts/generate_update_manifest.py`
- `services/update_download_service.py`
- `services/update_manifest_service.py`
- `services/update_service.py`
- `services/update_state_service.py`
- `services/update_validation_service.py`
- `tests/test_phase42_updates.py`
- `ui/controllers/update_controller.py`
- `ui/qml/updates/UpdateAvailableDialog.qml`
- `ui/qml/updates/UpdateHost.qml`
- `ui/qml/updates/UpdateProgress.qml`
- `ui/qml/updates/UpdateSettings.qml`

Modified files:
- `README.md`
- `app/phase40_runtime.py`
- `docs/known-issues.md`
- `docs/manual-qa-checklist.md`
- `domain/storage_category.py`
- `packaging/windows/README.md`
- `packaging/windows/build_config.json`
- `services/diagnostics_service.py`
- `ui/qml/pages/SettingsPage.qml`

Tests run:
- Phase 42 focused update suite: **34 passed**.
- Cross-phase available packaging/installer/update regression (`test_phase39_packaging.py`, `test_phase40_packaging.py`, `test_phase41_installer.py`, `test_phase42_updates.py`): **104 passed, 1 skipped**.
- The one skip is the existing partial-sandbox QML overlay check requiring the full historical QML tree; it is not a Phase 42 failure.
- Mandatory/security-focused subset: **8 passed, 26 deselected**.
- Python compile check passed for all Phase 42 Python implementation/test/generator files.
- Update-manifest generator smoke passed with Khmer/Thai/Vietnamese Unicode release notes and central version/project schema output.
- Source security grep confirmed no `shell=True` in Phase 42 updater sources.
- Full historical Phase 38 migration test collection could not be independently reconstructed in this sparse delta-only sandbox because unchanged pre-Phase32 dependencies such as `storage/json_writer.py` and Phase 27 recovery modules are not all present. Phase 42's post-update migration-marker test passes, and Phase 38 migration behavior remains delegated to the unchanged committed Phase 38 runtime rather than reimplemented.

Manifest-security test:
- PASS. Covers malformed JSON, invalid version, invalid/future schema, invalid URL scheme, HTTP rejection, Stable-only channel, forbidden executable fields, unsafe redirect downgrade, malicious URL filename/path, and build-level trust configuration.

Checksum-attack test:
- PASS. Altered installer with original expected SHA-256 is rejected/deleted and never launched.

Offline test:
- PASS. Offline/local connection failure returns non-fatal `Could not check for updates.` state.

Cancelled-download test:
- PASS. Cancellation removes `.part`, leaves the update available, and retry succeeds.

Active-work test:
- PASS. Mock render + Batch blocks install and prevents autosave/launcher handoff until active work is cleared.

Installer-handoff test:
- PASS. Uses a single safe installer argv, writes the pending marker, launches only a validated installer, and preserves Ready state on launch failure.

Known limitations:
- `UPDATE_MANIFEST_URL` is intentionally blank until the release owner publishes the official HTTPS manifest endpoint, so updater networking is disabled in unconfigured builds.
- `EXPECTED_UPDATE_SIGNER_SUBJECT` is intentionally blank until a real Windows code-signing identity is provisioned; HTTPS + checksum is the minimum integrity path but is not represented as independent publisher authentication.
- Native Authenticode, real Setup EXE update round-trip, clean Windows 11 non-admin upgrade/data-preservation, and complete QML/accessibility acceptance still require the documented release-workstation checklist before public rollout.
- No forced update, Beta channel, automatic rollback/downgrade, binary delta patching, arbitrary remote HTML/JS, or custom proxy UI is implemented.
- The current patch sandbox is a delta overlay rather than a full `.git` checkout, so literal local `git status` and a fully reconstructed Phase 38 historical test environment were unavailable; GitHub Phase 41 commit `ef616713b8498d55163dcb8b58c60859228e375c` was used as the authoritative baseline.

Architecture decisions:
- Keep `app.phase40_runtime:run` as the stable packaged entrypoint so Phase 40/41 tests and installer contracts remain valid.
- Layer Phase 42 through the shared Phase 31 container extension point and delegate to Phase 38 instead of creating a new bootstrap.
- Reuse Phase 27 recovery/autosave, Phase 29 cleanup, WorkerPool, Phase 36 diagnostics, Phase 38 migrations and Phase 41 installer.
- Trust updater endpoints only from build configuration; never from projects/templates/imported data.
- Require user consent before installer download and before install; no forced updates.
- Keep release notes plain text and external navigation user-triggered.
- Prefer fail-closed validation and conservative active-work blocking over risky self-modification.

Recommended next phase:
Phase 43 — Final Production Audit

Suggested Git commit:
feat: add secure Windows update architecture

Do not automatically begin Phase 43.

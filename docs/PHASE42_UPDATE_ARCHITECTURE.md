# Phase 42 — Secure Update Architecture

Phase 42 adds a user-controlled Stable-channel update path to the existing Windows packaging and installer architecture. It does **not** self-modify the running application and it does not replace the Phase 41 installer. The update layer checks trusted metadata, downloads only after user consent, validates the staged Setup EXE, flushes recovery/autosave state, launches the existing installer with an argv-only subprocess call, and exits only after launch succeeds.

## Trust model

The official manifest URL is build-level configuration in `app/update_config.py` and mirrored in `packaging/windows/build_config.json`. Project files, templates, imported assets, News content, and other user data cannot redefine the updater URL.

Production metadata and installer URLs must use HTTPS. The only HTTP exception is an explicit localhost-only test mode used by the deterministic QA server. Redirects are revalidated and an HTTPS request cannot downgrade to HTTP. Manifests containing command/script/argument/executable fields are rejected.

HTTPS plus a SHA-256 value fetched from the same HTTPS origin protects against corruption and many tampering cases, but **does not by itself prove publisher identity if that origin is compromised**. When a release certificate is configured, `EXPECTED_UPDATE_SIGNER_SUBJECT` activates Windows Authenticode verification and the installer is rejected unless Windows reports a valid signature from the expected publisher. The repository intentionally keeps the publisher identity empty until release signing is actually provisioned.

## Manifest

Stable manifest schema version 1 contains:

- `schema_version`
- `channel` (`stable` only)
- `version`
- `minimum_supported_version` (architecture only; no Phase 42 lockout)
- `published_at`
- plain-text `release_notes`
- optional HTTPS `release_notes_url`
- HTTPS `installer_url`
- `installer_sha256`
- positive `installer_size`
- optional Authenticode signature metadata
- `minimum_project_schema`

`SemanticVersion` implements release/prerelease ordering and intentionally ignores build metadata for precedence. Same/older manifests never trigger a downgrade path. Future manifest schemas are rejected.

Generate release metadata from the central application version with:

```powershell
py -3.11 scripts\generate_update_manifest.py `
  --installer "dist\installer\MMO-Video-Studio-Setup.exe" `
  --installer-url "https://updates.example.com/MMO-Video-Studio-Setup.exe" `
  --output "dist\installer\update-manifest.json" `
  --release-notes "Release notes"
```

Add `--signer-subject` only when the real Windows signing identity is configured.

## Update check and privacy

Settings → Updates shows the current version, Stable channel, manual Check for Updates, and the persisted Automatically Check preference. Automatic checks are lightweight metadata GET requests only and never download an installer automatically. No project, media, script, transcript, subtitle, template, voice, asset, or analytics data is sent by the updater.

If the device is offline or the update source is unavailable, the editor remains usable and the state becomes a non-fatal `Could not check for updates.` error.

## Download and staging

Downloads use `%LOCALAPPDATA%\MMOVideoStudio\updates` through the existing `AppPaths` root. The filename is generated from the validated semantic version instead of trusting a URL path. A `.part` file is streamed in bounded chunks, supports cancellation, reports progress, and is removed after cancellation/failure. A response that exceeds the manifest's expected installer size is rejected while streaming rather than filling the staging disk first.

Phase 29 classifies Update Temporary Files as `SAFE_TO_CLEAR`. Phase 42 extends the **existing** `CleanupService` instance rather than creating a second cleanup subsystem. Update staging is visible as a managed cleanup root, but download/validation/ready/installing states and a pending update marker veto deletion. `pending-update.json` and `last-update.json` are not exposed as disposable staging entries.

## Validation

Before an installer becomes Ready:

1. it must remain inside the managed staging directory;
2. it must be an `.exe`;
3. byte size must equal the manifest size;
4. SHA-256 must equal the manifest digest;
5. when a publisher is configured, Authenticode must be valid and match that expected publisher.

Any checksum/size/signature validation failure removes the staged executable. The installer is revalidated immediately before launch to detect replacement after the original download.

## Installer handoff and active work

Phase 42 launches the Phase 41 Setup EXE with a one-element argv list and `shell=False`; manifests cannot supply installer arguments or commands. Install Now is blocked while the shared worker pool reports active/pending work, Batch is active, or migration markers indicate migration work. This conservative gate covers render/model/background tasks without duplicating their job systems.

Before installer launch, Phase 27 recovery is reused: dirty projects receive a best-effort pre-update recovery snapshot and `AutosaveService.flush_all(reason="application_update")` must succeed. If saving fails, installation is blocked and the current application remains usable.

The app writes `pending-update.json` immediately before launch. If installer launch fails, that marker is removed and the app returns to Ready state. The application quits only after the installer process launches successfully.

## First launch after update

The stable packaged entrypoint remains `app.phase40_runtime:run`, preserving Phase 40/41 launcher contracts. Phase 40 delegates through Phase 42, which layers its container integration over Phase 38. Normal Phase 38 database/project migration startup therefore remains authoritative. After those startup migrations complete, Phase 42 finalizes a matching pending-update marker into `last-update.json` only when the running application version is actually newer and satisfies the intended target.

Phase 42 does not implement automatic application rollback or downgrade. Projects migrated to a newer schema may not open in an older application version, so rollback must be treated as a release-engineering/manual recovery operation rather than an automatic updater feature.

## UI and release notes

The update UI reuses the Phase 28 low-saturation shared controls. Settings now has a real Updates section, and an available-update dialog supports View Changes, Download Update, Later, progress/cancel, validation state, Install Now, active-work messaging, and safe install-error feedback.

Release notes embedded in the manifest are rendered as plain text. An external release-notes URL is opened only after a user action and only if it is HTTPS. No remote HTML/JavaScript is rendered inside the application.

## Diagnostics

Phase 36 Application diagnostics add only update-safe fields:

- current application version
- last update check
- update state
- last sanitized update error

No project/media content is added to diagnostics or support-bundle inputs.

## Release limitations

- `UPDATE_MANIFEST_URL` is intentionally blank until the release owner publishes the official HTTPS endpoint.
- `EXPECTED_UPDATE_SIGNER_SUBJECT` is intentionally blank until a real code-signing certificate/publisher identity is provisioned. In that state checksum+HTTPS validation is used, but publisher authentication is not claimed.
- Native Authenticode, real Phase 41 installer handoff, clean-profile upgrade preservation, and Windows UI behavior still require the Windows 11 release-workstation checklist before a public release is approved.
- No forced-update lockout, automatic binary downgrade, delta patching, Beta channel, or custom proxy UI is implemented in Phase 42.

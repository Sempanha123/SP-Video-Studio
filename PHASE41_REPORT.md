# PHASE 41 STATUS

**Implementation complete; native Windows installer release acceptance is pending on Windows 11 x64.**

Phase 41 adds the installer/uninstaller layer only. It does not begin Phase 42 and does not redesign the Phase 40 standalone application package.

## Completed:
- Added a per-user Windows 11 x64 installer definition around the verified Phase 40 one-folder application.
- Added a stable installer identity/AppId for in-place upgrades and one uninstall registration.
- Added numeric downgrade blocking against the registered installed `DisplayVersion`.
- Added a process-lifetime Windows application mutex shared with Inno Setup so install/update/uninstall will not replace a running application unsafely.
- Kept application binaries separate from `%LOCALAPPDATA%\MMOVideoStudio` managed user data.
- Preserved managed user data on normal upgrade and normal uninstall.
- Added explicit **No-by-default** interactive managed-data removal and explicit `/REMOVEAPPDATA` silent-QA opt-in.
- Added Start Menu shortcut plus optional unchecked Desktop shortcut.
- Added installer build, signing, SHA-256, manifest, logging, and native acceptance scripts.
- Added fresh-install, upgrade, downgrade, uninstall-preserves-data, explicit-removal, non-admin, Unicode/path-with-spaces and no-Python/FFmpeg acceptance coverage to the Windows verifier.
- Added Phase 41 packaging contract tests and documentation.
- No file association, URL protocol handler, service, driver, PATH edit, telemetry, online registration, model weights, or font binaries were added.

## Installer technology:
- **Inno Setup 7.1.0 x64**.
- Chosen for a small, reliable scriptable layer over the existing Phase 40 one-folder build rather than introducing MSI/WiX infrastructure without a product requirement.
- Compiler is a reviewed build-workstation prerequisite; the build script never downloads it silently.

## Install scope:
- **Per-user**.
- `PrivilegesRequired=lowest`.
- No elevation/UAC is required for the normal install path.
- Target is Windows 11 x64 only.

## Install location:
- Default application binaries/resources: `%LOCALAPPDATA%\Programs\MMO Video Studio`.
- Managed application data remains: `%LOCALAPPDATA%\MMOVideoStudio`.
- User-selected project/export paths outside the managed data root remain external to installer ownership.

## User-data policy:
- Upgrade and default uninstall preserve `%LOCALAPPDATA%\MMOVideoStudio`.
- Preserved categories include settings, models/model metadata, Asset Library data, templates, cache, recovery, logs, managed downloads/exports, voices, and the local database.
- Project folders stored elsewhere are not moved or deleted by Setup/Uninstall.

## Upgrade behavior:
- Stable AppId: `{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}`.
- `UsePreviousAppDir=yes` and `UsePreviousGroup=yes` allow N+1 to install over N without manual uninstall.
- Installer version is derived from central `app.constants.APP_VERSION` and must match the Phase 40 `build-manifest.json`.
- Application data is not placed under `{app}`, so replacing application files does not remove managed user data.
- A real previous-installer fixture is required by the native upgrade release gate.

## Downgrade behavior:
- Setup reads the current-user uninstall registration `DisplayVersion`.
- Versions are normalized and compared numerically with Inno Setup `StrToVersion` / `ComparePackedVersion`.
- If the installed version is newer, the older Setup exits instead of intentionally putting older application/schema code over newer data.

## Uninstall behavior:
- Default uninstall removes application files, Start Menu/Desktop shortcuts, and installer registration.
- There is intentionally no declarative `[UninstallDelete]` rule for `%LOCALAPPDATA%\MMOVideoStudio`.
- Default silent uninstall also preserves managed data.
- The shared application mutex prevents uninstall while MMO Video Studio is running.

## Optional data removal:
- Interactive uninstall offers an explicit confirmation after normal uninstall; **No is the default**.
- The prompt shows `%LOCALAPPDATA%\MMOVideoStudio`, names managed categories, and states external projects/exports are not removed.
- Disposable QA may explicitly use `/REMOVEAPPDATA`.
- Deletion is limited to the exact managed LocalAppData root; external project/export sentinels are verified by the native test script.

## Shortcuts:
- Start Menu: created by default.
- Desktop: optional installer task, unchecked by default.
- Normal uninstall removes installer-owned shortcuts.

## File associations:
- None.
- `.mmovtemplate` is not associated because safe import-on-open is not yet an established startup contract.
- No project extension was invented.
- No URL protocol handler was added.

## Prerequisites:
- End users do **not** need a separate Python installation.
- Phase 41 consumes the already-built Phase 40 standalone folder and does not rerun Nuitka.
- Inno Setup is build-time only.
- No random Visual C++ or other runtime installer is downloaded silently. If a future dependency requires a vendor redistributable, that must be reviewed and added explicitly.

## FFmpeg:
- Follows Phase 40.
- The installer consumes the verified Phase 40 `bin\ffmpeg.exe` and `bin\ffprobe.exe` plus exact FFmpeg `LICENSE.txt` / `SOURCE.txt` notices.
- No runtime FFmpeg download behavior was added.

## Models:
- Giant model weights are not bundled by the installer.
- Models continue to live under `%LOCALAPPDATA%\MMOVideoStudio\models` and are managed by the existing Model Manager/runtime.

## Signing support:
- Optional final Setup EXE signing uses `signtool.exe` only when an external certificate thumbprint is supplied.
- Inputs: `MMOVS_SIGN_CERT_THUMBPRINT` and optional `MMOVS_SIGN_TIMESTAMP_URL`.
- No certificate, password, private key, PFX, or signing token is stored in the repository.
- Development builds do not fail merely because a signing certificate is absent.

## Installer hash:
- Native installer hash was **not generated in this Linux sandbox because no Windows/Inno Setup executable was built here**.
- `scripts/build_windows_installer.ps1` generates `MMO-Video-Studio-<version>-Setup.exe.sha256` with SHA-256 and records the same hash in `installer-manifest.json` immediately after optional signing.

## Third-party notices:
- The verified Phase 40 package must contain `licenses\THIRD_PARTY_NOTICES.md` and exact `licenses\ffmpeg\LICENSE.txt` / `SOURCE.txt`; Phase 41 refuses to build without them.
- Phase 41 adds `packaging/windows/notices/APPLICATION_LICENSE_NOTICE.txt`.
- **Known public-release gate:** this repository does not yet contain owner-approved public application license terms. Phase 41 deliberately does not invent an MIT/Apache/GPL or other license. Replace/link that notice with the final owner-approved terms before public/commercial distribution.

## New files:
- `PHASE41_REPORT.md`
- `docs/PHASE41_WINDOWS_INSTALLER.md`
- `packaging/windows/installer/MMO-Video-Studio.iss`
- `packaging/windows/installer/README.md`
- `packaging/windows/installer/installer_config.json`
- `packaging/windows/notices/APPLICATION_LICENSE_NOTICE.txt`
- `scripts/build_windows_installer.ps1`
- `scripts/verify_windows_installer.ps1`
- `tests/test_phase41_installer.py`

## Modified files:
- `README.md`
- `app/phase40_runtime.py`
- `docs/known-issues.md`
- `packaging/windows/README.md`
- `packaging/windows/build_config.json`

## Fresh-install test:
- Automated/static Phase 41 installer contracts: **34 passed**.
- Phase 40 + Phase 41 packaging regression: **65 passed, 1 skipped**; the skip is the known partial-sandbox QML-tree assertion and becomes mandatory on a full checkout.
- Phase 39 + Phase 40 + Phase 41 `PACKAGING_SMOKE` regression-only overlay: **70 passed, 1 skipped** for the same partial-QML reason.
- Native clean-profile install/Start Menu/onboarding/create/import/render/reopen execution: **pending Windows 11 x64**. The verifier always requires an absent managed-data root and implements this acceptance flow with `-RequireCleanProfile -RequireNonAdmin -RequireInteractiveAcceptance`.
- Phase 40 recorded full RELEASE baseline before this installer phase: **247 passed, 7 environment/source skips, 0 failed**. The current replacement-ZIP sandbox does not contain the unchanged full `domain/` tree, so a new full Phase 38–41 release collection cannot be honestly rerun here.

## Upgrade test:
- Static upgrade/downgrade contract tests passed.
- Native N → N+1 test is **pending Windows 11 x64 with a real previous installer fixture built with the same AppId**.
- The verifier creates project/settings/template/asset/model metadata sentinels, installs N+1, checks preservation/migrations, and then attempts the previous installer to verify downgrade blocking.

## Uninstall-preserves-data test:
- Static contract passed: no `[UninstallDelete]` managed-data rule, default preservation, installer-owned shortcut checks.
- Native uninstall-preserves-data execution is **pending Windows 11 x64**.

## Optional-data-removal test:
- Static scope/default-No contract passed.
- Native destructive acceptance is **pending a disposable clean Windows profile/VM**.
- The verifier now refuses to start at all when `%LOCALAPPDATA%\MMOVideoStudio` already exists, so QA sentinels and destructive removal tests cannot touch a pre-existing real managed-data profile.

## Non-admin test:
- Per-user/no-elevation configuration is covered by automated contract tests.
- Native non-admin install is **pending Windows 11 x64**; verifier `-RequireNonAdmin` rejects an elevated/admin process for that gate.

## Unicode/path test:
- Build and verifier scripts are Unicode text and explicitly use a path with spaces plus Khmer characters and sentinels containing Khmer, Thai, and Vietnamese.
- Python/JSON compile/parse passed in this sandbox.
- Native Windows install/render under that path is **pending Windows 11 x64**.

## Known issues:
- Native Inno Setup compilation cannot run in this Linux sandbox; `.iss` syntax has static contract/delimiter coverage but must still be compiled by reviewed Inno Setup 7.1.0 x64 on Windows.
- Native installer acceptance is deliberately not run automatically by the normal build command; use `-RunNativeVerify` only when the build itself is inside a disposable clean QA profile, otherwise verify separately on a clean VM/profile.
- Fresh/upgrade/uninstall/non-admin/Unicode installer acceptance remains a Windows-only release gate.
- Upgrade acceptance needs a real earlier installer fixture; Phase 40 itself had no installer.
- Phase 40 standalone Windows-native verification must already be green before its dist folder is accepted as Phase 41 input.
- Owner-approved public application license terms are not yet supplied.
- Unsigned development installers may trigger Windows reputation warnings; signing is supported but credentials are intentionally external.

## Installer output:
- Expected Windows artifact: `dist\installer\MMO-Video-Studio-0.1.0-Setup.exe` for the current `APP_VERSION`.
- Expected hash sidecar: `dist\installer\MMO-Video-Studio-0.1.0-Setup.exe.sha256`.
- Expected build metadata: `dist\installer\installer-manifest.json`.
- No Setup EXE is included in this source patch because it cannot be compiled/verified in the Linux sandbox and should be produced from the reviewed Phase 40 Windows dist on the release workstation.

## Architecture decisions:
- Extend Phase 40 rather than add `app/phase41_runtime.py`; the existing `app.phase40_runtime:run` entry point remains authoritative.
- Add only a small Windows mutex to the existing packaged runtime for installer safety.
- Use per-user LocalAppData binaries so normal installation avoids UAC and does not require Program Files writes.
- Keep all mutable/user data outside the install directory.
- Use a stable AppId forever for this product line.
- Block downgrade instead of attempting risky backward schema compatibility.
- Let Setup own binaries/shortcuts/installer records, but not arbitrary user project/export locations.
- Keep destructive user-data removal explicit, No-by-default, and limited to one managed root.
- Consume the already verified Phase 40 standalone folder; do not duplicate Python/Nuitka packaging logic in the installer phase.
- Keep signing optional and credentials external.
- Do not add file associations until there is a safe import-on-open contract.

## Recommended next phase:
**Phase 42 — Update Architecture**

Phase 42 has **not** been started.

## Suggested Git commit:
`build: add safe Windows installer and upgrade flow`

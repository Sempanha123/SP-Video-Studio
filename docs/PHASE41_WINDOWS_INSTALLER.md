# Phase 41 — Windows Installer

## Architecture decision

Phase 41 uses **Inno Setup 7.1.0 x64**. It is a small, mature scriptable installer layer around the already verified Phase 40 one-folder application; introducing WiX/MSI infrastructure would add more moving parts without a product requirement. Inno Setup 7 supplies a native x64 Setup executable and supports current Windows 11.

The installer is deliberately **per-user** and non-elevated. `PrivilegesRequired=lowest` installs binaries to `%LOCALAPPDATA%\Programs\MMO Video Studio`, while the application keeps all managed mutable data under `%LOCALAPPDATA%\MMOVideoStudio`. No machine-wide registry writes, services, drivers, URL handlers, PATH edits, or system-wide prerequisites are introduced.

## Identity and upgrades

The stable installer identity is:

```text
AppId = {38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}
```

Do not change that AppId in later versions. Inno uses it to find the existing uninstall registration and append/update the same application installation. `UsePreviousAppDir=yes` keeps the previous directory on upgrade, so users do not need to uninstall manually first.

`AppVersion`, Setup file metadata, output filename, and the generated installer hash are derived from the same Phase 40 central application version (`app.constants.APP_VERSION`, recorded in `build-manifest.json`). The Phase 41 builder refuses a Phase 40 dist whose manifest version and source version disagree.

Before installation, Setup reads the current-user uninstall registration and compares its `DisplayVersion` with the incoming version using packed numeric comparison. A newer installed version blocks an older installer. This avoids intentionally putting a database/project-schema-newer installation behind older application code.

## Running application safety

The packaged runtime creates a Windows named mutex for the life of the process. The Inno `AppMutex` uses the same name, so Setup and Uninstall ask the user to close MMO Video Studio before continuing. Inno Restart Manager handling is also left enabled with `CloseApplications=yes`; force-close is not enabled and automatic app restart is disabled.

## Files and data ownership

Setup installs the entire verified Phase 40 standalone directory as application files. That includes QML/resources, Qt/PySide/native dependencies, the reviewed bundled `bin\ffmpeg.exe` / `ffprobe.exe`, build manifest, and the exact third-party/FFmpeg notices staged in Phase 40.

Phase 41 adds `licenses\application\APPLICATION_LICENSE_NOTICE.txt`. The repository still does not contain owner-approved public application license terms; this notice explicitly avoids implying a license. Replacing it with the final owner-approved license is a public-release legal/content gate, not something the installer should invent.

Large model weights are not installed. The application creates/uses `%LOCALAPPDATA%\MMOVideoStudio\models` only when needed.

## Shortcuts and associations

- Start Menu shortcut: yes.
- Desktop shortcut: optional task, unchecked by default.
- Project file association: none; there is no invented project extension.
- `.mmovtemplate` association: none in Phase 41 because safe import-on-open is not an established startup path.
- URL protocol handler: none.

## Uninstall policy

Normal uninstall removes the application directory, shortcuts, and installer registry records. There is intentionally **no `[UninstallDelete]` rule** targeting user data.

After interactive uninstall, an explicit confirmation offers managed application-data removal. **No is the default.** The prompt names `%LOCALAPPDATA%\MMOVideoStudio` and categories: settings, models, Asset Library data, user templates, cache, recovery, logs, managed downloads/exports, voices, and the local database. It also says projects/exports outside that folder are not removed.

Silent uninstall preserves data by default. Disposable automated QA may explicitly add `/REMOVEAPPDATA`; the script still deletes only the exact managed LocalAppData root.

## Prerequisites

The end user does not need Python, Visual Studio Build Tools, Inno Setup, or separate FFmpeg. Those are build-time inputs (or, for FFmpeg, part of the verified Phase 40 application payload). The installer does not download random redistributables. If a future native dependency introduces a redistributable requirement, add only a reviewed vendor redistributable strategy and test it before shipping.

## Signing and hashes

The Phase 40 application EXE can already be signed externally. `build_windows_installer.ps1` can separately sign the final Setup EXE with `signtool.exe` when an external certificate thumbprint is supplied. No signing credential is stored in source.

Every installer build emits a SHA-256 sidecar next to the setup executable. Preserve both files with the release artifacts.

The installer build does not automatically run the native acceptance because that verifier is intentionally restricted to a disposable clean profile. Run it as a separate release gate on the Windows VM/profile; `-RunNativeVerify` is only for a build already running in that disposable environment.

## Native Windows acceptance

`verify_windows_installer.ps1` always refuses a pre-existing `%LOCALAPPDATA%\MMOVideoStudio` root. Native installer acceptance must therefore run in a disposable clean profile/VM; this prevents QA sentinels or removal tests from touching real user data.

Run on Windows 11 x64 from a disposable clean non-admin profile/VM:

```powershell
.\scripts\verify_windows_installer.ps1 `
  -Installer '.\dist\installer\MMO-Video-Studio-0.1.0-Setup.exe' `
  -RequireCleanProfile `
  -RequireNonAdmin `
  -RequireInteractiveAcceptance
```

For upgrade/downgrade coverage, also supply a real previous installer built with the same stable AppId:

```powershell
.\scripts\verify_windows_installer.ps1 `
  -Installer '.\dist\installer\MMO-Video-Studio-0.1.0-Setup.exe' `
  -PreviousInstaller 'C:\release-fixtures\MMO-Video-Studio-0.0.9-Setup.exe' `
  -RequireCleanProfile `
  -RequireNonAdmin `
  -RequireUpgradeFixture `
  -RequireInteractiveAcceptance
```

The verifier covers install path with spaces/Khmer text, standard install logging, Start Menu launch, packaged no-Python/FFmpeg self-check, data sentinels, default uninstall preservation, explicit managed-data removal, and (when provided) N → N+1 upgrade plus downgrade blocking. Interactive acceptance performs the real create/import/render/reopen flow and validates migration behavior on the previous-version project fixture.

## Current execution limitation

This phase was implemented/tested in a Linux sandbox. Inno Setup and the Windows installer runtime are not available here, so the source/configuration contracts can be tested but a genuine Setup EXE, Add/Remove Programs registration, UAC behavior, Restart Manager prompt, Start Menu launch, and uninstall flow cannot truthfully be claimed as executed. Those are mandatory Windows release gates in `verify_windows_installer.ps1`.

- Native verification covers Unicode/path-with-spaces installation and Khmer/Thai/Vietnamese data paths.

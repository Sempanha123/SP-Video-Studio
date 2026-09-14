# Phase 41 Windows installer

MMO Video Studio uses **Inno Setup 7.1.0 x64** for the Windows 11 x64 consumer installer. The application itself must already have been produced and verified by Phase 40.

## Install model

- Scope: **per-user** (`PrivilegesRequired=lowest`), so normal installation does not request UAC elevation.
- Default binaries: `%LOCALAPPDATA%\Programs\MMO Video Studio`.
- Mutable application data: `%LOCALAPPDATA%\MMOVideoStudio` (never placed under the install folder).
- Project folders remain wherever the user selected them. The installer does not invent or manage a project file association.
- Start Menu shortcut is created; desktop shortcut is optional and unchecked by default.
- Stable AppId: `{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}`.
- Same AppId + `UsePreviousAppDir=yes` supports installing a newer version over the older one without a manual uninstall.
- Downgrade is blocked when the registered installed version is newer than the setup version.
- `CloseApplications=yes`, `RestartApplications=no`, and the shared application mutex prevent unsafe replacement of a running app.

## Build

Install the reviewed Inno Setup **7.1.0 x64** compiler on the build workstation. The build script does not download it silently.

```powershell
.\scripts\build_windows_installer.ps1 -DistDir '.\dist\MMO Video Studio'
```

Use `-InnoCompiler` or `MMOVS_INNO_COMPILER` if `ISCC.exe` is not in a standard install location.

The output is:

```text
dist\installer\MMO-Video-Studio-<version>-Setup.exe
dist\installer\MMO-Video-Studio-<version>-Setup.exe.sha256
```

The build command does **not** run the disposable-profile installer acceptance automatically. Run `verify_windows_installer.ps1` on a clean Windows VM/profile after copying the installer + `.sha256` sidecar there. `-RunNativeVerify` is available only when the build itself is already running inside such a clean QA profile.

## Signing

The setup EXE is optionally signed after compilation using the same external certificate-thumbprint/timestamp inputs as Phase 40:

```powershell
$env:MMOVS_SIGN_CERT_THUMBPRINT = '<certificate thumbprint>'
$env:MMOVS_SIGN_TIMESTAMP_URL = '<approved timestamp URL>'
.\scripts\build_windows_installer.ps1
```

No certificate, password, private key, or signing token belongs in the repository or installer payload. The inner app EXE should already have been signed by the Phase 40 build when release signing is configured.

## Logs and silent install

Inno Setup's standard logging is supported:

```powershell
.\MMO-Video-Studio-0.1.0-Setup.exe /LOG="C:\Temp\mmo-install.log"
```

Consumer silent installation is optional, not the primary flow:

```powershell
.\MMO-Video-Studio-0.1.0-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="C:\Temp\mmo-install.log"
```

The installer itself has no telemetry and no online registration requirement.

## Uninstall and user data

Default uninstall removes installed application files, Start Menu/Desktop shortcuts, and installer registration only. It **does not delete** `%LOCALAPPDATA%\MMOVideoStudio`.

Interactive uninstall asks, with **No as the default**, whether to remove that managed data folder. The prompt lists the categories and states that external project/export folders are not removed.

The native verifier is intentionally stricter than Setup itself: it refuses to start if `%LOCALAPPDATA%\MMOVideoStudio` already exists, so QA cannot pollute or delete a real user profile.

For disposable automated QA profiles only, silent uninstall can explicitly opt in with:

```text
/REMOVEAPPDATA
```

Never use that switch on a real profile unless the managed `%LOCALAPPDATA%\MMOVideoStudio` data is intentionally being deleted.

## File associations / protocol handlers

None are registered in Phase 41. `.mmovtemplate` is not associated because safe import-on-open is not yet an established startup contract, and no project extension is invented. URL protocol handlers are not added.

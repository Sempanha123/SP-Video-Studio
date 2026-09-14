# Phase 40 — Windows Packaging

## Scope

Phase 40 packages the existing MMO Video Studio release line as a reproducible **Windows 11 x64**, **CPython 3.11**, **Nuitka standalone one-folder** application. It does not introduce a second application bootstrap, does not embed model weights, does not convert the product to a one-file executable, and does not start the Phase 41 installer.

The selected baseline build tool versions are **Nuitka 4.2.1** and **PySide6 6.11.2**. These are pinned in `packaging/windows/constraints-win311.txt`; the application version continues to come from `app.constants.APP_VERSION`.

## Why one-folder

Qt/QML, FFmpeg, optional AI runtimes and native extension libraries are easier to inspect and verify in a standalone folder. One-file extraction would add startup complexity and make native-library/QML troubleshooting harder without a product benefit at this stage. Phase 40 therefore produces:

```text
dist/
  MMO Video Studio/
    MMO Video Studio.exe
    build-manifest.json
    bin/
      ffmpeg.exe
      ffprobe.exe
    ui/qml/...
    resources/...
    licenses/...
    PySide6 / Qt / native runtime files produced by Nuitka...
```

## Build Python and compiler

Build with **64-bit CPython 3.11**. The script creates `.build/phase40-windows/py311` and refuses another Python major/minor architecture. It uses Nuitka with the Windows MSVC toolchain (`--msvc=latest`); install a current Visual Studio 2022 Build Tools C++ workload on the build machine. Phase 40 intentionally does not move the production build to Python 3.14 simply because that interpreter may exist on a developer PC.

## Build modes

`build_windows.ps1` supports:

- `Release` — GUI application, console disabled.
- `Development` — standalone build with console available for development troubleshooting.
- `Debug` — console plus Nuitka debug mode.

The application always writes operational logs to `%LOCALAPPDATA%\MMOVideoStudio\logs`; a Release build does not rely on a console for crash diagnosis.

## QML and read-only resources

Nuitka includes `ui/qml` and `resources` explicitly. The PySide6 plugin is enabled and QML plugins are explicitly requested. Nuitka's PySide plugin retains its sensible Qt plugin set; the required families for this application are QML, the Windows platform plugin, image formats, and Qt Multimedia. The custom QML theme does not require a separate Qt style plugin, and online features use Python networking rather than Qt TLS/network plugins. The Windows verifier checks the required runtime resources rather than copying every Qt plugin blindly.

The bundled read-only resource set includes current QML pages/components/theme, SVG/UI icons, `resources/languages.json`, built-in templates, subtitle/export/news/voice static configuration and the Phase 40 application icon. Runtime data is never stored under this resource tree.

## FFmpeg strategy

Phase 40 chooses **bundled-at-build-time** FFmpeg/FFprobe. The application does not download either executable at runtime.

The builder stages an externally reviewed FFmpeg folder and passes `-FFmpegDir` (or `MMOVS_FFMPEG_DIR`). Four files are mandatory: `ffmpeg.exe`, `ffprobe.exe`, `LICENSE.txt`, and `SOURCE.txt`. The build probes the executables, copies only `ffmpeg.exe`/`ffprobe.exe` to `bin/`, and copies the exact license/source notices to `licenses/ffmpeg/`.

`FFmpegLocator` checks the controlled packaged `bin/` first, then preserves the existing custom-path/PATH behavior for source/developer runs. It never expands a command through a shell.

FFmpeg's redistribution obligations depend on the exact staged build configuration and linked libraries. `FFMPEG_STAGING.md` and the third-party notice are release checklists, not legal conclusions.

## Writable app data

On Windows, existing `AppPaths` already roots application-managed mutable data under:

```text
%LOCALAPPDATA%\MMOVideoStudio\
```

That includes models, cache, recovery, Asset Library data, logs, settings, downloads, voices/templates managed by the user, exports metadata and the application database. Projects continue to live in the configured project location (the existing default is the user's Documents area), never under Program Files or inside the compiled bundle.

The Windows verifier replaces `LOCALAPPDATA` with a fresh temporary profile and confirms the packaged self-check writes under that profile only.

## Models and AI runtime dependencies

Large model weights are **not bundled**. Model Manager continues to install them separately under `%LOCALAPPDATA%\MMOVideoStudio\models`.

The Release build can include the Python/native runtimes needed after a model is installed: `faster_whisper`, `ctranslate2`, `voxcpm`, `transformers`, `torch`, `sentencepiece`, and `soundfile`. These dynamic/native packages are explicit in the packaging configuration so Nuitka does not depend on accidental source-tree imports.

The default PyTorch build input uses the official CPU wheel channel. This keeps the base package functional on systems with no CUDA and avoids blindly bundling an NVIDIA driver stack. A CUDA-oriented package can be built only after separate dependency/DLL review by overriding `-TorchIndexUrl`; users still need a compatible NVIDIA driver. Existing readiness/engine capability checks remain authoritative at runtime.

## Fonts

Phase 40 adds **no font files**. Multilingual text continues to use the Language Registry's system-font fallback lists. Do not add a `.ttf`, `.otf`, `.woff`, or similar binary to the package until redistribution rights for that exact font have been confirmed.

## Application icon and Windows metadata

`resources/icons/app.ico` contains multiple common Windows icon sizes. Nuitka embeds it with `--windows-icon-from-ico`; modern Nuitka also applies that icon to PySide6 applications. The Phase 40 runtime additionally supplies Qt's standard `-qwindowicon` argument when running the packaged executable.

Windows version metadata is set from the central application version and build configuration:

- Product: `MMO Video Studio`
- Company/author label: `SP Video Studio`
- File description: `MMO Video Studio`
- File/product version: `APP_VERSION` normalized to four numeric components

## Build manifest

`scripts/generate_build_manifest.py` writes `build-manifest.json` after the standalone folder is assembled. It records app version, commit hash when available, UTC build time, build mode, Python version, PySide6 version, Nuitka version, FFmpeg version/source note, architecture, layout and model strategy. The manifest contains no credential fields.

## Secret and development-file scan

`scripts/verify_windows_build.ps1` refuses `.git`, tests, pytest output, `.env` files, common private-key/certificate files, and obvious credential assignments in packaged text/config files. Signing configuration is read from command parameters/environment only and is never copied into the package.

## Code signing preparation

Signing is optional in Phase 40. When `MMOVS_SIGN_CERT_THUMBPRINT` (or `-SigningCertificateThumbprint`) is provided, the build finds `signtool.exe` and signs the final EXE. An optional timestamp URL may also be supplied. No certificate, password, key, or token is stored in the repository. Phase 41 can reuse this build output for installer signing.

Unsigned/Nuitka-generated executables can receive reputation-based antivirus warnings on some Windows systems. Phase 40 uses no obfuscation or executable packing tricks to work around reputation systems; document and code-sign release artifacts when a certificate is available.

## Packaged self-check

The compiled runtime accepts:

```text
MMO Video Studio.exe --phase40-self-check <report.json>
```

The self-check validates the packaged QML/language/icon/notices, resolves bundled FFmpeg/FFprobe, performs a tiny `libx264` MP4 render and probes it, and verifies managed writable application data can be created. It writes only a local JSON result and removes its temporary render.

## Fresh profile / No-Python verification

`verify_windows_build.ps1` copies the standalone folder out of the source checkout into a temporary **Program Files-like path containing spaces and Khmer Unicode**, replaces `LOCALAPPDATA` with a clean temporary profile, removes developer Python from `PATH`, then executes the compiled self-check. This proves the self-check does not depend on a source checkout or separately installed Python.

It then launches the GUI for a short QML/startup smoke and fails if the process exits unexpectedly. For the mandatory visual workflow acceptance, run with `-RequireInteractiveAcceptance` and complete Home → project create → tiny media import/preview → overlay text → FFmpeg export → close/reopen → Diagnostics.

## Windows release procedure

1. Use Windows 11 x64 under a non-admin user where practical.
2. Install CPython 3.11 x64 and Visual Studio 2022 C++ Build Tools on the **build** machine.
3. Stage the reviewed FFmpeg files described in `packaging/windows/FFMPEG_STAGING.md`.
4. Run `scripts/build_windows.ps1 -Mode Release -FFmpegDir <folder>`.
5. Run `scripts/verify_windows_build.ps1 -DistDir 'dist\MMO Video Studio' -RequireInteractiveAcceptance`.
6. Repeat acceptance with Windows display scaling relevant to release QA and, when available, on both no-CUDA and CUDA-capable systems.
7. Archive the generated `build-manifest.json` with the release artifact.

## Current execution limitation

The Phase 40 implementation was authored/tested in a Linux sandbox that does not contain PySide6, Nuitka, Windows, Visual Studio Build Tools, or a redistributable Windows FFmpeg binary. Therefore this environment can validate the packaging configuration, Python helpers, resource contracts, build/verification scripts and source-level regressions, but **cannot truthfully claim that a Windows EXE or the mandatory Fresh profile / No-Python GUI acceptance was executed here**. Those gates are intentionally implemented in the Windows verifier and must be run on Windows 11 before calling a release artifact verified.

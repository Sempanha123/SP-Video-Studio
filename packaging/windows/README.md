# Phase 40 Windows packaging

Target: **Windows 11 x64**, **CPython 3.11**, **Nuitka standalone one-folder**.

The one-folder layout is intentionally preferred over one-file for Qt/QML, FFmpeg and optional AI native libraries. Large AI model weights remain in `%LOCALAPPDATA%/MMOVideoStudio/models` and are never embedded in the EXE.

## Reproducible build

```powershell
py -3.11 -V
$env:MMOVS_FFMPEG_DIR = 'C:\build-inputs\ffmpeg'
.\scripts\build_windows.ps1 -Mode Release
```

Development and debug/log-friendly modes are also available:

```powershell
.\scripts\build_windows.ps1 -Mode Development -FFmpegDir C:\build-inputs\ffmpeg
.\scripts\build_windows.ps1 -Mode Debug -FFmpegDir C:\build-inputs\ffmpeg
```

`build_windows.ps1` creates its own `.build/windows-py311` virtual environment, installs dependencies under `constraints-win311.txt`, compiles with Nuitka, copies only the controlled runtime resources/FFmpeg inputs, writes `build-manifest.json`, scans/verifies the result, and optionally signs the EXE when signing configuration is provided.

The default PyTorch installation is the CPU wheel channel. This keeps the base release functional without CUDA and avoids bundling an NVIDIA driver stack. A separately reviewed CUDA-oriented build may override `-TorchIndexUrl`; a user still needs a compatible NVIDIA driver, and the build script never embeds signing or driver secrets.

See `docs/PHASE40_WINDOWS_PACKAGING.md` for the audit and release procedure.


## Phase 41 installer

After the Phase 40 standalone folder passes `verify_windows_build.ps1`, build the per-user consumer installer with:

```powershell
.\scripts\build_windows_installer.ps1 -DistDir '.\dist\MMO Video Studio'
```

The installer uses Inno Setup 7.1.0 x64, keeps mutable data under `%LOCALAPPDATA%\MMOVideoStudio`, emits a SHA-256 sidecar, and reuses the Phase 40 external signing inputs when configured. See `packaging/windows/installer/README.md`.


Phase 41 installer compilation intentionally does not run destructive/fresh-profile acceptance by default. After building, move the Setup EXE and `.sha256` sidecar to a disposable clean Windows 11 x64 profile/VM and run `scripts\verify_windows_installer.ps1`. Use `-RunNativeVerify` on the build command only when the build environment itself is that clean QA profile.

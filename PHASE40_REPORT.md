# PHASE 40 STATUS

**Implementation complete — native Windows artifact verification pending on Windows 11 x64.**

Baseline: GitHub `main` commit `8da15fbab3612fcc9caff4f2a771094c4fa7006c` (`test: add release-grade end-to-end QA suite`). The sandbox does not contain a local `.git` checkout, so a literal local `git status` could not be produced; the pushed Phase 39 commit is the authoritative clean baseline.

## Completed:

- Added a reproducible Windows 11 x64 standalone one-folder packaging architecture without replacing the existing application bootstrap.
- Added Development, Release and Debug Windows build modes.
- Added build-time FFmpeg/FFprobe staging with explicit bundled runtime resolution; no runtime download path was introduced.
- Added packaged application/resource-root resolution so the compiled application does not depend on the source checkout.
- Kept writable models/cache/recovery/assets/logs/settings/downloads/database under the existing `%LOCALAPPDATA%\MMOVideoStudio` boundary.
- Added centralized Windows build constraints, resource/QML inclusion, selective Qt plugin validation, application icon/version metadata, build manifest generation, secret/development-file scanning, optional signing preparation and native verification scripts.
- Kept AI model weights outside the application package; Model Manager remains authoritative for model installation.
- Added a compiled backend self-check for resources, bundled FFmpeg/FFprobe and a tiny `libx264`/MP4 probe.
- Fixed a packaging-script integration bug found by the new tests: direct execution of `scripts/generate_build_manifest.py` now anchors imports to the repository root instead of assuming the package was already installed.
- Made the existing `APP_VERSION` the single version source for package metadata, diagnostics/environment reporting and migration history.
- Made Release logging safe when Windows GUI mode has no console/stderr; rotating managed file logs remain authoritative.
- Added/updated Phase 40 packaging tests and retained the Phase 37 security, Phase 38 migration and Phase 39 release QA gates.

## Packaging architecture:

- Target: Windows 11 x64.
- Layout: Nuitka standalone **one-folder**, not one-file.
- Entrypoint: `main.py` → `app.phase40_runtime:run` → existing Phase 38 runtime/application architecture.
- Expected release output: `dist\MMO Video Studio\MMO Video Studio.exe` plus Qt/Python/native runtime files, `ui\qml`, `resources`, `bin\ffmpeg.exe`, `bin\ffprobe.exe`, `licenses`, and `build-manifest.json`.
- Source mode keeps its existing PATH/custom FFmpeg behavior; packaged mode checks the controlled application `bin` directory before PATH.
- No installer is introduced in this phase.

## Build Python:

- Required production build interpreter: **64-bit CPython 3.11**.
- `scripts/build_windows.ps1` creates an isolated `.build\phase40-windows\py311` virtual environment and rejects another Python major/minor or non-x64 interpreter.
- The project itself remains `>=3.11,<3.15`; Phase 40 deliberately does not move the packaged AI stack to Python 3.14.

## PySide6/Nuitka:

- Pinned packaging baseline: **PySide6 6.11.2** and **Nuitka 4.2.1** in `packaging/windows/constraints-win311.txt`.
- Nuitka uses `--mode=standalone`, the `pyside6` plugin and QML plugin inclusion.
- Windows compilation is configured for the current MSVC toolchain via `--msvc=latest`.
- The Linux patch sandbox does not have PySide6/Nuitka/MSVC installed, so a native Windows compilation was not claimed here.

## QML packaging:

- `ui/qml` is explicitly included as read-only package data.
- The build keeps the current shared QML architecture; no business logic was moved into QML.
- Phase 40 contracts cover Main, Home/Create/Projects/Workspace, Video/News/Story/Dub/Shorts workflow surfaces, Voices, Templates, Assets, Batch, Models, Settings, Diagnostics, onboarding, theme and shared components.
- In the partial sandbox overlay, one full-tree assertion is skipped because not every repository QML file is mounted. On a normal full checkout, that test becomes mandatory and fails when required pages are missing.

## Qt plugins:

- The PySide6 Nuitka plugin remains responsible for its sensible Qt plugin set, with QML explicitly requested.
- `packaging/windows/build_config.json` records the required families: QML, Windows platform, image formats and multimedia.
- `verify_windows_build.ps1` rejects a dist missing `qwindows.dll`, Qt QML runtime, an image-format plugin family or a multimedia backend.
- Qt network/TLS plugins are not copied blindly because the current online features use the Python networking stack rather than Qt networking.

## FFmpeg strategy:

- Selected strategy: **bundle reviewed FFmpeg/FFprobe binaries at build time**.
- Builder input must contain `ffmpeg.exe`, `ffprobe.exe`, `LICENSE.txt`, and `SOURCE.txt`.
- The application never downloads FFmpeg silently at runtime.
- Packaged auto-discovery checks `<application>\bin\ffmpeg.exe` / `ffprobe.exe`; custom-path behavior remains available and source/developer PATH fallback remains intact.
- The exact staged FFmpeg build/license/source obligations must be reviewed for the chosen redistribution build. Phase 40 documents this requirement and does not make a legal conclusion.

## AI dependency packaging:

- Release builds can include runtime packages needed after model installation: `torch`, `faster_whisper`, `ctranslate2`, `voxcpm`, `transformers`, `sentencepiece`, and `soundfile`.
- The build performs an import smoke for those packages before compilation when AI runtime inclusion is enabled.
- Native packages are explicitly included rather than depending on accidental dynamic discovery.
- No AI model weight is embedded in the EXE/folder.

## Model strategy:

- Models remain external under `%LOCALAPPDATA%\MMOVideoStudio\models`.
- Existing Model Manager download/verification/storage behavior remains authoritative.
- A packaged install with no models remains usable for manual/offline workflows and the Models page must open without crashing.

## CUDA/CPU behavior:

- Base packaging uses the official CPU PyTorch wheel channel so the application remains installable/runnable without CUDA and does not bundle an NVIDIA driver stack.
- GPU/CUDA builds require a separately reviewed dependency/DLL matrix and compatible driver; `-TorchIndexUrl` is an explicit build input rather than an embedded driver solution.
- Existing runtime readiness/capability checks remain authoritative.
- Real VoxCPM2/Whisper/translation model inference was not run in this sandbox; optional model smoke remains capability-dependent.

## Writable app-data paths:

- Existing `AppPaths` remains authoritative.
- On Windows, managed mutable data stays under `%LOCALAPPDATA%\MMOVideoStudio` for models, cache, recovery, assets, logs, settings, downloads, managed voices/templates, exports metadata and application data/database.
- Project folders remain in the user-configured project root (existing default under Documents), not Program Files.
- Native verification overrides `LOCALAPPDATA` to an isolated fresh profile and checks that packaged self-check writes only beneath it.

## Resources:

- Bundled read-only resources include `ui/qml`, current `resources` (language registry, icons, built-in template/subtitle/export/news/voice static resources) and packaging license notices.
- Runtime resource discovery uses the executable directory in packaged mode and the repository root in source mode.
- Tests validate the central language resource, QML Main, icon and notice contracts.

## Fonts:

- Phase 40 adds **no font files**.
- English/Khmer/Thai/Vietnamese and other languages continue to use the existing Language Registry system-font fallback lists.
- A font binary must not be added to distribution until redistribution rights for that exact font are confirmed.

## Version metadata:

- `app.constants.APP_VERSION` remains the authoritative application version: **0.1.0** for this baseline.
- `pyproject.toml` now reads package version dynamically from that constant.
- Diagnostics/environment reporting, migration history, build manifest and Windows EXE metadata use the same version source.
- Nuitka build metadata includes product `MMO Video Studio`, organization/company label `SP Video Studio`, file description, file/product version and copyright label.
- Wheel metadata smoke produced `sp-video-studio 0.1.0` from the centralized version.

## Application icon:

- Added `resources/icons/app.ico` with 16, 20, 24, 32, 40, 48, 64, 128 and 256 pixel entries.
- Nuitka receives it through `--windows-icon-from-ico` for the executable.
- Packaged runtime also passes Qt's standard `-qwindowicon` argument so the application window uses the same icon.

## Build scripts:

- `scripts/build_windows.ps1` — reproducible Development/Release/Debug standalone build, dependency/import checks, FFmpeg staging, manifest generation, optional signing and verification.
- `scripts/verify_windows_build.ps1` — resource/plugin/secret scan plus clean-profile, Unicode/path-with-spaces, stripped-PATH no-Python self-check, GUI launch smoke and optional interactive acceptance.
- `scripts/generate_build_manifest.py` — records non-secret build/runtime metadata.
- No undocumented GUI build clicks are required.

## Build manifest:

- A successful Windows build generates `dist\MMO Video Studio\build-manifest.json`.
- It contains schema version, product/app version, commit when available, UTC build time, build mode, Windows target/architecture, Python implementation/version, PySide6/Nuitka versions, FFmpeg version/source marker, layout, model-bundling flag, runtime data root and console mode.
- It deliberately contains no signing secret, API key or personal user data.
- A direct manifest-generation smoke was executed successfully in the sandbox after fixing the source-checkout import path.

## Secret scan:

- Native verifier rejects `.env`, `.env.local`, `.env.production`, `.git`, `tests`, `test-results`, `.pytest_cache`, private-key/certificate containers and obvious credential assignments in packaged text/config files.
- Signing uses an externally configured certificate thumbprint; no signing certificate/private key/password is stored in the repository.
- Phase 37 security tests remain part of the release regression gate.

## New files:

- `PHASE40_REPORT.md`
- `app/packaging_self_check.py`
- `app/phase40_runtime.py`
- `app/runtime_paths.py`
- `docs/PHASE40_WINDOWS_PACKAGING.md`
- `packaging/windows/FFMPEG_STAGING.md`
- `packaging/windows/README.md`
- `packaging/windows/build_config.json`
- `packaging/windows/constraints-win311.txt`
- `packaging/windows/notices/THIRD_PARTY_NOTICES.md`
- `resources/icons/app.ico`
- `scripts/build_windows.ps1`
- `scripts/generate_build_manifest.py`
- `scripts/verify_windows_build.ps1`
- `tests/test_phase40_packaging.py`

## Modified files:

- `README.md`
- `app/constants.py`
- `app/logging_setup.py`
- `docs/known-issues.md`
- `main.py`
- `media/ffmpeg_locator.py`
- `pyproject.toml`
- `services/diagnostics_service.py`
- `services/environment_report_service.py`
- `services/project_migration_service.py`
- `tests/test_phase38_migrations.py`
- `tests/test_phase39_packaging.py`

## Packaged smoke tests:

Source/config package contracts in this environment:

```text
python -m pytest -q tests/test_phase40_packaging.py
31 passed, 1 skipped
```

Combined Phase 39 + Phase 40 `PACKAGING_SMOKE` profile:

```text
36 passed, 1 skipped, 220 deselected
```

The single Phase 40 skip is caused only by this partial sandbox QML overlay; the full repository checkout is required for the complete page-presence assertion.

Full available release profile after Phase 40:

```text
247 passed, 7 skipped, 3 deselected, 0 failed
```

The seven skips are environment/source-availability checks already documented by Phase 39/40: partial WorkerPool/thumbnail/QML source in this overlay, missing `qmllint`, Windows-only filesystem acceptance, and the full-QML Phase 40 assertion.

## Fresh-machine/profile test:

- **Not executed natively in this Linux sandbox.**
- Implemented in `verify_windows_build.ps1`: copy the compiled dist outside the source tree to a Program-Files-like Unicode/path-with-spaces location, use a fresh temporary `LOCALAPPDATA`, run the packaged backend self-check, launch the GUI, and optionally require manual Home/project/import/preview/text/export/reopen/Diagnostics/Models acceptance.
- This Windows-native gate is required before a Phase 40 binary is described as release-verified.

## No-Python test:

- **Not executed against a Windows EXE in this Linux sandbox.**
- The verifier strips `PATH` to Windows/System32 + Windows root before invoking the compiled EXE's `--phase40-self-check`, so it cannot succeed by finding a developer Python/FFmpeg on PATH.
- Static/source tests validate that this flow is present and uses the packaged resource/FFmpeg paths.

## FFmpeg render test:

- Source-side Phase 40 packaging self-check passed with installed FFmpeg 7.1.5 using a tiny `libx264`/`yuv420p` MP4 and FFprobe validation.
- Phase 39 release E2E render regressions also remain green.
- The required **bundled Windows FFmpeg executable** render is implemented in `verify_windows_build.ps1` but was not executable in this Linux environment.

## Optional AI smoke:

- Standard packaging does not download/load huge models.
- Build script performs no-model imports for the selected AI runtime packages on the Windows build environment.
- `verify_windows_build.ps1 -RequireInteractiveAcceptance` checks the Models page without installed models.
- Real installed-model VoxCPM2/Whisper/translation inference remains optional and was not run in this sandbox.

## Known packaging issues:

- **P0/P1:** none found by available automated Phase 37–40 gates.
- **P2:** native Windows 11 x64 standalone build, QML startup, fresh-profile/no-Python and interactive acceptance still require execution on the actual Windows build/release workstation (`QA-40-001`).
- **P3:** unsigned Nuitka binaries may receive SmartScreen/antivirus reputation warnings until release signing is configured (`QA-40-002`).
- PySide6, Nuitka, MSVC and a redistributable Windows FFmpeg build are not installed in this Linux sandbox, therefore no fake Windows EXE/dist is included in the Phase 40 patch archive.

## Build output:

Expected native Windows build output after running `scripts/build_windows.ps1 -Mode Release -FFmpegDir <reviewed-folder>`:

```text
dist\MMO Video Studio\
  MMO Video Studio.exe
  build-manifest.json
  bin\ffmpeg.exe
  bin\ffprobe.exe
  ui\qml\...
  resources\...
  licenses\THIRD_PARTY_NOTICES.md
  licenses\ffmpeg\LICENSE.txt
  licenses\ffmpeg\SOURCE.txt
  <Nuitka/PySide6/Qt/native runtime files>
```

The Phase 40 handoff ZIP contains source/configuration/tests only. It intentionally does **not** contain a fabricated Windows executable, third-party FFmpeg binary or model weights.

## Architecture decisions:

- Prefer one-folder + future installer over fragile one-file extraction for a Qt/QML + FFmpeg + AI-native application.
- Extend the existing runtime and `AppPaths`; do not create a second persistence/resource system.
- Keep model weights external while packaging the required Python/native runtimes separately.
- Bundle FFmpeg only from an explicitly staged/reviewed build and preserve its exact license/source notices.
- Keep Release console disabled but file logging always available.
- Use one central application version instead of synchronizing literals manually.
- Validate the resulting folder rather than blindly copying every Qt plugin.
- Keep signing credentials external; support signing when configured but do not block Phase 40 source implementation on a certificate.
- Treat native Windows clean-profile/no-Python acceptance as an artifact gate that cannot be substituted by Linux static tests.

## Recommended next phase:

**Phase 41 — Windows Installer** — only after the native Phase 40 Windows build/verification gate has passed on Windows 11 x64.

## Suggested Git commit:

```text
build: package standalone Windows MMO Video Studio application
```

Do not automatically begin Phase 41.

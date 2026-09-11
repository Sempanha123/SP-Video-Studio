# PHASE 3 STATUS

## Completed:

- Versioned persistent settings system
- Restart-safe theme, language, project path, performance, rendering, and advanced preferences
- Safe settings reset without deleting projects/models
- Background system readiness checks with cached session results
- Compact Home readiness summary and detailed Settings → Performance view
- Recognized historical project-root support after changing the default project folder

## Settings implemented:

- General: English/Khmer metadata, startup preferences
- Appearance: System / Light / Dark with immediate + persistent switching
- Projects: configurable default folder for new projects only
- Performance: Auto / Low Memory / Balanced / Maximum Quality
- Rendering: 24/25/30/50/60 FPS, 9:16/16:9/1:1, Auto encoder
- Storage: managed path display + Open Folder
- Advanced: debug logging, technical-detail preference, readiness-on-startup, Reset Settings
- `settings_version = 1`
- Atomic `settings.json` writes and invalid-file quarantine

## System detection:

- OS name/version/architecture
- CPU identity where available
- Physical/logical CPU cores
- Total/available RAM
- Best-effort GPU identity
- Readiness cached in the controller for the current session
- External readiness commands executed through WorkerPool

## FFmpeg detection:

- Central `FFmpegLocator`
- Auto detection through PATH
- Validated custom FFmpeg path
- FFprobe sibling/PATH discovery
- `-version` validation with timeout, captured output, and `shell=False`
- Custom validation runs outside the UI thread
- No automatic FFmpeg downloads

## GPU/CUDA detection:

- NVIDIA detection via `nvidia-smi` when available
- NVIDIA VRAM total/free where available
- Windows generic GPU-name fallback
- Vendor classification for NVIDIA / AMD / Intel / Unknown
- CUDA Available / Possibly Available / Unavailable / Unknown semantics
- Optional PyTorch signal used only if PyTorch already exists
- Detection failures degrade to Unknown without crashing

## Storage detection:

- Application Data
- Projects
- Models
- Temporary
- Free/total disk-space reporting
- Warning below 10 GB
- Critical below 3 GB
- Runtime folders created safely at startup

## Home readiness:

- Overall readiness badge
- GPU summary
- CUDA status
- FFmpeg state
- Project/storage free-space summary
- AI model install summary
- View Details and Recheck actions

## New files:

- `domain/settings.py`
- `domain/system_readiness.py`
- `storage/repositories/settings_repository.py`
- `services/settings_service.py`
- `services/system_readiness_service.py`
- `media/ffmpeg_locator.py`
- `ui/controllers/settings_controller.py`
- `ui/controllers/readiness_controller.py`
- `ui/qml/components/SettingsSection.qml`
- `ui/qml/components/SettingsRow.qml`
- `ui/qml/components/PathSelector.qml`
- `ui/qml/components/RadioCard.qml`
- `ui/qml/components/InfoBanner.qml`
- `ui/qml/components/ReadinessItem.qml`
- `tests/test_settings.py`
- `tests/test_ffmpeg_locator.py`
- `tests/test_system_readiness.py`
- `PHASE3_REPORT.md`

## Modified files:

- `app/bootstrap.py`
- `app/paths.py`
- `pyproject.toml`
- `services/project_service.py`
- `storage/repositories/__init__.py`
- `ui/qml/Main.qml`
- `ui/qml/components/StatusBadge.qml`
- `ui/qml/pages/HomePage.qml`
- `ui/qml/pages/SettingsPage.qml`
- `tests/test_project_system.py`
- `tests/test_qml_structure.py`
- `README.md`

## Tests run:

- `python -m compileall -q app domain media services storage workers`
- `pytest -q`
- 52 passed
- 1 skipped because PySide6 is unavailable in this packaging sandbox
- `git diff --check` passed

## Manual checks:

- Previous Phase 0/1/2 tests remain green
- Settings serialization/restart behavior exercised with temporary paths
- Invalid settings restore defaults without deleting other runtime data
- FFmpeg detected/missing/invalid cases are mocked and verified
- CPU/RAM, GPU fallback, CUDA uncertainty, and storage thresholds verified
- Existing project remains safely deletable after default-root change and restart
- Backend container/settings/database/project integration smoke passed with temporary runtime paths
- QML Phase 3 routes/components statically checked
- Live Qt window launch could not be executed in this sandbox because PySide6 is unavailable

## Restart persistence test:

- Passed in automated tests for theme, performance profile, language, and custom projects folder.
- Project persistence remains restart-safe.

## Known issues:

- Live QML runtime smoke test remains skipped in this sandbox because PySide6 is not installed. It will run in the target Python 3.11/PySide6 environment.
- GPU/CUDA data is hardware/driver dependent and may correctly show Unknown.
- AI models remain Not Installed unless expected model folders contain files; installation belongs to a later phase.

## Architecture decisions:

- Settings use versioned atomic JSON, while project library data remains in SQLite.
- QML accesses settings/readiness only through Qt controllers.
- Readiness uses a structured domain model and best-effort detection.
- External detection processes never run from QML and are dispatched through WorkerPool.
- Missing AI models are warnings; missing FFmpeg/FFprobe produces Setup Required for future media operations.
- Changing default project storage does not move existing projects.
- ProjectService tracks recognized historical roots so safe deletion remains possible after path changes/restarts without allowing arbitrary outside folders.

## Recommended next phase:
Phase 4 — Media Import + Media Library

## Suggested Git commit:
`feat: add settings persistence and system readiness detection`

# SP Video Studio

SP Video Studio is a native Windows desktop video-creation application built with Python 3.11, PySide6, Qt Quick, and QML.

## Current milestone

Phase 0 foundation + Phase 1 application shell + Phase 2 persistent projects + **Phase 3 settings and system readiness**.

Implemented now:

- Production-oriented Python package structure and rotating logging
- Native QML shell with persistent Light / Dark / System theme
- Versioned user settings with safe atomic JSON writes
- Configurable default projects folder for newly created projects
- Auto / Low Memory / Balanced / Maximum Quality performance profiles
- Rendering defaults for FPS, aspect ratio, and Auto encoder preference
- SQLite application database with ordered migrations
- Create, open, rename, duplicate, remove-from-library, and safe delete project operations
- Recent Projects on Home and a project workspace placeholder
- Background system readiness checks with session caching
- CPU, RAM, OS, architecture, GPU, CUDA, disk-space, model-folder, FFmpeg, and FFprobe readiness reporting
- Auto-detected or validated custom FFmpeg configuration
- Compact Home readiness summary and detailed Settings → Performance panel
- English (`en`) and Khmer (`km`) settings/project metadata architecture

Not implemented yet: media import, AI inference, VoxCPM2 inference, Whisper inference, translation processing, video rendering, model downloads, timeline editing, News research, Story generation, or batch rendering.

## Requirements

- Windows 10/11 recommended
- Python 3.11
- PySide6 6.8+
- psutil 6.1+

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Run

```powershell
python main.py
```

## Test

```powershell
pytest
```

## Runtime data

Application-managed data lives outside the source repository. On Windows the base folder is:

```text
%LOCALAPPDATA%\MMOVideoStudio\
```

Important runtime locations:

```text
data\app.db
settings\settings.json
models\
cache\
temp\
logs\
downloads\
exports\
```

`AppPaths` owns runtime path discovery and startup directory creation. Critical database paths are not casually user-editable.

## Settings architecture

Settings follow the same layered architecture as projects:

```text
QML
  ↓
SettingsController
  ↓
SettingsService
  ↓
SettingsRepository
  ↓
settings/settings.json
```

`settings.json` uses `settings_version = 1` so later settings migrations can be introduced without assuming the schema is permanent. Writes use the shared atomic JSON writer. Invalid settings are preserved as an `.invalid*` file and safe defaults are restored instead of crashing startup.

Current settings categories:

- General: language and startup preferences
- Appearance: System / Light / Dark theme
- Projects: default folder for new projects
- Performance: profile selection and system readiness
- Rendering: default FPS, aspect ratio, Auto encoder preference
- Storage: managed runtime folders and Open Folder actions
- Advanced: debug logging, technical details preference, startup readiness check, Reset Settings

Reset Settings does **not** delete the project database, project files, media, or AI models.

## Performance profiles

The profile is stored as a stable enum value rather than UI text:

- **Auto** — adapt later engines to detected hardware
- **Low Memory** — lower memory use, caching, and concurrency
- **Balanced** — moderate caching/concurrency with normal quality
- **Maximum Quality** — prefer highest configured quality when hardware permits

Phase 3 stores policy guidance only. It does not load AI models or start media rendering.

## System readiness

`SystemReadinessService` performs best-effort detection and returns a structured `SystemReadiness` model. External commands run through the background worker pool, so QML rendering is not blocked.

Readiness includes:

- OS name/version and architecture
- CPU name, physical cores, logical cores
- total and available RAM
- GPU identity/vendor and NVIDIA VRAM where available
- CUDA state: Available / Possibly Available / Unavailable / Unknown
- FFmpeg and FFprobe availability, path, and version
- application/project/model/temp disk space
- VoxCPM2 and faster-whisper install-folder status
- overall Ready / Ready with Warnings / Setup Required state

Hardware detection is intentionally best-effort. Missing command-line tools, unavailable drivers, unsupported APIs, or absent optional Python libraries are reported as Unknown/Detection unavailable rather than causing an application failure.

### GPU and CUDA interpretation

NVIDIA detection uses `nvidia-smi` when present, with timeouts and structured subprocess arguments. On Windows a lightweight video-controller identity fallback is attempted. AMD and Intel GPUs are reported as detected hardware without claiming future AI acceleration support.

If PyTorch already exists, its CUDA availability can confirm **Available**. PyTorch is never installed just for readiness detection. An NVIDIA driver/tool signal without a confirming runtime is represented as **Possibly Available** rather than falsely claiming CUDA is ready.

## FFmpeg discovery

`media/ffmpeg_locator.py` centralizes FFmpeg/FFprobe discovery.

Order:

1. validated custom path when the user selected one
2. sibling FFprobe beside a selected FFmpeg where available
3. environment `PATH`

Each executable is validated by invoking `-version` with a timeout, captured output, and `shell=False`. Phase 3 never downloads FFmpeg automatically. Custom validation runs through the worker pool before a path is persisted.

## Application database

The application database is:

```text
%LOCALAPPDATA%\MMOVideoStudio\data\app.db
```

`storage/database.py` owns connection setup and migration execution. SQL access for projects is isolated in `storage/repositories/project_repository.py`; QML never talks directly to SQLite.

`schema_migrations` records each applied migration version and timestamp. Ordered Python migrations are applied once inside SQLite transactions; the app never deletes/recreates the database to upgrade schema.

## Project location

Default:

```text
Documents\SP Video Studio\Projects\
```

Settings → Projects can change the default used by **new** projects. Existing projects remain in their original locations. ProjectService preserves recognized historical roots so an existing project remains openable/deletable safely after changing the default folder or restarting the app.

Each project uses a stable UUID-backed folder and portable `project.json` metadata. Physical project folders do not rename when the display title changes.

## Architecture

```text
QML
  ├── ProjectController → ProjectService → ProjectRepository → SQLite
  ├── SettingsController → SettingsService → SettingsRepository → JSON
  └── ReadinessController → WorkerPool → SystemReadinessService
                                      ├── FFmpegLocator
                                      ├── OS / CPU / RAM
                                      ├── GPU / CUDA
                                      ├── model-folder checks
                                      └── disk-space checks
```

Heavy future AI/media work must remain outside the UI thread and use the existing worker/job abstractions.

## Phase discipline

Phase 3 is intentionally limited to settings persistence and environment readiness. The next phase is **Phase 4 — Media Import + Media Library**.

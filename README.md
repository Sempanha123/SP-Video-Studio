# SP Video Studio

SP Video Studio is a native Windows desktop video-creation application built with Python 3.11, PySide6, Qt Quick, and QML.

## Current milestone

Phase 0 foundation + Phase 1 application shell + **Phase 2 persistent project system**.

Implemented now:

- Production-oriented Python package structure and rotating logging
- Native QML application shell with light/dark/system theme support
- Home, Create, Projects, Batch, Voices, Templates, Assets, Models, and Settings pages
- SQLite application database with ordered migrations
- Persistent project repository and service layers
- Create, open, rename, duplicate, remove-from-library, and safe delete operations
- Recent Projects on Home
- Project workspace placeholder for future editing phases
- Atomic `project.json` metadata writes
- UUID-backed project identity and safe project folder names
- English (`en`) and Khmer (`km`) project language metadata
- 9:16, 16:9, and 1:1 aspect ratios; 24/25/30/50/60 FPS
- Restart-safe project persistence

Not implemented yet: AI inference, VoxCPM2, Whisper, translation processing, media importing, FFmpeg rendering, model downloads, timeline editing, News research, Story generation, or batch rendering.

## Requirements

- Windows 10/11 recommended
- Python 3.11

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

## Application database

The application database lives outside the source repository.

On Windows:

```text
%LOCALAPPDATA%\MMOVideoStudio\data\app.db
```

`storage/database.py` owns connection setup and migration execution. SQL access for projects is isolated in `storage/repositories/project_repository.py`; QML never talks directly to SQLite.

### Migration strategy

`schema_migrations` records each applied migration version and timestamp. Ordered Python migration modules live in `storage/migrations/`. Missing migrations are applied once, inside SQLite transactions. The app never deletes/recreates the database to upgrade schema.

## Project location

The current default project root is platform-derived from the current user's home directory:

```text
Documents\SP Video Studio\Projects\
```

The path is supplied through the application path/config layer so a later Settings phase can make it user-configurable without changing project services.

## Project folder structure

Each project gets a stable UUID and a safe folder name such as:

```text
my-news-project_a1b2c3d4\
├── project.json
├── media\
├── audio\
├── subtitles\
├── generated\
├── thumbnails\
├── renders\
└── cache\
```

Renaming a project changes only its display title; the physical folder and project ID remain stable.

`project.json` is intentionally small. It contains portable identity/version/basic metadata for validation and quick inspection. The application database remains the library index, and the service keeps both representations synchronized.

## Project lifecycle

The UI calls the QML-facing `ProjectController`, which calls `ProjectService`. `ProjectService` coordinates repository operations, filesystem changes, atomic metadata writes, project validation, and safe cleanup.

Typical create flow:

1. Validate workflow, title, language, aspect ratio, FPS, and writable project root.
2. Generate a UUID.
3. Create the standard project folder structure.
4. Atomically write `project.json`.
5. Insert the SQLite record.
6. Refresh Projects/Recent Projects and open the workspace placeholder.

Delete is restricted to recognized projects beneath the configured project root. A valid matching `project.json` is required before destructive deletion. Missing folders are not automatically removed from the library; the UI offers a separate **Remove from Library** action.

## Architecture

The repository separates UI, configuration, domain models, engines, workers, services, storage, workflows, media helpers, and rendering concerns. Heavy future AI/media operations must stay outside the UI thread.

Phase 2 persistence path:

```text
QML
  ↓
ProjectController
  ↓
ProjectService
  ├── ProjectRepository → SQLiteDatabase
  └── project filesystem / project.json
```

## Phase discipline

Phase 2 is intentionally limited to durable project persistence. Phase 3 is reserved for Settings + System Readiness.

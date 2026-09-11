# SP Video Studio

SP Video Studio is a native Windows desktop video-creation application built with Python 3.11, PySide6, Qt Quick, and QML.

## Current milestone

Phase 0 foundation + Phase 1 design system and application shell.

Implemented now:

- Production-oriented Python package structure
- Application path management outside the repository
- Rotating logging
- Dependency container
- Core domain models and engine interfaces
- Worker/job abstractions
- Native QML application shell
- Centralized light/dark/system design system
- Home, Create, Projects, Batch, Voices, Templates, Assets, Models, and Settings pages
- Reusable desktop UI components
- Theme switching in the current session
- pytest coverage for foundation code and a QML launch smoke test when PySide6 is available

Not implemented yet: AI inference, VoxCPM2 integration, Whisper integration, FFmpeg processing, project persistence, real media importing, model downloads, timeline editing, or rendering.

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

## Architecture

The repository separates UI, application configuration, domain models, engines, workers, services, storage, workflows, media helpers, and rendering concerns. QML contains presentation and local visual state only. Future AI engines plug into stable Python interfaces and expensive operations must run outside the UI thread.

Runtime data is stored under `%LOCALAPPDATA%/MMOVideoStudio/` on Windows rather than inside the repository.

## Phase discipline

Each future phase should extend the existing architecture without rewriting unrelated working code. Phase 2 is reserved for the Database + Project System.

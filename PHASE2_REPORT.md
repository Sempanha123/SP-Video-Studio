# PHASE 2 STATUS

## Completed:

- Persistent SQLite project library
- Real Create Project form and workflow defaults
- Project folder creation and portable `project.json`
- Projects list and Home Recent Projects
- Open/reopen project workspace placeholder
- Rename, duplicate, delete, and remove-missing-entry flows
- Atomic metadata writes and filesystem/DB failure cleanup
- Stable UUID project identity
- English/Khmer project metadata
- Safe path validation for destructive deletion

## Database:

- `%LOCALAPPDATA%/MMOVideoStudio/data/app.db` on Windows
- Centralized `SQLiteDatabase`
- `projects` table with focused indexes for activity, workflow, and status
- No SQL in QML

## Migrations:

- `schema_migrations` version table
- Ordered Python migration registry
- Migration 001 creates the project table/indexes
- Transactional, idempotent migration startup

## Project operations:

- Create
- List / recent list
- Open and update `last_opened_at`
- Rename without renaming the physical project folder
- Duplicate into a new project ID/folder while excluding cache
- Confirmed safe deletion under the configured project root
- Remove missing project entry from library without deleting arbitrary files

## New files:

- `storage/json_writer.py`
- `storage/migrations/__init__.py`
- `storage/migrations/m001_create_projects.py`
- `storage/repositories/project_repository.py`
- `ui/controllers/__init__.py`
- `ui/controllers/project_controller.py`
- `ui/qml/components/ProjectCard.qml`
- `ui/qml/components/RecentProjectCard.qml`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- `resources/icons/back.svg`
- `resources/icons/copy.svg`
- `resources/icons/edit.svg`
- `resources/icons/open.svg`
- `resources/icons/trash.svg`
- `tests/test_database.py`
- `tests/test_project_metadata.py`
- `tests/test_project_system.py`

## Modified files:

- `app/bootstrap.py`
- `app/config.py`
- `app/paths.py`
- `domain/project.py`
- `services/project_service.py`
- `storage/database.py`
- `storage/repositories/__init__.py`
- `ui/qml/Main.qml`
- `ui/qml/components/AppButton.qml`
- `ui/qml/pages/CreatePage.qml`
- `ui/qml/pages/HomePage.qml`
- `ui/qml/pages/ProjectsPage.qml`
- `tests/test_qml_structure.py`
- `README.md`

## Tests run:

- `python -m pytest -q`
- 28 passed
- 1 skipped because PySide6 is not installed in the packaging sandbox
- `python -m compileall` passed for Python modules
- Persistence restart is covered with a temporary database/project root
- Full create/open/rename/duplicate/delete/restart backend smoke flow passed

## Manual checks:

- Backend lifecycle exercised with temporary storage only
- Project creation produces the expected standard folder structure
- Rename preserves project identity/path
- Duplicate creates an independent folder and metadata
- Delete removes only validated projects under the configured root
- QML routes/components were statically checked by tests
- Live Qt window launch could not be performed in this sandbox because PySide6 is unavailable

## Persistence restart test:

- Passed in automated tests: database/service recreated from the same temporary `app.db`, saved project was listed and reopened successfully.

## Known issues:

- Live QML runtime smoke test is skipped in this sandbox because PySide6 is unavailable. It remains in the project and will run on the target Python 3.11/PySide6 environment.
- No Phase 3 settings persistence or project-root picker yet by design.

## Architecture decisions:

- SQLite is the application library index; `project.json` provides portable/versioned project identity metadata.
- Project titles are never used as identity.
- Physical project folders do not rename when display titles change.
- Project deletion requires both root-boundary validation and matching `project.json` identity.
- QML uses a Qt `ProjectController`; database/repository objects are never exposed to QML.
- Atomic metadata replacement reduces corruption risk.

## Recommended next phase:
Phase 3 — Settings + System Readiness

## Suggested Git commit:
`feat: add persistent project and database system`

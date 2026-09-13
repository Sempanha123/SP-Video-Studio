# PHASE 38 STATUS

**Complete — Database + Project Migrations**

Baseline: Phase 37 GitHub `main` commit `01a24cf1cd0453d9519c6e8ea31057a20229b7d8`.

## Completed:

Phase 38 adds forward-only application/database, project, settings, recovery, template-adapter, Asset/Batch compatibility and migration-failure UX without creating a second persistence system. Migration paths are explicit, ordered, backup-first, validated and newer-version safe.

## Migration architecture:

- Explicit version contracts: app DB 28, project 2, settings 2, recovery snapshot 2.
- Ordered generic migration registry with gap/downgrade rejection.
- Application migrations stay in the existing `storage/migrations` chain.
- Project migrations stay in the new `migrations/project` registry and run before open/duplicate.
- Migration result/status/warning types are shared instead of using ad-hoc booleans.
- No destructive drop/recreate shortcut is used by Phase 38.

## Application DB migrations:

- Added migration 28 and `app_version` bookkeeping to `schema_migrations`.
- Startup migration runs before normal repository use.
- Uses SQLite backup API, crash marker, `BEGIN IMMEDIATE`, integrity/FK validation and restore-on-failure.
- Rejects a database whose schema is newer than the current app.
- Adds migration history/state and project/recovery schema-version metadata.
- Active Batch work from an old process is paused/interrupted instead of silently resumed.

## Project schema versions:

- Added `project_schema_version` to the project model, DB row and `project.json`.
- Project 1 → 2 migration is deterministic and backup-first.
- Known language aliases normalize to registry codes; unknown values are preserved with warnings.
- Legacy Script section content can create deterministic SpeechBlocks only where none exist.
- Legacy Dub/volume settings map to the existing generic Audio Mixer.
- Unknown project metadata is retained through migration/serialization.

## Settings migrations:

- Added settings schema 2 and a pure settings migration service.
- Known flat legacy keys map into current sections.
- Theme, project root, performance, shortcuts, media-tool and accessibility preferences are preserved.
- Unknown keys remain in the persisted payload rather than being discarded.
- Newer settings schemas are rejected.

## Template migrations:

Phase 38 reuses the Phase 24 `TemplateSchemaMigrator` through a thin adapter. No duplicate template schema/migrator was introduced.

## Asset migrations:

Existing Asset Library rows remain authoritative. Managed/referenced mode, paths, tags/collections, rights and usage metadata are not recreated or reimported by Phase 38. Regression fixtures verify Asset records survive project migration unchanged.

## Batch migrations:

Existing Batch rows, items, stage states, template snapshots and variants are preserved. A previously `running` Batch becomes `paused`; active items/stages become `interrupted`, preventing unsafe automatic continuation after an app upgrade.

## Recovery migrations:

- Recovery snapshots persist an explicit schema version.
- Old supported payloads migrate in memory on restore.
- The stored old snapshot file is not silently rewritten.
- Newer recovery payloads use the existing unsupported-version path.

## Backup strategy:

- Project migration backup: shared SQLite DB + `project.json` + small manifest; source media is not copied.
- Application migration backup: SQLite backup API before pending DB migrations.
- Migration backups are a protected storage category and use the Phase 37 managed-root safe-delete boundary.
- Successful project migrations retain at least the newest three backups and respect the minimum retention age.

## Failure recovery:

- DB migration failure restores the pre-migration application database backup.
- Project migration failure rolls back the SQLite transaction and restores original project metadata.
- Migration-in-progress markers allow interrupted startup/project migration detection.
- Direct backup-restore tests verify both DB rows and `project.json` can be recovered.
- The failure dialog exposes **Open Diagnostics**, **Open Backup Location**, and **Close**.

## Newer-version protection:

A project whose DB or `project.json` version is newer than supported is rejected without modification with the required message:

`This project was created with a newer MMO Video Studio version.`

The dialog exposes **Open Folder** and **Cancel**.

## Foreign-key validation:

Migration validation runs SQLite integrity and foreign-key checks and validates required project ownership. A deliberately injected orphan record is detected and fails validation.

## Legacy fixtures:

`tests/fixtures/phase38_legacy.py` documents real schema milestones already present in the repository: early project/media, Script-only, Scene/Subtitle, Timeline, News, Story/Dub, Phase 22 multilingual/SpeechBlock/layers, Phase 30 Audio Mixer and current schema. Fixtures do not invent historical tables that were never shipped.

## New files:

- `PHASE38_REPORT.md`
- `docs/PHASE38_DATABASE_PROJECT_MIGRATIONS.md`
- `domain/migration_result.py`
- `domain/schema_version.py`
- `migrations/__init__.py`
- `migrations/app/__init__.py`
- `migrations/project/__init__.py`
- `migrations/project/v001_to_v002.py`
- `migrations/template/__init__.py`
- `services/backup_service.py`
- `services/migration_service.py`
- `services/migration_validation_service.py`
- `services/project_migration_service.py`
- `services/recovery_migration_service.py`
- `services/settings_migration_service.py`
- `storage/migration_registry.py`
- `storage/migrations/m028_phase38_migration_metadata.py`
- `tests/fixtures/phase38_legacy.py`
- `tests/test_phase38_migrations.py`
- `app/phase38_runtime.py`

## Modified files:

- `README.md`
- `domain/project.py`
- `domain/recovery_snapshot.py`
- `domain/settings.py`
- `domain/storage_category.py`
- `main.py`
- `pyproject.toml`
- `services/recovery_snapshot_service.py`
- `services/settings_service.py`
- `storage/database.py`
- `storage/migrations/__init__.py`
- `storage/repositories/project_repository.py`
- `storage/repositories/recovery_repository.py`
- `ui/controllers/project_controller.py`
- `ui/qml/Main.qml`

`domain/recovery_errors.py` and `storage/json_writer.py` were used during implementation/testing but are byte-identical to the Phase 37 baseline and are not part of the final Phase 38 delta.

## Tests run:

Focused Phase 38:

```text
python -m pytest -q tests/test_phase38_migrations.py
36 passed
```

Available Phase 35–38 regression overlay:

```text
python -m pytest -q \
  tests/test_phase35_onboarding.py \
  tests/test_phase36_diagnostics.py \
  tests/test_phase37_security.py \
  tests/test_phase38_migrations.py
168 passed, 2 failed
```

The two failures are superseded static entrypoint assertions only: Phase 35 expects `main.py` to remain Phase 35, and Phase 37 expects the package entrypoint to remain Phase 37. Phase 38 intentionally changes both to `app.phase38_runtime`. No behavioral test in this available cross-phase gate failed.

## Legacy-project migration test:

Passed. An older English/Khmer project migrates after creating the protected backup, then opens through current persistence structures and can be edited/saved.

## Multilingual migration test:

Passed. Thai/Vietnamese language data, plus English/Khmer fixture content, remains valid; known aliases normalize carefully and unknown languages remain preserved rather than guessed.

## SpeechBlock migration test:

Passed. Missing legacy SpeechBlocks are derived deterministically from real Script-section content; existing SpeechBlocks are not duplicated and a second migration call is idempotent/current.

## Audio/Dub migration test:

Passed. Legacy Dub mix settings and project-level source/narration volume settings map to existing generic Audio Mixer roles/settings while preserving existing mixer data.

## Failed-migration rollback test:

Passed. Injected migration failure leaves the original project unchanged and retains a recovery backup. Application migration failure also restores the pre-migration DB backup.

## No-data-loss test:

Passed. Representative IDs, Unicode text, media fingerprints/references, subtitles/scenes/layers, Timeline data, Asset records, Batch state and multilingual SpeechBlock/speaker data are compared before/after migration.

## Post-migration render test:

Passed with the installed real FFmpeg. The migrated project was edited/saved and a small H.264/yuv420p MP4 was successfully produced under `renders/`.

## Known issues:

- The working sandbox does not contain a full local Git checkout, so Phase 37 GitHub `main` is the authoritative baseline and a literal local `git status` cannot be reported here.
- The available regression overlay is not the full repository test suite. Phase 39 should run the complete native Windows/PySide6 end-to-end suite.
- The two older entrypoint assertions described above are intentionally stale after moving to Phase 38; historical tests were not weakened to hide that fact.
- No live Windows/PySide6 click-through of the new migration dialogs was possible in this sandbox. Their exact messages/actions are covered by static Phase 38 contract tests.

## Architecture decisions:

- Extend the existing `storage/migrations` application chain rather than introducing a second DB migration framework.
- Keep per-project semantic migration separate from global DB DDL, but share explicit version/result/validation contracts.
- Reuse Phase 24 template migration and Phase 37 safe-path/storage boundaries.
- Preserve unknown fields/languages when mapping is ambiguous.
- Migrate old Recovery payloads in memory, not by rewriting the user's recovery file.
- Pause/interruption is safer than automatically resuming Batch work across application upgrades.
- Do not show fake migration progress; the current migration is short/deterministic. A future long migration should expose real progress events.

## Recommended next phase:

**Phase 39 — Full Test Suite + End-to-End QA**

## Suggested Git commit:

```text
feat: add safe versioned database and project migrations
```

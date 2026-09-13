# Phase 38 — Database + Project Migrations

## Scope

Phase 38 adds durable, versioned upgrade paths to the existing SP/MMO Video Studio architecture. It does not replace the SQLite repository layer, project services, Recovery, Phase 24 template migration, Phase 27 autosave/recovery, Phase 30 Audio Mixer, or the Phase 37 security boundaries. The goal is to let older installations and projects move forward without silently losing IDs, text, media references, language metadata, mixer intent, Batch checkpoints, or recovery data.

Current schema contracts introduced by this phase are:

- Application SQLite schema: **28**
- Project schema: **2**
- Settings schema: **2**
- Recovery snapshot payload schema: **2**

Versions are explicit and migrations are forward-only. A file or database created by a newer unsupported version is rejected rather than guessed or rewritten.

## Application database migrations

`storage/migrations` remains the single ordered application-database migration chain. Migration 28 extends the existing `schema_migrations` bookkeeping with application-version metadata, adds project schema version metadata and migration history/state tables, versions recovery snapshots, and safely interrupts stale Batch work left active across an application upgrade.

`SQLiteDatabase.initialize()` performs application migrations before normal repository use. The database is backed up with SQLite's backup API before pending migrations, a crash marker records the in-progress upgrade, and each migration uses `BEGIN IMMEDIATE`. Validation runs after migration work. On failure, the pre-migration database backup is restored. Startup detects a leftover migration marker and recovers before continuing.

A database whose recorded schema version is greater than the application-supported schema is rejected. It is never downgraded.

## Project migrations

Every project has a `project_schema_version` in both the project database row and `project.json`. `ProjectMigrationService.ensure_current()` runs before opening or duplicating a project.

The project migration flow is:

1. Read the database and `project.json` schema versions.
2. Reject a newer unsupported project without modifying it.
3. Resolve a deterministic ordered migration path.
4. Create a protected migration backup.
5. Write a migration-in-progress marker.
6. Run the project migration inside an immediate SQLite transaction.
7. Validate integrity, foreign keys, project ownership, and representative record counts.
8. Atomically write the migrated `project.json`.
9. Record migration history and commit.
10. Clear the marker and apply retention rules only after success.

The backup contains the shared SQLite database and small project metadata only. Source media is not duplicated by migration backup creation.

If the process is interrupted after project metadata was written but before the migration is committed, the SQLite transaction/journal protects database changes and the Phase 38 marker restores the prior project metadata before another migration attempt.

## Legacy project mapping rules

Phase 38 derives migrations from actual historical tables and fields already present in the repository. It does not invent synthetic historical product schemas.

The project 1 → 2 migration keeps existing IDs and data in place and adds compatibility data only where the mapping is deterministic:

- Historical language names/aliases are normalized to canonical registry codes when known: English → `en`, Khmer/Cambodian → `km`, Thai → `th`, Vietnamese/Viet → `vi`, including common locale variants.
- Unknown language values are preserved and surfaced as migration warnings rather than guessed.
- Legacy script-section content can seed deterministic SpeechBlocks when that section has no SpeechBlock yet. Existing SpeechBlocks are not duplicated.
- Legacy Dub mix settings map to the generic Phase 30 mixer using semantic source/dub roles.
- Legacy project `source_volume` / `sourceVolume` and `narration_volume` / `narrationVolume` values map to generic mixer metadata/tracks.
- Existing visual layer/composition metadata remains in the existing generic scene-layer model; Phase 38 does not create a second composition system.
- Existing Asset Library, News, Story, Shorts, Timeline, subtitles, voice/speaker, media, template, and Batch records stay in their authoritative tables.

## Settings migrations

Settings now carry `settings_version = 2`. `SettingsMigrationService` migrates older settings as a pure data transform before `AppSettings` validation. It maps known historical flat keys into the current sections while preserving unknown keys and nested data in `extra_payload` so a round-trip does not silently discard future or third-party values.

Covered compatibility includes the project root, performance profile, keyboard shortcut overrides, theme/general choices, media-tool configuration, and accessibility preferences.

A newer unsupported settings schema is rejected instead of rewritten.

## Template migrations

Phase 38 does not create a second template migration system. `migrations.template.migrate_payload()` delegates to the existing Phase 24 `TemplateSchemaMigrator` so `.mmovtemplate` compatibility remains centralized and Phase 37 package security checks remain authoritative.

## Asset and Batch migration behavior

Asset migration behavior is preservation-first. Managed/referenced mode, paths, tags/collections, rights metadata, and usage state remain in the existing Asset Library schema. Phase 38 does not reimport or recopy source assets.

Batch records and template snapshots remain in the existing Batch Factory schema. If an application upgrade finds a Batch marked `running`, the Batch is paused with an upgrade reason. Active item states are changed to `interrupted`, and running per-stage checkpoints are changed to `interrupted`. Completed/failed/cancelled historical results remain unchanged.

This avoids silently resuming work that belonged to a prior process/runtime while preserving enough checkpoint data for the existing Batch recovery/retry logic.

## Recovery snapshot migrations

Recovery snapshots now persist an explicit schema version. Creation stores the current payload schema. Loading an older supported snapshot passes its payload through `RecoveryMigrationService` in memory; the stored snapshot bytes are not silently rewritten. Loading a newer unsupported snapshot marks it unsupported and raises the existing `RecoveryVersionUnsupported` path.

## Backup retention and safety

Migration backups are registered as a protected storage category. They live below the application-managed migration backup root and are deleted only through the Phase 37 safe-path boundary. Successful project migration pruning keeps at least the newest three backups and never removes backups younger than the minimum retention age (14 days in the Phase 38 service default).

Application-database migration backups use a separate app backup directory and retain the newest protected copies needed for startup recovery.

## Validation and no-data-loss checks

`MigrationValidationService` performs SQLite `integrity_check`, `foreign_key_check`, required-table checks, project ownership checks, and representative per-project record counts. Foreign-key orphan failures stop the migration.

The Phase 38 fixture catalogue covers actual repository milestones:

- early project + media
- Script-only
- Scene + Subtitle
- advanced Timeline
- News Studio
- Story + Dub
- Phase 22 multilingual speakers/SpeechBlocks/layers
- Audio Mixer
- current Phase 38 schema

Representative migration tests fingerprint IDs, Unicode text, and media references before and after migration. The multilingual fixture includes English, Khmer, Thai, and Vietnamese content and retains speaker/SpeechBlock data, layered/chroma-key scene metadata, Dub settings, and generic Audio Mixer data.

## User-facing failure behavior

A project created by a newer unsupported version is not modified. The UI shows:

> This project was created with a newer MMO Video Studio version.

Actions: **Open Folder** and **Cancel**.

If a supported project migration fails, the transaction is rolled back and the original metadata is restored. The UI shows:

> MMO Video Studio could not update this project safely. The original project was kept unchanged.

Actions: **Open Diagnostics**, **Open Backup Location**, and **Close**.

The current 1 → 2 migration is intentionally short and deterministic, so no fake progress percentage is shown. A future long-running migration should expose real progress rather than an artificial timer.

## Migration author rules

Future migrations should follow these rules:

- append a new ordered migration; never edit an already-released migration to reinterpret old data;
- keep migration steps deterministic and idempotent where practical;
- avoid destructive drop/recreate shortcuts;
- preserve unknown fields unless there is a documented unsafe reason not to;
- keep user media out of migration backups unless a future migration explicitly changes media bytes;
- never infer an unknown language or semantic role from ambiguous data;
- validate foreign keys and required ownership relations before success;
- make new migration data compatible with existing Recovery and diagnostics paths;
- add representative old-version fixtures and failure injection tests with every schema change;
- reject newer versions rather than attempting downgrade or best-effort parsing.

## Validation environment

Phase 38's focused suite is runnable without PySide6 UI startup. The post-migration render smoke test uses a real installed FFmpeg and creates a small H.264/yuv420p MP4 after project migration and edit/save. Static UX contract tests verify the required newer-version and migration-failure actions/messages.

A complete native Windows/PySide6 visual interaction pass still belongs to Phase 39 end-to-end QA; Phase 38 does not claim that UI automation was performed in this Linux/sandbox environment.

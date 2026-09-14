from __future__ import annotations

from app.constants import APP_VERSION

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from domain.migration_result import MigrationResult, MigrationStatus, MigrationWarning
from domain.schema_version import PROJECT_SCHEMA_VERSION
from migrations.project import registry as project_registry
from services.migration_validation_service import MigrationValidationService
from storage.json_writer import atomic_write_json, read_json


class ProjectMigrationError(RuntimeError):
    user_message = "MMO Video Studio could not update this project safely. The original project was kept unchanged."
    def __init__(self, message: str | None = None, *, backup_path: str = "") -> None:
        super().__init__(message or self.user_message); self.backup_path = backup_path


class NewerProjectVersionError(ProjectMigrationError):
    user_message = "This project was created with a newer MMO Video Studio version."
    def __init__(self, project_path: str = "") -> None:
        super().__init__(self.user_message); self.project_path = project_path


_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(project_id: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(str(project_id), threading.RLock())


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectMigrationService:
    def __init__(self, database, project_repository, backup_service, validation: MigrationValidationService | None = None, logger=None) -> None:
        self.database = database
        self.projects = project_repository
        self.backups = backup_service
        self.validation = validation or MigrationValidationService()
        self.logger = logger or logging.getLogger("sp_video_studio.project_migrations")
        self.registry = project_registry()

    def ensure_current(self, project_id: str) -> MigrationResult:
        with _lock_for(project_id):
            project = self.projects.get_by_id(project_id)
            if project is None:
                raise KeyError(f"Project {project_id} does not exist.")
            project_path = Path(project.project_path)
            metadata_path = project_path / "project.json"
            if not metadata_path.is_file():
                raise ProjectMigrationError("Project metadata is missing.")
            self._recover_interrupted(project_id, project_path)
            metadata = read_json(metadata_path)
            metadata_version = int(metadata.get("project_schema_version", metadata.get("version", 1)) or 1)
            db_version = int(getattr(project, "project_schema_version", getattr(project, "version", 1)) or 1)
            current = min(metadata_version, db_version)
            if max(metadata_version, db_version) > PROJECT_SCHEMA_VERSION:
                raise NewerProjectVersionError(str(project_path))
            if current == PROJECT_SCHEMA_VERSION and metadata_version == db_version:
                return MigrationResult(MigrationStatus.CURRENT, current, current)

            try:
                steps = self.registry.path(current, PROJECT_SCHEMA_VERSION)
            except (KeyError, ValueError) as exc:
                raise ProjectMigrationError("No supported migration path exists for this project.") from exc

            backup = self.backups.create_project_backup(project_id, project_path)
            self.backups.write_marker(project_id, {
                "backupPath": str(backup.root), "fromVersion": current,
                "toVersion": PROJECT_SCHEMA_VERSION, "startedAt": _utc(),
            })
            warnings: list[MigrationWarning] = []
            applied: list[str] = []
            details: dict[str, object] = {}
            original_metadata = dict(metadata)
            started = _utc()
            try:
                with self.database.connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    for step in steps:
                        part = step.apply(connection, project_id, metadata, warnings)
                        if isinstance(part, dict): details.update(part)
                        if step.validate: step.validate(connection)
                        applied.append(step.migration_id)
                    connection.execute(
                        "UPDATE projects SET version=?, project_schema_version=?, language=? WHERE id=?",
                        (PROJECT_SCHEMA_VERSION, PROJECT_SCHEMA_VERSION, str(metadata.get("language") or project.language), project_id),
                    )
                    counts = self.validation.validate_project(connection, project_id)
                    metadata["project_schema_version"] = PROJECT_SCHEMA_VERSION
                    metadata["version"] = PROJECT_SCHEMA_VERSION
                    atomic_write_json(metadata_path, metadata)
                    self._history(connection, project_id, applied[-1] if applied else "project_current", current,
                                  PROJECT_SCHEMA_VERSION, "completed", counts, len(warnings), str(backup.root), started)
                    connection.commit()
            except Exception as exc:
                try:
                    if backup.metadata_path and backup.metadata_path.is_file():
                        atomic_write_json(metadata_path, read_json(backup.metadata_path))
                    else:
                        atomic_write_json(metadata_path, original_metadata)
                except Exception:
                    self.logger.exception("Could not restore project metadata after failed migration: %s", project_id)
                self.backups.clear_marker(project_id)
                self._record_failure(project_id, current, PROJECT_SCHEMA_VERSION, backup.root, started)
                self.logger.exception("Project migration failed: project=%s from=%d to=%d", project_id, current, PROJECT_SCHEMA_VERSION)
                raise ProjectMigrationError(backup_path=str(backup.root)) from exc

            self.backups.clear_marker(project_id)
            self.backups.prune()
            self.logger.info("Project migration completed: project=%s from=%d to=%d steps=%s",
                             project_id, current, PROJECT_SCHEMA_VERSION, ",".join(applied))
            return MigrationResult(MigrationStatus.MIGRATED, current, PROJECT_SCHEMA_VERSION, applied, warnings, backup.root, details)

    def _recover_interrupted(self, project_id: str, project_path: Path) -> None:
        marker = self.backups.read_marker(project_id)
        if not marker or not marker.get("migration_in_progress"):
            return
        root = Path(str(marker.get("backupPath") or ""))
        metadata = root / "project.json"
        if metadata.is_file():
            atomic_write_json(project_path / "project.json", read_json(metadata))
            self.logger.warning("Recovered interrupted project migration metadata: project=%s", project_id)
            self.backups.clear_marker(project_id)
            return
        raise ProjectMigrationError("An interrupted project migration was detected but its backup metadata is missing.", backup_path=str(root))

    def _history(self, connection: sqlite3.Connection, project_id: str, migration_id: str, from_version: int,
                 to_version: int, status: str, counts: dict[str, int], warning_count: int,
                 backup_path: str, started_at: str) -> None:
        tables = {str(x[0]) for x in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "migration_history" not in tables:
            return
        connection.execute(
            """INSERT INTO migration_history(scope,subject_id,migration_id,from_version,to_version,status,record_counts_json,
               warning_count,backup_path,started_at,completed_at,app_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("project", project_id, migration_id, from_version, to_version, status,
             json.dumps(counts, sort_keys=True), warning_count, backup_path, started_at, _utc(), APP_VERSION),
        )

    def _record_failure(self, project_id: str, from_version: int, to_version: int, backup_path: Path, started: str) -> None:
        try:
            with self.database.connect() as c, c:
                self._history(c, project_id, "project_migration", from_version, to_version, "failed", {}, 0, str(backup_path), started)
        except Exception:
            pass

from __future__ import annotations

import sqlite3
from collections.abc import Iterable


class MigrationValidationError(RuntimeError):
    pass


class MigrationValidationService:
    def validate_database(self, connection: sqlite3.Connection, *, required_tables: Iterable[str] = ()) -> None:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or str(integrity[0]).lower() != "ok":
            raise MigrationValidationError("Database integrity validation failed.")
        fk = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise MigrationValidationError(f"Foreign-key validation found {len(fk)} problem(s).")
        existing = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [name for name in required_tables if name not in existing]
        if missing:
            raise MigrationValidationError("Required tables are missing: " + ", ".join(missing))

    def validate_project(self, connection: sqlite3.Connection, project_id: str) -> dict[str, int]:
        row = connection.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row or int(row[0]) != 1:
            raise MigrationValidationError("Migrated project record is missing.")
        fk = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise MigrationValidationError("Project migration left foreign-key violations.")
        counts: dict[str, int] = {}
        tables = {str(r[0]) for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, column in (
            ("media_assets", "project_id"), ("scripts", "project_id"), ("scenes", "project_id"),
            ("speakers", "project_id"), ("subtitle_tracks", "project_id"), ("audio_tracks", "project_id"),
            ("dubbing_projects", "project_id"), ("batches", "project_id"),
        ):
            if table not in tables:
                continue
            cols = {str(x[1]) for x in connection.execute(f"PRAGMA table_info({table})")}
            if column not in cols:
                continue
            counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", (project_id,)).fetchone()[0])
        return counts

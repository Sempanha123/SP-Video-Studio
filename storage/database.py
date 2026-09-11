from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from domain.project import utc_now_iso
from storage.migrations import MIGRATIONS


class DatabaseMigrationError(RuntimeError):
    pass


class SQLiteDatabase:
    """Centralized SQLite connection and schema migration manager."""

    def __init__(self, path: Path, logger: logging.Logger | None = None) -> None:
        self.path = Path(path)
        self.logger = logger or logging.getLogger("sp_video_studio.database")

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
                applied = {
                    int(row["version"])
                    for row in connection.execute("SELECT version FROM schema_migrations")
                }
                for migration in sorted(MIGRATIONS, key=lambda item: item.version):
                    if migration.version in applied:
                        continue
                    try:
                        connection.execute("BEGIN IMMEDIATE")
                        migration.apply(connection)
                        connection.execute(
                            "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                            (migration.version, migration.name, utc_now_iso()),
                        )
                        connection.commit()
                        self.logger.info(
                            "Applied database migration %03d_%s",
                            migration.version,
                            migration.name,
                        )
                    except Exception as exc:
                        connection.rollback()
                        self.logger.exception(
                            "Database migration %03d_%s failed",
                            migration.version,
                            migration.name,
                        )
                        raise DatabaseMigrationError(
                            f"Could not apply database migration {migration.version}."
                        ) from exc
        except DatabaseMigrationError:
            raise
        except sqlite3.Error as exc:
            self.logger.exception("Database initialization failed at %s", self.path)
            raise DatabaseMigrationError("Could not initialize the application database.") from exc

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def current_version(self) -> int:
        if not self.path.exists():
            return 0
        with self.connect() as connection:
            row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
            return int(row["version"] or 0) if row else 0

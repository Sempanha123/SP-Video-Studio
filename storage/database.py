from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from collections.abc import Iterator

from storage.migrations import MIGRATIONS


class DatabaseMigrationError(RuntimeError):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _app_version() -> str:
    try:
        return importlib_metadata.version("sp-video-studio")
    except importlib_metadata.PackageNotFoundError:
        return "dev"


_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _path_lock(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path.resolve(strict=False)))
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


class SQLiteDatabase:
    """Central SQLite manager with backup-first, resumable startup migrations."""

    def __init__(self, path: Path, logger: logging.Logger | None = None) -> None:
        self.path = Path(path)
        self.logger = logger or logging.getLogger("sp_video_studio.database")
        self.journal_mode = "unknown"
        self._lock = _path_lock(self.path)

    @property
    def migration_backup_root(self) -> Path:
        return self.path.parent / "migration_backups" / "app"

    @property
    def migration_marker(self) -> Path:
        return self.migration_backup_root / "migration_in_progress.json"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._recover_incomplete_if_needed()
            backup: Path | None = None
            try:
                with self.connect() as c:
                    self._configure(c)
                    c.execute(
                        """CREATE TABLE IF NOT EXISTS schema_migrations(
                        version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL,app_version TEXT NOT NULL DEFAULT '')"""
                    )
                    c.commit()
                    applied = {int(r["version"]) for r in c.execute("SELECT version FROM schema_migrations")}
                    current = max(applied) if applied else 0
                    from domain.schema_version import APP_SCHEMA_VERSION
                    if current > APP_SCHEMA_VERSION:
                        raise DatabaseMigrationError(
                            f"This database was created by a newer SP Video Studio version (schema {current})."
                        )
                    pending = [m for m in sorted(MIGRATIONS, key=lambda x: x.version) if m.version not in applied]
                    if not pending:
                        self._validate(c)
                        return
                    backup = self._backup_before_migrations(max(applied) if applied else 0, max(m.version for m in pending))
                    self._write_marker(backup, min(pending, key=lambda m: m.version).version - 1, max(m.version for m in pending))
                    for migration in pending:
                        started = _utc_now_iso()
                        try:
                            c.execute("BEGIN IMMEDIATE")
                            migration.apply(c)
                            if migration.validate:
                                migration.validate(c)
                            self._record_migration(c, migration.version, migration.name)
                            c.commit()
                            self.logger.info(
                                "Applied database migration %03d_%s app=%s",
                                migration.version, migration.name, _app_version(),
                            )
                        except Exception as exc:
                            c.rollback()
                            self.logger.exception("Database migration %03d_%s failed", migration.version, migration.name)
                            raise DatabaseMigrationError(f"Could not apply database migration {migration.version}.") from exc
                    self._validate(c)
                self._clear_marker()
                self._prune_backups()
            except DatabaseMigrationError:
                if backup and backup.is_file():
                    self._restore_database_file(backup)
                raise
            except sqlite3.Error as exc:
                if backup and backup.is_file():
                    self._restore_database_file(backup)
                self.logger.exception("Database initialization failed at %s", self.path)
                raise DatabaseMigrationError("Could not initialize the application database.") from exc

    def _configure(self, c: sqlite3.Connection) -> None:
        try:
            row = c.execute("PRAGMA journal_mode=WAL").fetchone()
            self.journal_mode = str(row[0] if row else "unknown").lower()
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA wal_autocheckpoint=1000")
            if self.journal_mode != "wal":
                self.logger.warning("SQLite WAL unavailable; continuing with journal mode %s", self.journal_mode)
        except sqlite3.Error:
            self.logger.warning("SQLite WAL could not be enabled; continuing with default journal mode", exc_info=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.path, timeout=10.0)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
        try:
            yield c
        finally:
            c.close()

    def current_version(self) -> int:
        if not self.path.exists():
            return 0
        with self.connect() as c:
            try:
                row = c.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
                return int(row["version"] or 0) if row else 0
            except sqlite3.Error:
                return 0

    def applied_migrations(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        with self.connect() as c:
            try:
                columns = {str(x[1]) for x in c.execute("PRAGMA table_info(schema_migrations)")}
                extra = ", app_version" if "app_version" in columns else ""
                rows = c.execute(f"SELECT version,name,applied_at{extra} FROM schema_migrations ORDER BY version").fetchall()
                return [dict(row) for row in rows]
            except sqlite3.Error:
                return []

    def backup_to(self, target: Path) -> Path:
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path, timeout=10.0)
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
            dest.commit()
        finally:
            dest.close(); source.close()
        return target

    def _record_migration(self, c: sqlite3.Connection, version: int, name: str) -> None:
        columns = {str(x[1]) for x in c.execute("PRAGMA table_info(schema_migrations)")}
        if "app_version" in columns:
            c.execute(
                "INSERT INTO schema_migrations(version,name,applied_at,app_version) VALUES(?,?,?,?)",
                (version, name, _utc_now_iso(), _app_version()),
            )
        else:
            c.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (version, name, _utc_now_iso()),
            )

    def _validate(self, c: sqlite3.Connection) -> None:
        row = c.execute("PRAGMA integrity_check").fetchone()
        if not row or str(row[0]).lower() != "ok":
            raise DatabaseMigrationError("Database integrity validation failed after migration.")
        fk = c.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise DatabaseMigrationError("Foreign-key validation failed after migration.")

    def _backup_before_migrations(self, from_version: int, to_version: int) -> Path:
        self.migration_backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = self.migration_backup_root / f"app-v{from_version}-to-v{to_version}-{stamp}.db"
        return self.backup_to(target)

    def _write_marker(self, backup: Path, from_version: int, to_version: int) -> None:
        self.migration_backup_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "migration_in_progress": True,
            "backup": str(backup),
            "fromVersion": int(from_version),
            "toVersion": int(to_version),
            "startedAt": _utc_now_iso(),
        }
        temp = self.migration_marker.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp, self.migration_marker)

    def _clear_marker(self) -> None:
        self.migration_marker.unlink(missing_ok=True)

    def _recover_incomplete_if_needed(self) -> None:
        if not self.migration_marker.is_file():
            return
        try:
            payload = json.loads(self.migration_marker.read_text(encoding="utf-8"))
            backup = Path(str(payload.get("backup") or ""))
        except (OSError, ValueError, json.JSONDecodeError):
            self.logger.error("Unreadable migration marker; refusing to ignore possible interrupted migration.")
            raise DatabaseMigrationError("A previous database migration did not finish safely.")
        if not backup.is_file():
            raise DatabaseMigrationError("A previous database migration was interrupted and its backup is missing.")
        self.logger.warning("Recovering interrupted database migration from backup %s", backup.name)
        self._restore_database_file(backup)
        self._clear_marker()

    def _restore_database_file(self, backup: Path) -> None:
        for suffix in ("-wal", "-shm"):
            Path(str(self.path) + suffix).unlink(missing_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".restore")
        shutil.copy2(backup, temp)
        os.replace(temp, self.path)

    def _prune_backups(self, keep: int = 3) -> None:
        if not self.migration_backup_root.is_dir():
            return
        rows = sorted(self.migration_backup_root.glob("app-v*-to-v*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in rows[max(1, keep):]:
            try:
                path.unlink()
            except OSError:
                pass

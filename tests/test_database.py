from pathlib import Path

import pytest

from storage.database import SQLiteDatabase


def test_database_initialization_applies_migrations(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "data" / "app.db")
    db.initialize()
    assert db.path.is_file()
    assert db.current_version() == 2

    with db.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        indexes = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
    assert {"schema_migrations", "projects", "media_assets"} <= tables
    assert "idx_projects_updated_at" in indexes
    assert "idx_projects_last_opened_at" in indexes
    assert "idx_media_assets_project_imported" in indexes
    assert "idx_media_assets_project_type" in indexes


def test_database_initialization_is_idempotent(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db")
    db.initialize()
    db.initialize()
    with db.connect() as connection:
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    assert [row["version"] for row in rows] == [1, 2]


def test_failed_migration_rolls_back_schema_changes(tmp_path: Path, monkeypatch):
    import storage.database as database_module
    from storage.database import DatabaseMigrationError
    from storage.migrations import Migration

    def broken_migration(connection):
        connection.execute("CREATE TABLE should_rollback(id INTEGER)")
        raise RuntimeError("boom")

    monkeypatch.setattr(
        database_module,
        "MIGRATIONS",
        (Migration(2, "broken", broken_migration),),
    )
    db = SQLiteDatabase(tmp_path / "app.db")
    with pytest.raises(DatabaseMigrationError):
        db.initialize()

    with db.connect() as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='should_rollback'"
        ).fetchone()
        versions = connection.execute("SELECT version FROM schema_migrations").fetchall()
    assert table is None
    assert versions == []

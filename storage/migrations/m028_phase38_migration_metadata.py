from __future__ import annotations

from sqlite3 import Connection


def _columns(connection: Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def migrate(connection: Connection) -> None:
    schema_cols = _columns(connection, "schema_migrations")
    if "app_version" not in schema_cols:
        connection.execute("ALTER TABLE schema_migrations ADD COLUMN app_version TEXT NOT NULL DEFAULT ''")
    connection.execute("UPDATE schema_migrations SET app_version = 'legacy' WHERE app_version = ''")
    project_cols = _columns(connection, "projects")
    if project_cols and "project_schema_version" not in project_cols:
        connection.execute("ALTER TABLE projects ADD COLUMN project_schema_version INTEGER NOT NULL DEFAULT 1")
        connection.execute("UPDATE projects SET project_schema_version = version WHERE project_schema_version = 1 AND version IS NOT NULL")
    # A Batch that was running under an older process must never auto-resume
    # across an application-schema upgrade. Preserve its definition/items, but
    # make the queue explicitly resumable by the user.
    tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "batches" in tables:
        batch_cols = _columns(connection, "batches")
        if {"status", "pause_reason"}.issubset(batch_cols):
            connection.execute(
                """UPDATE batches
                   SET status='paused',
                       pause_reason=CASE WHEN TRIM(COALESCE(pause_reason,''))=''
                         THEN 'App upgrade interrupted an active Batch safely'
                         ELSE pause_reason END
                   WHERE status='running'"""
            )
    if "batch_items" in tables:
        item_cols = _columns(connection, "batch_items")
        if "status" in item_cols:
            connection.execute(
                """UPDATE batch_items SET status='interrupted'
                   WHERE status IN ('validating','project_setup','translation','tts',
                                    'subtitles','scene_setup','rendering','exporting')"""
            )
    if "batch_stage_state" in tables:
        stage_cols = _columns(connection, "batch_stage_state")
        if "status" in stage_cols:
            connection.execute("UPDATE batch_stage_state SET status='interrupted' WHERE status='running'")
    if "recovery_snapshots" in tables:
        recovery_cols = _columns(connection, "recovery_snapshots")
        if "schema_version" not in recovery_cols:
            connection.execute("ALTER TABLE recovery_snapshots ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1")

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS migration_history(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          scope TEXT NOT NULL,
          subject_id TEXT NOT NULL DEFAULT '',
          migration_id TEXT NOT NULL,
          from_version INTEGER NOT NULL,
          to_version INTEGER NOT NULL,
          status TEXT NOT NULL,
          record_counts_json TEXT NOT NULL DEFAULT '{}',
          warning_count INTEGER NOT NULL DEFAULT 0,
          backup_path TEXT NOT NULL DEFAULT '',
          started_at TEXT NOT NULL,
          completed_at TEXT NOT NULL DEFAULT '',
          app_version TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_migration_history_scope_subject ON migration_history(scope,subject_id,id DESC);
        CREATE TABLE IF NOT EXISTS migration_state(
          scope TEXT NOT NULL,
          subject_id TEXT NOT NULL DEFAULT '',
          migration_id TEXT NOT NULL,
          from_version INTEGER NOT NULL,
          to_version INTEGER NOT NULL,
          backup_path TEXT NOT NULL DEFAULT '',
          started_at TEXT NOT NULL,
          PRIMARY KEY(scope,subject_id)
        );
        """
    )

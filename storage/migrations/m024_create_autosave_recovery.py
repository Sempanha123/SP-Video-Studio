from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS autosave_state (
            project_id TEXT PRIMARY KEY,
            project_revision INTEGER NOT NULL DEFAULT 0,
            saved_revision INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'clean',
            last_modified_at REAL NOT NULL DEFAULT 0,
            last_saved_at REAL NOT NULL DEFAULT 0,
            scheduled_at REAL,
            saving_revision INTEGER NOT NULL DEFAULT 0,
            dirty_topics_json TEXT NOT NULL DEFAULT '[]',
            failure_message TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS recovery_sessions (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            closed_at TEXT NOT NULL DEFAULT '',
            clean_shutdown INTEGER NOT NULL DEFAULT 0,
            app_version TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS recovery_snapshots (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            snapshot_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'valid',
            path TEXT NOT NULL,
            size INTEGER NOT NULL DEFAULT 0,
            checksum TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS interrupted_jobs (
            job_key TEXT PRIMARY KEY,
            project_id TEXT NOT NULL DEFAULT '',
            job_type TEXT NOT NULL,
            source_id TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'interrupted',
            retry_mode TEXT NOT NULL DEFAULT 'restart',
            detected_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_recovery_snapshots_project_created ON recovery_snapshots(project_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_recovery_sessions_started ON recovery_sessions(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_interrupted_jobs_project ON interrupted_jobs(project_id, job_type);
        """
    )

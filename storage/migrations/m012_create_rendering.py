from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS render_jobs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            preset_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            output_path TEXT,
            started_at TEXT,
            completed_at TEXT,
            progress REAL NOT NULL DEFAULT 0,
            expected_duration_ms INTEGER NOT NULL DEFAULT 0,
            actual_duration_ms INTEGER NOT NULL DEFAULT 0,
            settings_json TEXT NOT NULL DEFAULT '{}',
            error_message TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS render_outputs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            render_job_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            fps REAL NOT NULL,
            duration_ms INTEGER NOT NULL,
            video_codec TEXT NOT NULL,
            audio_codec TEXT NOT NULL DEFAULT '',
            file_size INTEGER NOT NULL DEFAULT 0,
            thumbnail_path TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(render_job_id) REFERENCES render_jobs(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_render_jobs_project_created ON render_jobs(project_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_render_jobs_project_status ON render_jobs(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_render_outputs_project_created ON render_outputs(project_id, created_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_render_output_job ON render_outputs(render_job_id);
        """
    )

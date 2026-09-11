from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS generated_audio (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            script_id TEXT,
            section_id TEXT,
            engine TEXT NOT NULL,
            model_id TEXT NOT NULL,
            language TEXT NOT NULL,
            voice_mode TEXT NOT NULL,
            voice_config_json TEXT NOT NULL DEFAULT '{}',
            text_hash TEXT NOT NULL,
            file_path TEXT NOT NULL,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            sample_rate INTEGER NOT NULL DEFAULT 0,
            channels INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            generation_settings_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE SET NULL,
            FOREIGN KEY(section_id) REFERENCES script_sections(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_generated_audio_project_created
            ON generated_audio(project_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_generated_audio_section
            ON generated_audio(section_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_generated_audio_active
            ON generated_audio(project_id, active);
        """
    )

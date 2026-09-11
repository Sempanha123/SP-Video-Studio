from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.execute(
        """
        CREATE TABLE media_assets (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            original_path TEXT,
            project_path TEXT NOT NULL UNIQUE,
            thumbnail_path TEXT,
            duration_ms INTEGER,
            width INTEGER,
            height INTEGER,
            fps REAL,
            codec TEXT,
            audio_codec TEXT,
            sample_rate INTEGER,
            channels INTEGER,
            file_size INTEGER NOT NULL,
            mime_type TEXT,
            extension TEXT,
            created_at TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            status TEXT NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX idx_media_assets_project_imported ON media_assets(project_id, imported_at DESC)"
    )
    connection.execute(
        "CREATE INDEX idx_media_assets_project_type ON media_assets(project_id, type)"
    )
    connection.execute("CREATE INDEX idx_media_assets_status ON media_assets(status)")

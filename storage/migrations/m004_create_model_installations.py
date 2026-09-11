from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.execute(
        """
        CREATE TABLE model_installations (
            model_id TEXT PRIMARY KEY,
            installed INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            install_path TEXT NOT NULL DEFAULT '',
            installed_version TEXT NOT NULL DEFAULT '',
            downloaded_bytes INTEGER NOT NULL DEFAULT 0,
            total_bytes INTEGER NOT NULL DEFAULT 0,
            installed_at TEXT,
            verified_at TEXT,
            verification_status TEXT NOT NULL DEFAULT 'unknown',
            error_message TEXT NOT NULL DEFAULT '',
            is_loaded INTEGER NOT NULL DEFAULT 0,
            in_use_count INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX idx_model_installations_status ON model_installations(status, updated_at DESC)"
    )

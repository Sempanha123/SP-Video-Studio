from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS translations (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_language TEXT NOT NULL,
            target_language TEXT NOT NULL,
            engine_id TEXT NOT NULL,
            model_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL DEFAULT '',
            settings_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS translation_segments (
            id TEXT PRIMARY KEY,
            translation_id TEXT NOT NULL,
            source_segment_id TEXT NOT NULL DEFAULT '',
            segment_order INTEGER NOT NULL,
            start_ms INTEGER,
            end_ms INTEGER,
            source_text TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            machine_translation TEXT NOT NULL DEFAULT '',
            translated_text TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            edited INTEGER NOT NULL DEFAULT 0,
            reviewed INTEGER NOT NULL DEFAULT 0,
            locked INTEGER NOT NULL DEFAULT 0,
            confidence REAL,
            notes TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(translation_id) REFERENCES translations(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_translations_project_source
            ON translations(project_id, source_type, source_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_translation_segments_order
            ON translation_segments(translation_id, segment_order);
        CREATE INDEX IF NOT EXISTS idx_translation_segments_source
            ON translation_segments(translation_id, source_segment_id);
        CREATE INDEX IF NOT EXISTS idx_translation_segments_review
            ON translation_segments(translation_id, reviewed, locked, status);
        """
    )

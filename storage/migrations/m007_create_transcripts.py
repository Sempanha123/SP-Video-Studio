from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS transcripts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            media_id TEXT NOT NULL,
            engine TEXT NOT NULL,
            model_id TEXT NOT NULL,
            model_version TEXT NOT NULL DEFAULT '',
            language_mode TEXT NOT NULL,
            detected_language TEXT,
            language_probability REAL,
            device TEXT NOT NULL,
            compute_type TEXT NOT NULL,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            settings_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            active INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(media_id) REFERENCES media_assets(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS transcript_segments (
            id TEXT PRIMARY KEY,
            transcript_id TEXT NOT NULL,
            segment_order INTEGER NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            text TEXT NOT NULL,
            original_text TEXT NOT NULL,
            confidence REAL,
            no_speech_probability REAL,
            temperature REAL,
            edited INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS transcript_words (
            id TEXT PRIMARY KEY,
            segment_id TEXT NOT NULL,
            word_order INTEGER NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            text TEXT NOT NULL,
            probability REAL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(segment_id) REFERENCES transcript_segments(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_transcripts_project_media
            ON transcripts(project_id, media_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_transcripts_active
            ON transcripts(media_id, active);
        CREATE INDEX IF NOT EXISTS idx_transcript_segments_order
            ON transcript_segments(transcript_id, segment_order);
        CREATE INDEX IF NOT EXISTS idx_transcript_words_order
            ON transcript_words(segment_id, word_order);
        """
    )

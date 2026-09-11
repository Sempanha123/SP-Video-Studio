from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS subtitle_styles (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            font_family TEXT NOT NULL,
            font_size REAL NOT NULL,
            font_weight INTEGER NOT NULL,
            italic INTEGER NOT NULL DEFAULT 0,
            text_color TEXT NOT NULL,
            secondary_text_color TEXT NOT NULL,
            outline_color TEXT NOT NULL,
            outline_width REAL NOT NULL,
            shadow_enabled INTEGER NOT NULL DEFAULT 1,
            shadow_offset REAL NOT NULL DEFAULT 2,
            background_enabled INTEGER NOT NULL DEFAULT 0,
            background_color TEXT NOT NULL,
            background_opacity REAL NOT NULL,
            alignment TEXT NOT NULL,
            vertical_position TEXT NOT NULL,
            horizontal_margin REAL NOT NULL,
            vertical_margin REAL NOT NULL,
            max_lines INTEGER NOT NULL,
            max_chars_per_line INTEGER NOT NULL,
            line_spacing REAL NOT NULL,
            highlight_color TEXT NOT NULL,
            highlight_text_color TEXT NOT NULL,
            secondary_scale REAL NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subtitle_tracks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            language TEXT NOT NULL,
            track_type TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL DEFAULT '',
            source_language TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            style_id TEXT NOT NULL DEFAULT '',
            is_default INTEGER NOT NULL DEFAULT 0,
            is_bilingual INTEGER NOT NULL DEFAULT 0,
            secondary_language TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subtitle_cues (
            id TEXT PRIMARY KEY,
            track_id TEXT NOT NULL,
            cue_order INTEGER NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            text TEXT NOT NULL DEFAULT '',
            secondary_text TEXT NOT NULL DEFAULT '',
            position TEXT NOT NULL DEFAULT 'bottom',
            alignment TEXT NOT NULL DEFAULT 'center',
            style_override_json TEXT NOT NULL DEFAULT '{}',
            edited INTEGER NOT NULL DEFAULT 0,
            locked INTEGER NOT NULL DEFAULT 0,
            source_segment_id TEXT NOT NULL DEFAULT '',
            source_hash TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(track_id) REFERENCES subtitle_tracks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subtitle_words (
            id TEXT PRIMARY KEY,
            cue_id TEXT NOT NULL,
            word_order INTEGER NOT NULL,
            text TEXT NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            probability REAL,
            highlight_group INTEGER,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(cue_id) REFERENCES subtitle_cues(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subtitle_user_presets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            style_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_subtitle_tracks_project ON subtitle_tracks(project_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_subtitle_tracks_source ON subtitle_tracks(project_id, source_type, source_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_subtitle_default_track ON subtitle_tracks(project_id) WHERE is_default=1;
        CREATE INDEX IF NOT EXISTS idx_subtitle_cues_order ON subtitle_cues(track_id, start_ms, cue_order);
        CREATE INDEX IF NOT EXISTS idx_subtitle_cues_source ON subtitle_cues(track_id, source_segment_id);
        CREATE INDEX IF NOT EXISTS idx_subtitle_words_order ON subtitle_words(cue_id, word_order);
        CREATE INDEX IF NOT EXISTS idx_subtitle_styles_project ON subtitle_styles(project_id);
        """
    )

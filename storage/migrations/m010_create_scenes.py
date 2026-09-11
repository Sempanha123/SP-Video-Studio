from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS scenes (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            scene_order INTEGER NOT NULL,
            name TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            primary_media_id TEXT NOT NULL DEFAULT '',
            background_media_id TEXT NOT NULL DEFAULT '',
            narration_audio_id TEXT NOT NULL DEFAULT '',
            subtitle_track_id TEXT NOT NULL DEFAULT '',
            script_section_id TEXT NOT NULL DEFAULT '',
            transcript_segment_id TEXT NOT NULL DEFAULT '',
            translation_segment_id TEXT NOT NULL DEFAULT '',
            source_hash TEXT NOT NULL DEFAULT '',
            source_status TEXT NOT NULL DEFAULT 'current',
            fit_mode TEXT NOT NULL DEFAULT 'fill',
            source_start_ms INTEGER NOT NULL DEFAULT 0,
            source_end_ms INTEGER,
            background_color TEXT NOT NULL DEFAULT '#10131A',
            transition_in_json TEXT NOT NULL DEFAULT '{}',
            transition_out_json TEXT NOT NULL DEFAULT '{}',
            audio_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'incomplete',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS scene_layers (
            id TEXT PRIMARY KEY,
            scene_id TEXT NOT NULL,
            layer_order INTEGER NOT NULL,
            layer_type TEXT NOT NULL,
            asset_id TEXT NOT NULL DEFAULT '',
            x REAL NOT NULL DEFAULT 0,
            y REAL NOT NULL DEFAULT 0,
            width REAL NOT NULL DEFAULT 1,
            height REAL NOT NULL DEFAULT 1,
            opacity REAL NOT NULL DEFAULT 1,
            rotation REAL NOT NULL DEFAULT 0,
            visible INTEGER NOT NULL DEFAULT 1,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS scene_overlays (
            id TEXT PRIMARY KEY,
            scene_id TEXT NOT NULL,
            overlay_order INTEGER NOT NULL,
            overlay_type TEXT NOT NULL,
            text TEXT NOT NULL DEFAULT '',
            secondary_text TEXT NOT NULL DEFAULT '',
            asset_id TEXT NOT NULL DEFAULT '',
            x REAL NOT NULL,
            y REAL NOT NULL,
            width REAL NOT NULL,
            height REAL NOT NULL,
            opacity REAL NOT NULL DEFAULT 1,
            rotation REAL NOT NULL DEFAULT 0,
            visible INTEGER NOT NULL DEFAULT 1,
            start_offset_ms INTEGER NOT NULL DEFAULT 0,
            end_offset_ms INTEGER,
            style_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_scenes_project_order ON scenes(project_id, scene_order);
        CREATE INDEX IF NOT EXISTS idx_scenes_project_enabled ON scenes(project_id, enabled, scene_order);
        CREATE INDEX IF NOT EXISTS idx_scenes_script_section ON scenes(project_id, script_section_id);
        CREATE INDEX IF NOT EXISTS idx_scene_layers_scene_order ON scene_layers(scene_id, layer_order);
        CREATE INDEX IF NOT EXISTS idx_scene_overlays_scene_order ON scene_overlays(scene_id, overlay_order);
        """
    )

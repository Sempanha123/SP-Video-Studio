from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS timeline_state (
            project_id TEXT PRIMARY KEY,
            zoom_level REAL NOT NULL DEFAULT 80,
            playhead_ms INTEGER NOT NULL DEFAULT 0,
            scroll_position REAL NOT NULL DEFAULT 0,
            snap_enabled INTEGER NOT NULL DEFAULT 1,
            snap_threshold_px REAL NOT NULL DEFAULT 8,
            active_track_id TEXT NOT NULL DEFAULT '',
            selected_clip_id TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS timeline_tracks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            track_type TEXT NOT NULL,
            name TEXT NOT NULL,
            track_order INTEGER NOT NULL,
            visible INTEGER NOT NULL DEFAULT 1,
            muted INTEGER NOT NULL DEFAULT 0,
            locked INTEGER NOT NULL DEFAULT 0,
            height INTEGER NOT NULL DEFAULT 64,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            UNIQUE(project_id, track_type)
        );
        CREATE INDEX IF NOT EXISTS idx_timeline_tracks_project_order ON timeline_tracks(project_id, track_order);
        CREATE TABLE IF NOT EXISTS timeline_markers (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            time_ms INTEGER NOT NULL,
            label TEXT NOT NULL DEFAULT 'Marker',
            color TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_timeline_markers_project_time ON timeline_markers(project_id, time_ms);
        """
    )

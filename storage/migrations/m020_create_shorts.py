from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS shorts_projects (
            project_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL DEFAULT 'manual',
            source_id TEXT NOT NULL DEFAULT '',
            target_duration_ms INTEGER NOT NULL DEFAULT 30000,
            target_aspect_ratio TEXT NOT NULL DEFAULT '9:16',
            language TEXT NOT NULL DEFAULT 'en',
            platform TEXT NOT NULL DEFAULT 'generic',
            style TEXT NOT NULL DEFAULT 'creator',
            status TEXT NOT NULL DEFAULT 'draft',
            source_project_id TEXT NOT NULL DEFAULT '',
            source_entity_ids_json TEXT NOT NULL DEFAULT '[]',
            source_fingerprint TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS short_candidates (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            hook TEXT NOT NULL DEFAULT '',
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            language TEXT NOT NULL DEFAULT 'en',
            status TEXT NOT NULL DEFAULT 'draft',
            source_project_id TEXT NOT NULL DEFAULT '',
            source_entity_ids_json TEXT NOT NULL DEFAULT '[]',
            source_fingerprint TEXT NOT NULL DEFAULT '',
            score_metadata_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_short_candidates_project ON short_candidates(project_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_short_candidates_source ON short_candidates(project_id, source_type, source_id);

        CREATE TABLE IF NOT EXISTS short_segments (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            segment_order INTEGER NOT NULL,
            source_start_ms INTEGER NOT NULL,
            source_end_ms INTEGER NOT NULL,
            source_entity_id TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(candidate_id) REFERENCES short_candidates(id) ON DELETE CASCADE,
            UNIQUE(candidate_id, segment_order)
        );
        CREATE INDEX IF NOT EXISTS idx_short_segments_candidate ON short_segments(candidate_id, segment_order);
        """
    )

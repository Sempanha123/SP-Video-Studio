from __future__ import annotations

from sqlite3 import Connection


def _columns(connection: Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS director_plans (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            workflow TEXT NOT NULL,
            platform TEXT NOT NULL,
            language TEXT NOT NULL,
            target_duration_ms INTEGER NOT NULL,
            aspect_ratio TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'review',
            plan_version INTEGER NOT NULL DEFAULT 1,
            schema_version INTEGER NOT NULL DEFAULT 1,
            rule_engine_version TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL DEFAULT '',
            recommendations_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS director_scene_plans (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            scene_order INTEGER NOT NULL,
            title TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT '',
            target_duration_ms INTEGER NOT NULL,
            script_section_id TEXT NOT NULL DEFAULT '',
            visual_type TEXT NOT NULL DEFAULT 'mixed_media',
            visual_description TEXT NOT NULL DEFAULT '',
            overlay_recommendation TEXT NOT NULL DEFAULT '',
            voice_style TEXT NOT NULL DEFAULT '',
            subtitle_style TEXT NOT NULL DEFAULT 'clean',
            transition TEXT NOT NULL DEFAULT 'cut',
            notes TEXT NOT NULL DEFAULT '',
            locked INTEGER NOT NULL DEFAULT 0,
            user_modified INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(plan_id) REFERENCES director_plans(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_director_plans_project ON director_plans(project_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_director_plans_source ON director_plans(project_id, source_type, source_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_director_scene_order ON director_scene_plans(plan_id, scene_order);
        """
    )
    columns = _columns(connection, "projects")
    if "active_director_plan_id" not in columns:
        connection.execute("ALTER TABLE projects ADD COLUMN active_director_plan_id TEXT")
    if "default_subtitle_preset_id" not in columns:
        connection.execute("ALTER TABLE projects ADD COLUMN default_subtitle_preset_id TEXT")

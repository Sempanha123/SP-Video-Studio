from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        template_type TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        workflow TEXT NOT NULL,
        version TEXT NOT NULL DEFAULT '1.0',
        schema_version INTEGER NOT NULL DEFAULT 1,
        author_label TEXT NOT NULL DEFAULT '',
        preview_image TEXT NOT NULL DEFAULT '',
        tags_json TEXT NOT NULL DEFAULT '[]',
        aspects_json TEXT NOT NULL DEFAULT '[]',
        languages_json TEXT NOT NULL DEFAULT '[]',
        features_json TEXT NOT NULL DEFAULT '[]',
        manifest_path TEXT NOT NULL DEFAULT '',
        template_json_path TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_templates_category_name ON templates(category,name COLLATE NOCASE);
    CREATE INDEX IF NOT EXISTS idx_templates_workflow ON templates(workflow,template_type);

    CREATE TABLE IF NOT EXISTS template_usage (
        template_id TEXT NOT NULL,
        project_id TEXT NOT NULL DEFAULT '',
        last_used_at TEXT NOT NULL,
        use_count INTEGER NOT NULL DEFAULT 0,
        template_version TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        PRIMARY KEY(template_id,project_id)
    );
    CREATE INDEX IF NOT EXISTS idx_template_usage_recent ON template_usage(last_used_at DESC);

    CREATE TABLE IF NOT EXISTS template_assets (
        template_id TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        asset_type TEXT NOT NULL DEFAULT 'asset',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        PRIMARY KEY(template_id,relative_path),
        FOREIGN KEY(template_id) REFERENCES templates(id) ON DELETE CASCADE
    );
    """)

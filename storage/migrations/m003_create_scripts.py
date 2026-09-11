from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.execute(
        """
        CREATE TABLE scripts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT NOT NULL,
            pace TEXT NOT NULL DEFAULT 'normal',
            version INTEGER NOT NULL,
            notes TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE script_sections (
            id TEXT PRIMARY KEY,
            script_id TEXT NOT NULL,
            section_order INTEGER NOT NULL,
            section_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            notes TEXT,
            enabled INTEGER NOT NULL,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX idx_scripts_project ON scripts(project_id, updated_at DESC)")
    connection.execute("CREATE INDEX idx_script_sections_script_order ON script_sections(script_id, section_order)")

from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.execute(
        """
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            workflow TEXT NOT NULL,
            language TEXT NOT NULL,
            aspect_ratio TEXT NOT NULL,
            fps INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_opened_at TEXT,
            thumbnail_path TEXT,
            status TEXT NOT NULL,
            project_path TEXT NOT NULL UNIQUE,
            version INTEGER NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX idx_projects_updated_at ON projects(updated_at DESC)")
    connection.execute("CREATE INDEX idx_projects_last_opened_at ON projects(last_opened_at DESC)")
    connection.execute("CREATE INDEX idx_projects_workflow ON projects(workflow)")
    connection.execute("CREATE INDEX idx_projects_status ON projects(status)")

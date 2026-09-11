from __future__ import annotations

from domain.project import Project
from storage.database import SQLiteDatabase


class ProjectRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, project: Project) -> Project:
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO projects(
                    id, title, workflow, language, aspect_ratio, fps,
                    created_at, updated_at, last_opened_at, thumbnail_path,
                    status, project_path, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._values(project),
            )
        return project

    def get_by_id(self, project_id: str) -> Project | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return Project.from_record(row) if row else None

    def list_all(self) -> list[Project]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM projects
                ORDER BY COALESCE(last_opened_at, updated_at) DESC, updated_at DESC
                """
            ).fetchall()
        return [Project.from_record(row) for row in rows]

    def list_recent(self, limit: int = 6) -> list[Project]:
        safe_limit = max(1, min(int(limit), 50))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM projects
                ORDER BY COALESCE(last_opened_at, updated_at) DESC, updated_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [Project.from_record(row) for row in rows]

    def update(self, project: Project) -> Project:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE projects SET
                    title = ?, workflow = ?, language = ?, aspect_ratio = ?, fps = ?,
                    created_at = ?, updated_at = ?, last_opened_at = ?, thumbnail_path = ?,
                    status = ?, project_path = ?, version = ?
                WHERE id = ?
                """,
                (
                    project.title,
                    str(project.workflow),
                    project.language,
                    project.aspect_ratio,
                    project.fps,
                    project.created_at,
                    project.updated_at,
                    project.last_opened_at,
                    project.thumbnail_path,
                    str(project.status),
                    project.project_path,
                    project.version,
                    project.project_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Project {project.project_id} does not exist.")
        return project

    def rename(self, project_id: str, title: str, updated_at: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                "UPDATE projects SET title = ?, updated_at = ? WHERE id = ?",
                (title, updated_at, project_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Project {project_id} does not exist.")

    def delete(self, project_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            if cursor.rowcount == 0:
                raise KeyError(f"Project {project_id} does not exist.")

    @staticmethod
    def _values(project: Project) -> tuple[object, ...]:
        return (
            project.project_id,
            project.title,
            str(project.workflow),
            project.language,
            project.aspect_ratio,
            project.fps,
            project.created_at,
            project.updated_at,
            project.last_opened_at,
            project.thumbnail_path,
            str(project.status),
            project.project_path,
            project.version,
        )

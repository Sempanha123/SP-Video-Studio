from __future__ import annotations

import json

from domain.script import Script
from domain.script_section import ScriptSection
from storage.database import SQLiteDatabase


class ScriptRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, script: Script, sections: list[ScriptSection]) -> Script:
        script.validate()
        for section in sections:
            section.validate()
            if section.script_id != script.script_id:
                raise ValueError("Section belongs to another script.")
        with self.database.connect() as connection, connection:
            self._insert_script(connection, script)
            for section in sections:
                self._insert_section(connection, section)
        return script

    def get_by_id(self, script_id: str) -> Script | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
        return Script.from_record(row) if row else None

    def get_primary_by_project(self, project_id: str) -> Script | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM scripts WHERE project_id = ? ORDER BY created_at ASC LIMIT 1",
                (project_id,),
            ).fetchone()
        return Script.from_record(row) if row else None

    def list_sections(self, script_id: str) -> list[ScriptSection]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM script_sections WHERE script_id = ? ORDER BY section_order ASC, created_at ASC",
                (script_id,),
            ).fetchall()
        return [ScriptSection.from_record(row) for row in rows]

    def get_section(self, section_id: str) -> ScriptSection | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM script_sections WHERE id = ?", (section_id,)
            ).fetchone()
        return ScriptSection.from_record(row) if row else None

    def section_belongs_to_project(self, section_id: str, project_id: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM script_sections ss
                JOIN scripts s ON s.id = ss.script_id
                WHERE ss.id = ? AND s.project_id = ?
                """,
                (section_id, project_id),
            ).fetchone()
        return row is not None

    def update_script(self, script: Script) -> Script:
        script.validate()
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE scripts SET title=?, language=?, status=?, pace=?, version=?, notes=?,
                    metadata_json=?, updated_at=? WHERE id=? AND project_id=?
                """,
                (
                    script.title, script.language, str(script.status), str(script.pace), script.version,
                    script.notes, json.dumps(script.metadata, ensure_ascii=False, separators=(",", ":")),
                    script.updated_at, script.script_id, script.project_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError("Script does not exist for this project.")
        return script

    def update_section(self, project_id: str, section: ScriptSection) -> ScriptSection:
        section.validate()
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE script_sections SET section_order=?, section_type=?, title=?, content=?, notes=?,
                    enabled=?, metadata_json=?, updated_at=?
                WHERE id=? AND script_id IN (SELECT id FROM scripts WHERE project_id=?)
                """,
                (
                    section.order, section.type, section.title, section.content, section.notes,
                    int(section.enabled), json.dumps(section.metadata, ensure_ascii=False, separators=(",", ":")),
                    section.updated_at, section.section_id, project_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError("Script section does not belong to this project.")
        return section

    def create_section(self, project_id: str, section: ScriptSection) -> ScriptSection:
        section.validate()
        with self.database.connect() as connection, connection:
            owner = connection.execute(
                "SELECT 1 FROM scripts WHERE id=? AND project_id=?", (section.script_id, project_id)
            ).fetchone()
            if owner is None:
                raise KeyError("Script does not belong to this project.")
            self._insert_section(connection, section)
        return section

    def delete_section(self, project_id: str, section_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                DELETE FROM script_sections
                WHERE id=? AND script_id IN (SELECT id FROM scripts WHERE project_id=?)
                """,
                (section_id, project_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("Script section does not belong to this project.")

    def replace_sections(self, project_id: str, script_id: str, sections: list[ScriptSection]) -> None:
        with self.database.connect() as connection, connection:
            owner = connection.execute(
                "SELECT 1 FROM scripts WHERE id=? AND project_id=?", (script_id, project_id)
            ).fetchone()
            if owner is None:
                raise KeyError("Script does not belong to this project.")
            connection.execute("DELETE FROM script_sections WHERE script_id=?", (script_id,))
            for section in sections:
                section.validate()
                if section.script_id != script_id:
                    raise ValueError("Section belongs to another script.")
                self._insert_section(connection, section)

    def save_order(self, project_id: str, script_id: str, sections: list[ScriptSection]) -> None:
        with self.database.connect() as connection, connection:
            owner = connection.execute(
                "SELECT 1 FROM scripts WHERE id=? AND project_id=?", (script_id, project_id)
            ).fetchone()
            if owner is None:
                raise KeyError("Script does not belong to this project.")
            for order, section in enumerate(sections):
                section.order = order
                connection.execute(
                    "UPDATE script_sections SET section_order=?, updated_at=? WHERE id=? AND script_id=?",
                    (order, section.updated_at, section.section_id, script_id),
                )

    def count_for_project(self, project_id: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM scripts WHERE project_id=?", (project_id,)).fetchone()
        return int(row["count"] if row else 0)

    @staticmethod
    def _insert_script(connection, script: Script) -> None:
        connection.execute(
            """
            INSERT INTO scripts(id, project_id, title, language, status, pace, version, notes,
                                metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                script.script_id, script.project_id, script.title, script.language, str(script.status),
                str(script.pace), script.version, script.notes,
                json.dumps(script.metadata, ensure_ascii=False, separators=(",", ":")),
                script.created_at, script.updated_at,
            ),
        )

    @staticmethod
    def _insert_section(connection, section: ScriptSection) -> None:
        connection.execute(
            """
            INSERT INTO script_sections(id, script_id, section_order, section_type, title, content,
                                        notes, enabled, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                section.section_id, section.script_id, section.order, section.type, section.title,
                section.content, section.notes, int(section.enabled),
                json.dumps(section.metadata, ensure_ascii=False, separators=(",", ":")),
                section.created_at, section.updated_at,
            ),
        )

from __future__ import annotations

import json

from domain.project import utc_now_iso
from domain.voice_profile import VoiceProfile
from storage.database import SQLiteDatabase


class VoiceRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def list_profiles(self) -> list[VoiceProfile]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM voice_profiles ORDER BY updated_at DESC, name COLLATE NOCASE").fetchall()
        return [VoiceProfile.from_record(row) for row in rows]

    def get_profile(self, voice_id: str) -> VoiceProfile | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM voice_profiles WHERE id=?", (voice_id,)).fetchone()
        return VoiceProfile.from_record(row) if row else None

    def create_profile(self, voice: VoiceProfile) -> VoiceProfile:
        voice.validate()
        if voice.is_builtin:
            raise ValueError("Built-in voices are immutable registry data.")
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO voice_profiles(
                    id,name,voice_type,language,category,engine_id,voice_description,
                    style_tags_json,description,reference_audio_path,settings_json,notes,
                    validated,duration_ms,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                self._values(voice),
            )
        return voice

    def update_profile(self, voice: VoiceProfile) -> VoiceProfile:
        voice.validate()
        if voice.is_builtin:
            raise ValueError("Built-in voices cannot be edited.")
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE voice_profiles SET name=?,voice_type=?,language=?,category=?,engine_id=?,
                    voice_description=?,style_tags_json=?,description=?,reference_audio_path=?,
                    settings_json=?,notes=?,validated=?,duration_ms=?,updated_at=? WHERE id=?
                """,
                (
                    voice.name, voice.type_code, voice.language, voice.category, voice.engine_id,
                    voice.voice_description, json.dumps(voice.style_tags, ensure_ascii=False),
                    voice.description, voice.reference_audio_path,
                    json.dumps(voice.settings, ensure_ascii=False, separators=(",", ":")),
                    voice.notes, int(voice.validated), int(voice.duration_ms), voice.updated_at, voice.voice_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError("Voice profile not found.")
        return voice

    def delete_profile(self, voice_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute("DELETE FROM voice_profiles WHERE id=?", (voice_id,))
            if cursor.rowcount == 0:
                raise KeyError("Voice profile not found.")
            connection.execute("DELETE FROM voice_preferences WHERE voice_id=?", (voice_id,))

    def preference(self, voice_id: str) -> dict[str, object]:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM voice_preferences WHERE voice_id=?", (voice_id,)).fetchone()
        if row is None:
            return {"favorite": False, "last_used_at": None, "usage_count": 0}
        return {
            "favorite": bool(row["favorite"]),
            "last_used_at": row["last_used_at"],
            "usage_count": int(row["usage_count"] or 0),
        }

    def all_preferences(self) -> dict[str, dict[str, object]]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM voice_preferences").fetchall()
        return {
            str(row["voice_id"]): {
                "favorite": bool(row["favorite"]),
                "last_used_at": row["last_used_at"],
                "usage_count": int(row["usage_count"] or 0),
            }
            for row in rows
        }

    def set_favorite(self, voice_id: str, favorite: bool) -> None:
        pref = self.preference(voice_id)
        self._upsert_preference(voice_id, bool(favorite), pref["last_used_at"], int(pref["usage_count"]))

    def mark_used(self, voice_id: str) -> None:
        pref = self.preference(voice_id)
        self._upsert_preference(voice_id, bool(pref["favorite"]), utc_now_iso(), int(pref["usage_count"]) + 1)

    def get_project_default_voice(self, project_id: str) -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT default_voice_id FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise KeyError("Project not found.")
        return str(row["default_voice_id"] or "")

    def set_project_default_voice(self, project_id: str, voice_id: str | None) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute("UPDATE projects SET default_voice_id=? WHERE id=?", (voice_id or None, project_id))
            if cursor.rowcount == 0:
                raise KeyError("Project not found.")

    def get_section_voice_override(self, section_id: str) -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT voice_override_id FROM script_sections WHERE id=?", (section_id,)).fetchone()
        if row is None:
            raise KeyError("Script section not found.")
        return str(row["voice_override_id"] or "")

    def set_section_voice_override(self, project_id: str, section_id: str, voice_id: str | None) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE script_sections SET voice_override_id=?
                WHERE id=? AND script_id IN (SELECT id FROM scripts WHERE project_id=?)
                """,
                (voice_id or None, section_id, project_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("Script section does not belong to this project.")

    def assignment_count(self, voice_id: str) -> int:
        with self.database.connect() as connection:
            project_count = connection.execute("SELECT COUNT(*) AS n FROM projects WHERE default_voice_id=?", (voice_id,)).fetchone()["n"]
            section_count = connection.execute("SELECT COUNT(*) AS n FROM script_sections WHERE voice_override_id=?", (voice_id,)).fetchone()["n"]
        return int(project_count) + int(section_count)

    def clear_assignments(self, voice_id: str) -> None:
        with self.database.connect() as connection, connection:
            connection.execute("UPDATE projects SET default_voice_id=NULL WHERE default_voice_id=?", (voice_id,))
            connection.execute("UPDATE script_sections SET voice_override_id=NULL WHERE voice_override_id=?", (voice_id,))

    def duplicate_project_assignments(self, source_project_id: str, duplicate_project_id: str) -> None:
        with self.database.connect() as connection, connection:
            source = connection.execute("SELECT default_voice_id FROM projects WHERE id=?", (source_project_id,)).fetchone()
            if source is None:
                raise KeyError("Source project not found.")
            connection.execute("UPDATE projects SET default_voice_id=? WHERE id=?", (source["default_voice_id"], duplicate_project_id))
            source_rows = connection.execute(
                """
                SELECT ss.section_order, ss.voice_override_id
                FROM script_sections ss JOIN scripts s ON s.id=ss.script_id
                WHERE s.project_id=? ORDER BY ss.section_order
                """,
                (source_project_id,),
            ).fetchall()
            for row in source_rows:
                if not row["voice_override_id"]:
                    continue
                connection.execute(
                    """
                    UPDATE script_sections SET voice_override_id=?
                    WHERE section_order=? AND script_id IN (SELECT id FROM scripts WHERE project_id=?)
                    """,
                    (row["voice_override_id"], row["section_order"], duplicate_project_id),
                )

    def _upsert_preference(self, voice_id: str, favorite: bool, last_used_at, usage_count: int) -> None:
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO voice_preferences(voice_id,favorite,last_used_at,usage_count)
                VALUES(?,?,?,?)
                ON CONFLICT(voice_id) DO UPDATE SET favorite=excluded.favorite,
                    last_used_at=excluded.last_used_at,usage_count=excluded.usage_count
                """,
                (voice_id, int(favorite), last_used_at, int(usage_count)),
            )

    @staticmethod
    def _values(voice: VoiceProfile) -> tuple[object, ...]:
        return (
            voice.voice_id, voice.name, voice.type_code, voice.language, voice.category, voice.engine_id,
            voice.voice_description, json.dumps(voice.style_tags, ensure_ascii=False), voice.description,
            voice.reference_audio_path, json.dumps(voice.settings, ensure_ascii=False, separators=(",", ":")),
            voice.notes, int(voice.validated), int(voice.duration_ms), voice.created_at, voice.updated_at,
        )

from __future__ import annotations

import json
from domain.generated_audio import GeneratedAudio
from storage.database import SQLiteDatabase


class GeneratedAudioRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, item: GeneratedAudio) -> GeneratedAudio:
        with self.database.connect() as connection, connection:
            if item.active:
                connection.execute("UPDATE generated_audio SET active=0 WHERE project_id=?", (item.project_id,))
            connection.execute(
                """INSERT INTO generated_audio(id,project_id,script_id,section_id,engine,model_id,language,voice_mode,
                    voice_config_json,text_hash,file_path,duration_ms,sample_rate,channels,created_at,generation_settings_json,
                    status,active,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                self._values(item),
            )
        return item

    def get(self, generated_audio_id: str) -> GeneratedAudio | None:
        with self.database.connect() as connection:
            row=connection.execute("SELECT * FROM generated_audio WHERE id=?",(generated_audio_id,)).fetchone()
        return GeneratedAudio.from_record(row) if row else None

    def get_by_id(self, generated_audio_id: str) -> GeneratedAudio | None:
        return self.get(generated_audio_id)

    def list_for_project(self, project_id: str) -> list[GeneratedAudio]:
        with self.database.connect() as connection:
            rows=connection.execute("SELECT * FROM generated_audio WHERE project_id=? ORDER BY created_at DESC,id DESC",(project_id,)).fetchall()
        return [GeneratedAudio.from_record(row) for row in rows]

    def list_for_section(self, project_id: str, section_id: str) -> list[GeneratedAudio]:
        with self.database.connect() as connection:
            rows=connection.execute("SELECT * FROM generated_audio WHERE project_id=? AND section_id=? ORDER BY created_at DESC",(project_id,section_id)).fetchall()
        return [GeneratedAudio.from_record(row) for row in rows]

    def list_for_speech_block(self, project_id: str, block_id: str) -> list[GeneratedAudio]:
        # Metadata JSON is intentionally filtered in Python so SQLite JSON1 is not required.
        result=[]
        for item in self.list_for_project(project_id):
            meta=dict(getattr(item,"metadata",{}) or {})
            if str(meta.get("speechBlockId","") or "")==str(block_id):result.append(item)
        return result

    def active_for_project(self, project_id: str) -> GeneratedAudio | None:
        with self.database.connect() as connection:
            row=connection.execute("SELECT * FROM generated_audio WHERE project_id=? AND active=1 ORDER BY created_at DESC LIMIT 1",(project_id,)).fetchone()
        return GeneratedAudio.from_record(row) if row else None

    def set_active(self, project_id: str, generated_audio_id: str) -> None:
        with self.database.connect() as connection, connection:
            owner=connection.execute("SELECT 1 FROM generated_audio WHERE id=? AND project_id=?",(generated_audio_id,project_id)).fetchone()
            if owner is None:raise KeyError("Generated audio does not belong to this project.")
            connection.execute("UPDATE generated_audio SET active=0 WHERE project_id=?",(project_id,))
            connection.execute("UPDATE generated_audio SET active=1 WHERE id=?",(generated_audio_id,))

    def delete(self, project_id: str, generated_audio_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor=connection.execute("DELETE FROM generated_audio WHERE id=? AND project_id=?",(generated_audio_id,project_id))
            if cursor.rowcount==0:raise KeyError("Generated audio does not belong to this project.")

    @staticmethod
    def _values(item: GeneratedAudio) -> tuple[object,...]:
        return (item.generated_audio_id,item.project_id,item.script_id,item.section_id,item.engine,item.model_id,item.language,item.voice_mode,
                json.dumps(item.voice_config,ensure_ascii=False,separators=(",",":")),item.text_hash,item.file_path,int(item.duration_ms),int(item.sample_rate),int(item.channels),item.created_at,
                json.dumps(item.generation_settings,ensure_ascii=False,separators=(",",":")),item.status_code,int(item.active),json.dumps(item.metadata,ensure_ascii=False,separators=(",",":")))

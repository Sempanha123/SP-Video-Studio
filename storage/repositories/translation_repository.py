from __future__ import annotations

import json
from collections.abc import Iterable

from domain.project import utc_now_iso
from domain.translation import Translation
from domain.translation_segment import TranslationSegment
from storage.database import SQLiteDatabase


class TranslationRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, translation: Translation, segments: Iterable[TranslationSegment]) -> Translation:
        translation.validate()
        items = list(segments)
        for segment in items:
            segment.validate()
            if segment.translation_id != translation.translation_id:
                raise ValueError("Translation segment ownership mismatch.")
        with self.database.connect() as connection, connection:
            self._insert_translation(connection, translation)
            for segment in items:
                self._insert_segment(connection, segment)
        return translation

    def get(self, translation_id: str) -> Translation | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM translations WHERE id=?", (translation_id,)).fetchone()
        return Translation.from_record(row) if row else None

    def list_for_project(self, project_id: str) -> list[Translation]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM translations WHERE project_id=? ORDER BY updated_at DESC, created_at DESC",
                (project_id,),
            ).fetchall()
        return [Translation.from_record(row) for row in rows]

    def list_for_source(self, project_id: str, source_type: str, source_id: str) -> list[Translation]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM translations
                WHERE project_id=? AND source_type=? AND source_id=?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (project_id, source_type, source_id),
            ).fetchall()
        return [Translation.from_record(row) for row in rows]

    def latest_for_source(
        self,
        project_id: str,
        source_type: str,
        source_id: str,
        target_language: str | None = None,
    ) -> Translation | None:
        sql = """
            SELECT * FROM translations
            WHERE project_id=? AND source_type=? AND source_id=?
        """
        params: list[object] = [project_id, source_type, source_id]
        if target_language:
            sql += " AND target_language=?"
            params.append(target_language)
        sql += " ORDER BY updated_at DESC, created_at DESC LIMIT 1"
        with self.database.connect() as connection:
            row = connection.execute(sql, tuple(params)).fetchone()
        return Translation.from_record(row) if row else None

    def segments(self, translation_id: str) -> list[TranslationSegment]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM translation_segments WHERE translation_id=? ORDER BY segment_order ASC, created_at ASC",
                (translation_id,),
            ).fetchall()
        return [TranslationSegment.from_record(row) for row in rows]

    def segment(self, segment_id: str) -> TranslationSegment | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM translation_segments WHERE id=?", (segment_id,)).fetchone()
        return TranslationSegment.from_record(row) if row else None

    def update_translation(self, translation: Translation) -> Translation:
        translation.validate()
        translation.updated_at = utc_now_iso()
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE translations SET source_language=?, target_language=?, engine_id=?, model_id=?,
                    status=?, source_fingerprint=?, settings_json=?, metadata_json=?, updated_at=?
                WHERE id=? AND project_id=?
                """,
                (
                    translation.source_language,
                    translation.target_language,
                    translation.engine_id,
                    translation.model_id,
                    translation.status_code,
                    translation.source_fingerprint,
                    json.dumps(translation.settings, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(translation.metadata, ensure_ascii=False, separators=(",", ":")),
                    translation.updated_at,
                    translation.translation_id,
                    translation.project_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError("Translation does not belong to this project.")
        return translation

    def update_segment(self, project_id: str, segment: TranslationSegment) -> TranslationSegment:
        segment.validate()
        segment.updated_at = utc_now_iso()
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE translation_segments
                SET source_segment_id=?, segment_order=?, start_ms=?, end_ms=?, source_text=?, source_hash=?,
                    machine_translation=?, translated_text=?, status=?, edited=?, reviewed=?, locked=?, confidence=?,
                    notes=?, metadata_json=?, updated_at=?
                WHERE id=? AND translation_id IN (SELECT id FROM translations WHERE project_id=?)
                """,
                (
                    segment.source_segment_id,
                    segment.order,
                    segment.start_ms,
                    segment.end_ms,
                    segment.source_text,
                    segment.source_hash,
                    segment.machine_translation,
                    segment.translated_text,
                    segment.status_code,
                    int(segment.edited),
                    int(segment.reviewed),
                    int(segment.locked),
                    segment.confidence,
                    segment.notes,
                    json.dumps(segment.metadata, ensure_ascii=False, separators=(",", ":")),
                    segment.updated_at,
                    segment.segment_id,
                    project_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError("Translation segment does not belong to this project.")
        return segment

    def create_segment(self, project_id: str, segment: TranslationSegment) -> TranslationSegment:
        segment.validate()
        with self.database.connect() as connection, connection:
            owner = connection.execute(
                "SELECT 1 FROM translations WHERE id=? AND project_id=?",
                (segment.translation_id, project_id),
            ).fetchone()
            if owner is None:
                raise KeyError("Translation does not belong to this project.")
            self._insert_segment(connection, segment)
        return segment

    def replace_segments(self, project_id: str, translation_id: str, segments: Iterable[TranslationSegment]) -> None:
        items = list(segments)
        with self.database.connect() as connection, connection:
            owner = connection.execute(
                "SELECT 1 FROM translations WHERE id=? AND project_id=?",
                (translation_id, project_id),
            ).fetchone()
            if owner is None:
                raise KeyError("Translation does not belong to this project.")
            connection.execute("DELETE FROM translation_segments WHERE translation_id=?", (translation_id,))
            for segment in items:
                segment.validate()
                if segment.translation_id != translation_id:
                    raise ValueError("Translation segment ownership mismatch.")
                self._insert_segment(connection, segment)

    def search_segments(self, translation_id: str, query: str) -> list[TranslationSegment]:
        needle = f"%{(query or '').strip()}%"
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM translation_segments
                WHERE translation_id=? AND (source_text LIKE ? COLLATE NOCASE OR translated_text LIKE ? COLLATE NOCASE)
                ORDER BY segment_order ASC
                """,
                (translation_id, needle, needle),
            ).fetchall()
        return [TranslationSegment.from_record(row) for row in rows]

    def delete(self, project_id: str, translation_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM translations WHERE id=? AND project_id=?", (translation_id, project_id)
            )
            if cursor.rowcount == 0:
                raise KeyError("Translation does not belong to this project.")

    def count_for_project(self, project_id: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM translations WHERE project_id=?", (project_id,)
            ).fetchone()
        return int(row["count"] if row else 0)

    @staticmethod
    def _insert_translation(connection, translation: Translation) -> None:
        connection.execute(
            """
            INSERT INTO translations(
                id, project_id, source_type, source_id, source_language, target_language,
                engine_id, model_id, status, source_fingerprint, settings_json, metadata_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                translation.translation_id,
                translation.project_id,
                translation.source_type_code,
                translation.source_id,
                translation.source_language,
                translation.target_language,
                translation.engine_id,
                translation.model_id,
                translation.status_code,
                translation.source_fingerprint,
                json.dumps(translation.settings, ensure_ascii=False, separators=(",", ":")),
                json.dumps(translation.metadata, ensure_ascii=False, separators=(",", ":")),
                translation.created_at,
                translation.updated_at,
            ),
        )

    @staticmethod
    def _insert_segment(connection, segment: TranslationSegment) -> None:
        connection.execute(
            """
            INSERT INTO translation_segments(
                id, translation_id, source_segment_id, segment_order, start_ms, end_ms,
                source_text, source_hash, machine_translation, translated_text, status,
                edited, reviewed, locked, confidence, notes, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                segment.segment_id,
                segment.translation_id,
                segment.source_segment_id,
                segment.order,
                segment.start_ms,
                segment.end_ms,
                segment.source_text,
                segment.source_hash,
                segment.machine_translation,
                segment.translated_text,
                segment.status_code,
                int(segment.edited),
                int(segment.reviewed),
                int(segment.locked),
                segment.confidence,
                segment.notes,
                json.dumps(segment.metadata, ensure_ascii=False, separators=(",", ":")),
                segment.created_at,
                segment.updated_at,
            ),
        )

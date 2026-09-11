from __future__ import annotations

import json

from domain.transcript import Transcript
from domain.transcript_segment import TranscriptSegment
from domain.transcript_word import TranscriptWord
from storage.database import SQLiteDatabase


class TranscriptRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create_with_segments(self, transcript: Transcript, segments: list[TranscriptSegment]) -> Transcript:
        transcript.validate()
        with self.database.connect() as connection, connection:
            if transcript.active:
                connection.execute("UPDATE transcripts SET active=0 WHERE media_id=?", (transcript.media_id,))
            connection.execute(
                """
                INSERT INTO transcripts(
                    id, project_id, media_id, engine, model_id, model_version, language_mode,
                    detected_language, language_probability, device, compute_type, duration_ms,
                    created_at, updated_at, status, source_fingerprint, settings_json, metadata_json, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._transcript_values(transcript),
            )
            for segment in segments:
                segment.validate()
                if segment.transcript_id != transcript.transcript_id:
                    raise ValueError("Transcript segment ownership mismatch.")
                self._insert_segment(connection, segment)
                for word in segment.words:
                    if word.segment_id != segment.segment_id:
                        raise ValueError("Transcript word ownership mismatch.")
                    self._insert_word(connection, word)
        return transcript

    def get(self, transcript_id: str) -> Transcript | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM transcripts WHERE id=?", (transcript_id,)).fetchone()
        return Transcript.from_record(row) if row else None

    def list_for_media(self, project_id: str, media_id: str) -> list[Transcript]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcripts WHERE project_id=? AND media_id=? ORDER BY created_at DESC, id DESC",
                (project_id, media_id),
            ).fetchall()
        return [Transcript.from_record(row) for row in rows]

    def list_for_project(self, project_id: str) -> list[Transcript]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcripts WHERE project_id=? ORDER BY created_at DESC, id DESC", (project_id,)
            ).fetchall()
        return [Transcript.from_record(row) for row in rows]

    def active_for_media(self, project_id: str, media_id: str) -> Transcript | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM transcripts WHERE project_id=? AND media_id=? AND active=1 ORDER BY created_at DESC LIMIT 1",
                (project_id, media_id),
            ).fetchone()
        return Transcript.from_record(row) if row else None

    def segments(self, transcript_id: str) -> list[TranscriptSegment]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcript_segments WHERE transcript_id=? ORDER BY segment_order ASC, start_ms ASC",
                (transcript_id,),
            ).fetchall()
            segments = [TranscriptSegment.from_record(row) for row in rows]
            for segment in segments:
                word_rows = connection.execute(
                    "SELECT * FROM transcript_words WHERE segment_id=? ORDER BY word_order ASC", (segment.segment_id,)
                ).fetchall()
                segment.words = [TranscriptWord.from_record(row) for row in word_rows]
        return segments

    def set_active(self, project_id: str, media_id: str, transcript_id: str) -> None:
        with self.database.connect() as connection, connection:
            owner = connection.execute(
                "SELECT 1 FROM transcripts WHERE id=? AND project_id=? AND media_id=?",
                (transcript_id, project_id, media_id),
            ).fetchone()
            if owner is None:
                raise KeyError("Transcript does not belong to this project media.")
            connection.execute("UPDATE transcripts SET active=0 WHERE media_id=?", (media_id,))
            connection.execute("UPDATE transcripts SET active=1 WHERE id=?", (transcript_id,))

    def update_status(self, transcript_id: str, status: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                "UPDATE transcripts SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, transcript_id)
            )
            if cursor.rowcount == 0:
                raise KeyError("Transcript not found.")

    def update_segment_text(self, transcript_id: str, segment_id: str, text: str, *, edited: bool) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE transcript_segments
                   SET text=?, edited=?, updated_at=CURRENT_TIMESTAMP
                 WHERE id=? AND transcript_id=?
                """,
                (text, int(edited), segment_id, transcript_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("Transcript segment not found.")

    def reset_segment(self, transcript_id: str, segment_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE transcript_segments
                   SET text=original_text, edited=0, updated_at=CURRENT_TIMESTAMP
                 WHERE id=? AND transcript_id=?
                """,
                (segment_id, transcript_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("Transcript segment not found.")

    def delete(self, project_id: str, transcript_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM transcripts WHERE id=? AND project_id=?", (transcript_id, project_id)
            )
            if cursor.rowcount == 0:
                raise KeyError("Transcript does not belong to this project.")

    def delete_for_media(self, media_id: str) -> None:
        with self.database.connect() as connection, connection:
            connection.execute("DELETE FROM transcripts WHERE media_id=?", (media_id,))

    def search_segments(self, transcript_id: str, query: str) -> list[TranscriptSegment]:
        clean = query.strip().lower()
        if not clean:
            return self.segments(transcript_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM transcript_segments
                 WHERE transcript_id=? AND LOWER(text) LIKE ? ESCAPE '\\'
                 ORDER BY segment_order ASC
                """,
                (transcript_id, f"%{self._escape_like(clean)}%"),
            ).fetchall()
        return [TranscriptSegment.from_record(row) for row in rows]

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _transcript_values(item: Transcript) -> tuple[object, ...]:
        return (
            item.transcript_id, item.project_id, item.media_id, item.engine, item.model_id, item.model_version,
            item.language_mode, item.detected_language, item.language_probability, item.device, item.compute_type,
            int(item.duration_ms), item.created_at, item.updated_at, item.status_code, item.source_fingerprint,
            json.dumps(item.settings, ensure_ascii=False, separators=(",", ":")),
            json.dumps(item.metadata, ensure_ascii=False, separators=(",", ":")), int(item.active),
        )

    @staticmethod
    def _insert_segment(connection, item: TranscriptSegment) -> None:
        connection.execute(
            """
            INSERT INTO transcript_segments(
                id, transcript_id, segment_order, start_ms, end_ms, text, original_text,
                confidence, no_speech_probability, temperature, edited, created_at, updated_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.segment_id, item.transcript_id, item.order, item.start_ms, item.end_ms, item.text,
                item.original_text, item.confidence, item.no_speech_probability, item.temperature, int(item.edited),
                item.created_at, item.updated_at,
                json.dumps(item.metadata, ensure_ascii=False, separators=(",", ":")),
            ),
        )

    @staticmethod
    def _insert_word(connection, item: TranscriptWord) -> None:
        connection.execute(
            """
            INSERT INTO transcript_words(
                id, segment_id, word_order, start_ms, end_ms, text, probability, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.word_id, item.segment_id, item.order, item.start_ms, item.end_ms, item.text, item.probability,
                json.dumps(item.metadata, ensure_ascii=False, separators=(",", ":")),
            ),
        )

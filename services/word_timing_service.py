from __future__ import annotations

import json
import re
from uuid import uuid4

from domain.phase22_errors import SpeechBlockInvalid
from domain.transcript_word import TranscriptWord
from services.frame_time_service import FrameTimeService


_PUNCT_RIGHT = re.compile(r"^[,.;:!?%\)\]\}]+$")
_PUNCT_LEFT = re.compile(r"^[\(\[\{]+$")


class WordTimingService:
    def __init__(self, transcript_repository, frame_time: FrameTimeService | None = None, subtitle_repository=None) -> None:
        self.transcripts = transcript_repository
        self.frames = frame_time or FrameTimeService()
        self.subtitles = subtitle_repository

    def words(self, project_id: str, segment_id: str) -> list[TranscriptWord]:
        with self.transcripts.database.connect() as c:
            rows = c.execute(
                """SELECT w.* FROM transcript_words w JOIN transcript_segments s ON s.id=w.segment_id
                   JOIN transcripts t ON t.id=s.transcript_id WHERE w.segment_id=? AND t.project_id=? ORDER BY w.word_order""",
                (segment_id, project_id),
            ).fetchall()
        return [TranscriptWord.from_record(row) for row in rows]

    def update_word(self, project_id: str, word_id: str, *, text: str | None = None, start_ms: int | None = None,
                    end_ms: int | None = None, fps: int | None = None, snap_to_frame: bool = False) -> TranscriptWord:
        word, segment_id = self._owned(project_id, word_id)
        if text is not None:
            word.text = str(text)
        if start_ms is not None:
            word.start_ms = self.frames.snap_ms(start_ms, fps) if snap_to_frame and fps else int(start_ms)
        if end_ms is not None:
            word.end_ms = self.frames.snap_ms(end_ms, fps) if snap_to_frame and fps else int(end_ms)
        word.validate()
        with self.transcripts.database.connect() as c, c:
            c.execute("UPDATE transcript_words SET start_ms=?,end_ms=?,text=?,metadata_json=? WHERE id=?",
                      (word.start_ms, word.end_ms, word.text, json.dumps(word.metadata, ensure_ascii=False, separators=(",", ":")), word.id))
        self._rebuild_segment(project_id, segment_id)
        return word

    def merge(self, project_id: str, first_id: str, second_id: str) -> TranscriptWord:
        first, segment_id = self._owned(project_id, first_id); second, segment2 = self._owned(project_id, second_id)
        if segment_id != segment2 or second.order != first.order + 1:
            raise SpeechBlockInvalid("Only adjacent words in the same transcript segment can be merged.")
        first.text = self._join_tokens([first.text, second.text]); first.end_ms = second.end_ms
        with self.transcripts.database.connect() as c, c:
            c.execute("UPDATE transcript_words SET text=?,end_ms=? WHERE id=?", (first.text, first.end_ms, first.id))
            c.execute("DELETE FROM transcript_words WHERE id=?", (second.id,))
            c.execute("UPDATE transcript_words SET word_order=word_order-1 WHERE segment_id=? AND word_order>?", (segment_id, second.order))
        self._rebuild_segment(project_id, segment_id)
        return first

    def split(self, project_id: str, word_id: str, first_text: str, second_text: str, *, split_ms: int | None = None) -> tuple[TranscriptWord, TranscriptWord]:
        word, segment_id = self._owned(project_id, word_id)
        a = first_text.strip(); b = second_text.strip()
        if not a or not b:
            raise SpeechBlockInvalid("Both split word parts require text.")
        point = int(split_ms) if split_ms is not None else word.start_ms + max(1, (word.end_ms - word.start_ms) // 2)
        if point <= word.start_ms or point >= word.end_ms:
            raise SpeechBlockInvalid("Choose a split timestamp inside the word timing.")
        second = TranscriptWord(segment_id=segment_id, order=word.order + 1, start_ms=point, end_ms=word.end_ms, text=b, probability=word.probability,
                                metadata={**word.metadata, "splitFrom": word.id})
        word.text = a; word.end_ms = point; word.metadata["split"] = True
        with self.transcripts.database.connect() as c, c:
            c.execute("UPDATE transcript_words SET word_order=word_order+1 WHERE segment_id=? AND word_order>?", (segment_id, word.order))
            c.execute("UPDATE transcript_words SET text=?,end_ms=?,metadata_json=? WHERE id=?", (word.text, word.end_ms, json.dumps(word.metadata, ensure_ascii=False), word.id))
            c.execute("INSERT INTO transcript_words(id,segment_id,word_order,start_ms,end_ms,text,probability,metadata_json) VALUES(?,?,?,?,?,?,?,?)",
                      (second.id, segment_id, second.order, second.start_ms, second.end_ms, second.text, second.probability, json.dumps(second.metadata, ensure_ascii=False)))
        self._rebuild_segment(project_id, segment_id)
        return word, second

    def _owned(self, project_id: str, word_id: str) -> tuple[TranscriptWord, str]:
        with self.transcripts.database.connect() as c:
            row = c.execute(
                """SELECT w.* FROM transcript_words w JOIN transcript_segments s ON s.id=w.segment_id
                   JOIN transcripts t ON t.id=s.transcript_id WHERE w.id=? AND t.project_id=?""", (word_id, project_id)
            ).fetchone()
        if row is None:
            raise KeyError("Transcript word not found.")
        item = TranscriptWord.from_record(row)
        return item, item.segment_id

    def _rebuild_segment(self, project_id: str, segment_id: str) -> str:
        words = self.words(project_id, segment_id)
        text = self._join_tokens([word.text for word in words])
        with self.transcripts.database.connect() as c, c:
            c.execute(
                """UPDATE transcript_segments SET text=?,edited=1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND transcript_id IN
                   (SELECT id FROM transcripts WHERE project_id=?)""", (text, segment_id, project_id)
            )
        self._sync_subtitle_words(project_id, segment_id, text, words)
        return text

    def _sync_subtitle_words(self, project_id: str, segment_id: str, text: str, words: list[TranscriptWord]) -> None:
        if self.subtitles is None or not hasattr(self.subtitles, "database"):
            return
        try:
            with self.subtitles.database.connect() as c, c:
                rows=c.execute("""SELECT c.id AS cue_id,t.source_type,t.is_bilingual,t.metadata_json FROM subtitle_cues c
                                  JOIN subtitle_tracks t ON t.id=c.track_id WHERE t.project_id=? AND c.source_segment_id=?
                                  AND (t.source_type='transcript' OR t.is_bilingual=1)""",(project_id,segment_id)).fetchall()
                for row in rows:
                    primary_source=True
                    if bool(row["is_bilingual"]):
                        try: primary_source=json.loads(str(row["metadata_json"] or "{}")).get("primaryOrder","source")=="source"
                        except Exception: primary_source=True
                        c.execute("UPDATE subtitle_cues SET text=? WHERE id=?" if primary_source else "UPDATE subtitle_cues SET secondary_text=? WHERE id=?",(text,str(row["cue_id"])))
                    else:
                        c.execute("UPDATE subtitle_cues SET text=? WHERE id=?",(text,str(row["cue_id"])))
                    if primary_source:
                        cue_id=str(row["cue_id"]); c.execute("DELETE FROM subtitle_words WHERE cue_id=?",(cue_id,))
                        for order,word in enumerate(words):
                            c.execute("INSERT INTO subtitle_words(id,cue_id,word_order,text,start_ms,end_ms,probability,highlight_group,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                                      (str(uuid4()),cue_id,order,word.text,word.start_ms,word.end_ms,word.probability,None,json.dumps(word.metadata,ensure_ascii=False,separators=(",",":"))))
        except Exception:
            # Transcript edit remains canonical even if an older project has no subtitle-word tables yet.
            return

    @staticmethod
    def _join_tokens(tokens: list[str]) -> str:
        result = ""
        previous = ""
        for raw in tokens:
            token = str(raw or "")
            stripped = token.strip()
            if not stripped:
                continue
            if not result:
                result = stripped
            elif token[:1].isspace():
                result += token
            elif _PUNCT_RIGHT.match(stripped):
                result += stripped
            elif _PUNCT_LEFT.match(previous.strip()):
                result += stripped
            else:
                result += " " + stripped
            previous = stripped
        return result.strip()

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Iterable

from domain.project import utc_now_iso
from domain.subtitle import SubtitleTrack
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle
from domain.subtitle_word import SubtitleWord
from storage.database import SQLiteDatabase


class SubtitleRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create_track(self, track: SubtitleTrack, style: SubtitleStyle, cues: Iterable[SubtitleCue]) -> SubtitleTrack:
        track.validate(); style.validate()
        items = list(cues)
        if style.project_id != track.project_id:
            raise ValueError("Subtitle style ownership mismatch.")
        track.style_id = style.style_id
        with self.database.connect() as c, c:
            if track.is_default:
                c.execute("UPDATE subtitle_tracks SET is_default=0 WHERE project_id=?", (track.project_id,))
            self._insert_style(c, style)
            self._insert_track(c, track)
            for cue in items:
                if cue.track_id != track.track_id:
                    raise ValueError("Subtitle cue ownership mismatch.")
                cue.validate(); self._insert_cue(c, cue)
                for word in cue.words:
                    if word.cue_id != cue.cue_id:
                        raise ValueError("Subtitle word ownership mismatch.")
                    self._insert_word(c, word)
        return track

    def get_track(self, track_id: str) -> SubtitleTrack | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM subtitle_tracks WHERE id=?", (track_id,)).fetchone()
        return SubtitleTrack.from_record(row) if row else None

    def list_for_project(self, project_id: str) -> list[SubtitleTrack]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM subtitle_tracks WHERE project_id=? ORDER BY is_default DESC, updated_at DESC", (project_id,)).fetchall()
        return [SubtitleTrack.from_record(row) for row in rows]

    def list_for_source(self, project_id: str, source_type: str, source_id: str) -> list[SubtitleTrack]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM subtitle_tracks WHERE project_id=? AND source_type=? AND source_id=? ORDER BY updated_at DESC", (project_id, source_type, source_id)).fetchall()
        return [SubtitleTrack.from_record(row) for row in rows]

    def default_for_project(self, project_id: str) -> SubtitleTrack | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM subtitle_tracks WHERE project_id=? AND is_default=1 LIMIT 1", (project_id,)).fetchone()
        return SubtitleTrack.from_record(row) if row else None

    def cues(self, track_id: str) -> list[SubtitleCue]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM subtitle_cues WHERE track_id=? ORDER BY start_ms, cue_order, created_at", (track_id,)).fetchall()
            result = [SubtitleCue.from_record(row) for row in rows]
            for cue in result:
                words = c.execute("SELECT * FROM subtitle_words WHERE cue_id=? ORDER BY word_order", (cue.cue_id,)).fetchall()
                cue.words = [SubtitleWord.from_record(row) for row in words]
        return result

    def cue(self, cue_id: str) -> SubtitleCue | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM subtitle_cues WHERE id=?", (cue_id,)).fetchone()
            if not row:
                return None
            cue = SubtitleCue.from_record(row)
            words = c.execute("SELECT * FROM subtitle_words WHERE cue_id=? ORDER BY word_order", (cue_id,)).fetchall()
            cue.words = [SubtitleWord.from_record(item) for item in words]
        return cue

    def style(self, style_id: str) -> SubtitleStyle | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM subtitle_styles WHERE id=?", (style_id,)).fetchone()
        return SubtitleStyle.from_record(row) if row else None

    def update_track(self, track: SubtitleTrack) -> SubtitleTrack:
        track.validate(); track.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            if track.is_default:
                c.execute("UPDATE subtitle_tracks SET is_default=0 WHERE project_id=? AND id<>?", (track.project_id, track.track_id))
            cur = c.execute("""UPDATE subtitle_tracks SET name=?, language=?, track_type=?, source_type=?, source_id=?, source_language=?, status=?, style_id=?, is_default=?, is_bilingual=?, secondary_language=?, metadata_json=?, updated_at=? WHERE id=? AND project_id=?""",
                (track.name, track.language, track.track_type_code, track.source_type, track.source_id, track.source_language,
                 track.status_code, track.style_id, int(track.is_default), int(track.is_bilingual), track.secondary_language,
                 json.dumps(track.metadata, ensure_ascii=False, separators=(",", ":")), track.updated_at, track.track_id, track.project_id))
            if cur.rowcount == 0: raise KeyError("Subtitle track does not belong to this project.")
        return track

    def update_style(self, style: SubtitleStyle) -> SubtitleStyle:
        style.validate(); style.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            cur = c.execute("""UPDATE subtitle_styles SET name=?, font_family=?, font_size=?, font_weight=?, italic=?, text_color=?, secondary_text_color=?, outline_color=?, outline_width=?, shadow_enabled=?, shadow_offset=?, background_enabled=?, background_color=?, background_opacity=?, alignment=?, vertical_position=?, horizontal_margin=?, vertical_margin=?, max_lines=?, max_chars_per_line=?, line_spacing=?, highlight_color=?, highlight_text_color=?, secondary_scale=?, metadata_json=?, updated_at=? WHERE id=? AND project_id=?""",
                (style.name, style.font_family, style.font_size, style.font_weight, int(style.italic), style.text_color,
                 style.secondary_text_color, style.outline_color, style.outline_width, int(style.shadow_enabled), style.shadow_offset,
                 int(style.background_enabled), style.background_color, style.background_opacity, style.alignment,
                 style.vertical_position, style.horizontal_margin, style.vertical_margin, style.max_lines,
                 style.max_chars_per_line, style.line_spacing, style.highlight_color, style.highlight_text_color,
                 style.secondary_scale, json.dumps(style.metadata, ensure_ascii=False, separators=(",", ":")),
                 style.updated_at, style.style_id, style.project_id))
            if cur.rowcount == 0: raise KeyError("Subtitle style does not belong to this project.")
        return style

    def update_cue(self, project_id: str, cue: SubtitleCue) -> SubtitleCue:
        cue.validate(); cue.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            cur = c.execute("""UPDATE subtitle_cues SET cue_order=?, start_ms=?, end_ms=?, text=?, secondary_text=?, position=?, alignment=?, style_override_json=?, edited=?, locked=?, source_segment_id=?, source_hash=?, metadata_json=?, updated_at=? WHERE id=? AND track_id IN (SELECT id FROM subtitle_tracks WHERE project_id=?)""",
                (cue.order, cue.start_ms, cue.end_ms, cue.text, cue.secondary_text, cue.position, cue.alignment,
                 json.dumps(cue.style_override, ensure_ascii=False, separators=(",", ":")), int(cue.edited), int(cue.locked),
                 cue.source_segment_id, cue.source_hash, json.dumps(cue.metadata, ensure_ascii=False, separators=(",", ":")),
                 cue.updated_at, cue.cue_id, project_id))
            if cur.rowcount == 0: raise KeyError("Subtitle cue does not belong to this project.")
        return cue

    def add_cue(self, project_id: str, cue: SubtitleCue) -> SubtitleCue:
        cue.validate()
        with self.database.connect() as c, c:
            owner = c.execute("SELECT 1 FROM subtitle_tracks WHERE id=? AND project_id=?", (cue.track_id, project_id)).fetchone()
            if owner is None: raise KeyError("Subtitle track does not belong to this project.")
            self._insert_cue(c, cue)
            for word in cue.words: self._insert_word(c, word)
        return cue

    def replace_cues(self, project_id: str, track_id: str, cues: Iterable[SubtitleCue]) -> None:
        items = list(cues)
        with self.database.connect() as c, c:
            owner = c.execute("SELECT 1 FROM subtitle_tracks WHERE id=? AND project_id=?", (track_id, project_id)).fetchone()
            if owner is None: raise KeyError("Subtitle track does not belong to this project.")
            c.execute("DELETE FROM subtitle_cues WHERE track_id=?", (track_id,))
            for cue in items:
                cue.track_id = track_id; cue.validate(); self._insert_cue(c, cue)
                for word in cue.words:
                    word.cue_id = cue.cue_id; self._insert_word(c, word)

    def delete_cue(self, project_id: str, cue_id: str) -> None:
        with self.database.connect() as c, c:
            cur = c.execute("DELETE FROM subtitle_cues WHERE id=? AND track_id IN (SELECT id FROM subtitle_tracks WHERE project_id=?)", (cue_id, project_id))
            if cur.rowcount == 0: raise KeyError("Subtitle cue does not belong to this project.")

    def set_default(self, project_id: str, track_id: str) -> None:
        with self.database.connect() as c, c:
            owner = c.execute("SELECT 1 FROM subtitle_tracks WHERE id=? AND project_id=?", (track_id, project_id)).fetchone()
            if owner is None: raise KeyError("Subtitle track does not belong to this project.")
            c.execute("UPDATE subtitle_tracks SET is_default=0 WHERE project_id=?", (project_id,))
            c.execute("UPDATE subtitle_tracks SET is_default=1 WHERE id=?", (track_id,))

    def delete_track(self, project_id: str, track_id: str) -> None:
        with self.database.connect() as c, c:
            row = c.execute("SELECT style_id FROM subtitle_tracks WHERE id=? AND project_id=?", (track_id, project_id)).fetchone()
            if row is None: raise KeyError("Subtitle track does not belong to this project.")
            style_id = str(row["style_id"] or "")
            c.execute("DELETE FROM subtitle_tracks WHERE id=?", (track_id,))
            if style_id: c.execute("DELETE FROM subtitle_styles WHERE id=? AND project_id=?", (style_id, project_id))

    def user_presets(self) -> list[dict[str, object]]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM subtitle_user_presets ORDER BY name COLLATE NOCASE").fetchall()
        result=[]
        for row in rows:
            try: style=json.loads(row["style_json"] or "{}")
            except json.JSONDecodeError: style={}
            result.append({"id":str(row["id"]),"name":str(row["name"]),"style":style,"builtin":False,"created_at":str(row["created_at"]),"updated_at":str(row["updated_at"])})
        return result

    def save_user_preset(self, preset_id: str, name: str, style: dict[str, object]) -> None:
        now=utc_now_iso()
        with self.database.connect() as c, c:
            c.execute("INSERT INTO subtitle_user_presets(id,name,style_json,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,style_json=excluded.style_json,updated_at=excluded.updated_at",
                      (preset_id,name,json.dumps(style,ensure_ascii=False,separators=(",",":")),now,now))

    def delete_user_preset(self, preset_id: str) -> None:
        with self.database.connect() as c, c:
            c.execute("DELETE FROM subtitle_user_presets WHERE id=?", (preset_id,))

    @staticmethod
    def _insert_track(c, t: SubtitleTrack) -> None:
        c.execute("""INSERT INTO subtitle_tracks(id,project_id,name,language,track_type,source_type,source_id,source_language,status,style_id,is_default,is_bilingual,secondary_language,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (t.track_id,t.project_id,t.name,t.language,t.track_type_code,t.source_type,t.source_id,t.source_language,t.status_code,t.style_id,int(t.is_default),int(t.is_bilingual),t.secondary_language,json.dumps(t.metadata,ensure_ascii=False,separators=(",",":")),t.created_at,t.updated_at))

    @staticmethod
    def _insert_style(c, s: SubtitleStyle) -> None:
        c.execute("""INSERT INTO subtitle_styles(id,project_id,name,font_family,font_size,font_weight,italic,text_color,secondary_text_color,outline_color,outline_width,shadow_enabled,shadow_offset,background_enabled,background_color,background_opacity,alignment,vertical_position,horizontal_margin,vertical_margin,max_lines,max_chars_per_line,line_spacing,highlight_color,highlight_text_color,secondary_scale,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (s.style_id,s.project_id,s.name,s.font_family,s.font_size,s.font_weight,int(s.italic),s.text_color,s.secondary_text_color,s.outline_color,s.outline_width,int(s.shadow_enabled),s.shadow_offset,int(s.background_enabled),s.background_color,s.background_opacity,s.alignment,s.vertical_position,s.horizontal_margin,s.vertical_margin,s.max_lines,s.max_chars_per_line,s.line_spacing,s.highlight_color,s.highlight_text_color,s.secondary_scale,json.dumps(s.metadata,ensure_ascii=False,separators=(",",":")),s.created_at,s.updated_at))

    @staticmethod
    def _insert_cue(c, q: SubtitleCue) -> None:
        c.execute("""INSERT INTO subtitle_cues(id,track_id,cue_order,start_ms,end_ms,text,secondary_text,position,alignment,style_override_json,edited,locked,source_segment_id,source_hash,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (q.cue_id,q.track_id,q.order,q.start_ms,q.end_ms,q.text,q.secondary_text,q.position,q.alignment,json.dumps(q.style_override,ensure_ascii=False,separators=(",",":")),int(q.edited),int(q.locked),q.source_segment_id,q.source_hash,json.dumps(q.metadata,ensure_ascii=False,separators=(",",":")),q.created_at,q.updated_at))

    @staticmethod
    def _insert_word(c, w: SubtitleWord) -> None:
        c.execute("""INSERT INTO subtitle_words(id,cue_id,word_order,text,start_ms,end_ms,probability,highlight_group,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)""",
                  (w.word_id,w.cue_id,w.order,w.text,w.start_ms,w.end_ms,w.probability,w.highlight_group,json.dumps(w.metadata,ensure_ascii=False,separators=(",",":"))))

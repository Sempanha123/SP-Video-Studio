from __future__ import annotations

import json
from copy import deepcopy
from uuid import uuid4

from domain.project import utc_now_iso
from domain.speaker_profile import SpeakerProfile
from domain.speech_block import SpeechBlock, speech_text_hash
from domain.manual_audio_clip import ManualAudioClip
from storage.database import SQLiteDatabase


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Phase22Repository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    # Speakers -----------------------------------------------------------------
    def speakers(self, project_id: str) -> list[SpeakerProfile]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM speakers WHERE project_id=? ORDER BY created_at,id", (project_id,)).fetchall()
        return [SpeakerProfile.from_record(row) for row in rows]

    def speaker(self, project_id: str, speaker_id: str) -> SpeakerProfile | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM speakers WHERE id=? AND project_id=?", (speaker_id, project_id)).fetchone()
        return SpeakerProfile.from_record(row) if row else None

    def save_speaker(self, item: SpeakerProfile) -> SpeakerProfile:
        item.validate(); item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute(
                """INSERT INTO speakers(id,project_id,name,role,voice_id,language,description,avatar,metadata_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,role=excluded.role,voice_id=excluded.voice_id,
                   language=excluded.language,description=excluded.description,avatar=excluded.avatar,
                   metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (item.id,item.project_id,item.name,item.role_code,item.voice_id,item.language,item.description,item.avatar,
                 _json(item.metadata),item.created_at,item.updated_at),
            )
        return item

    def speaker_usage_count(self, project_id: str, speaker_id: str) -> int:
        with self.database.connect() as c:
            row = c.execute(
                """SELECT COUNT(*) AS n FROM speech_blocks b
                   JOIN script_sections s ON s.id=b.script_section_id
                   JOIN scripts sc ON sc.id=s.script_id
                   WHERE sc.project_id=? AND b.speaker_id=?""", (project_id, speaker_id)
            ).fetchone()
        return int(row["n"] if row else 0)

    def delete_speaker(self, project_id: str, speaker_id: str) -> None:
        with self.database.connect() as c, c:
            cur = c.execute("DELETE FROM speakers WHERE id=? AND project_id=?", (speaker_id, project_id))
            if cur.rowcount == 0: raise KeyError("Speaker not found.")

    # Speech blocks ------------------------------------------------------------
    def blocks_for_section(self, section_id: str) -> list[SpeechBlock]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM speech_blocks WHERE script_section_id=? ORDER BY block_order,id", (section_id,)).fetchall()
        return [SpeechBlock.from_record(row) for row in rows]

    def blocks_for_project(self, project_id: str) -> list[SpeechBlock]:
        with self.database.connect() as c:
            rows = c.execute(
                """SELECT b.* FROM speech_blocks b
                   JOIN script_sections s ON s.id=b.script_section_id
                   JOIN scripts sc ON sc.id=s.script_id
                   WHERE sc.project_id=? ORDER BY s.section_order,b.block_order,b.id""", (project_id,)
            ).fetchall()
        result=[SpeechBlock.from_record(row) for row in rows]
        for item in result:
            if not item.project_id: item.project_id=project_id
        return result

    def block(self, project_id: str, block_id: str) -> SpeechBlock | None:
        with self.database.connect() as c:
            row = c.execute(
                """SELECT b.* FROM speech_blocks b
                   JOIN script_sections s ON s.id=b.script_section_id
                   JOIN scripts sc ON sc.id=s.script_id
                   WHERE b.id=? AND sc.project_id=?""", (block_id, project_id)
            ).fetchone()
        item=SpeechBlock.from_record(row) if row else None
        if item and not item.project_id: item.project_id=project_id
        return item

    def save_block(self, project_id: str, item: SpeechBlock) -> SpeechBlock:
        item.project_id=project_id
        item.text_hash=item.text_hash or speech_text_hash(item.text)
        item.validate(); item.updated_at = utc_now_iso()
        # Keep legacy Phase 22 pointers mirrored for Phase 30 and old views.
        if item.active_generated_audio_id: item.audio_id=item.active_generated_audio_id
        elif item.audio_id: item.active_generated_audio_id=item.audio_id
        if item.timeline_start_ms is not None and not item.scene_id: item.start_offset_ms=int(item.timeline_start_ms)
        with self.database.connect() as c, c:
            owner = c.execute(
                """SELECT 1 FROM script_sections s JOIN scripts sc ON sc.id=s.script_id
                   WHERE s.id=? AND sc.project_id=?""", (item.script_section_id, project_id)
            ).fetchone()
            if owner is None: raise KeyError("Script section not found in this project.")
            c.execute(
                """INSERT INTO speech_blocks(
                   id,project_id,script_section_id,block_order,speaker_id,text,language,voice_override_id,
                   speech_source_type,pause_before_ms,pause_after_ms,scene_id,start_offset_ms,audio_id,
                   timeline_start_ms,timeline_end_ms,active_generated_audio_id,text_hash,audio_status,timing_status,
                   user_modified,metadata_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id,block_order=excluded.block_order,
                   speaker_id=excluded.speaker_id,text=excluded.text,language=excluded.language,
                   voice_override_id=excluded.voice_override_id,speech_source_type=excluded.speech_source_type,
                   pause_before_ms=excluded.pause_before_ms,pause_after_ms=excluded.pause_after_ms,
                   scene_id=excluded.scene_id,start_offset_ms=excluded.start_offset_ms,audio_id=excluded.audio_id,
                   timeline_start_ms=excluded.timeline_start_ms,timeline_end_ms=excluded.timeline_end_ms,
                   active_generated_audio_id=excluded.active_generated_audio_id,text_hash=excluded.text_hash,
                   audio_status=excluded.audio_status,timing_status=excluded.timing_status,
                   user_modified=excluded.user_modified,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (item.id,item.project_id,item.script_section_id,item.order,item.speaker_id or None,item.text,item.language,
                 item.voice_override_id,item.source_type_code,item.pause_before_ms,item.pause_after_ms,item.scene_id or None,
                 item.start_offset_ms,item.audio_id,item.timeline_start_ms,item.timeline_end_ms,item.active_generated_audio_id,
                 item.text_hash,item.audio_status_code,item.timing_status_code,int(item.user_modified),_json(item.metadata),
                 item.created_at,item.updated_at),
            )
        return item

    def save_blocks(self, project_id: str, items: list[SpeechBlock]) -> list[SpeechBlock]:
        # Transactional bulk path used by find/replace, split/merge and bulk assignment.
        for item in items: item.project_id=project_id; item.validate()
        with self.database.connect() as c, c:
            for item in items:
                item.updated_at=utc_now_iso(); item.text_hash=item.text_hash or speech_text_hash(item.text)
                if item.active_generated_audio_id: item.audio_id=item.active_generated_audio_id
                if item.timeline_start_ms is not None and not item.scene_id: item.start_offset_ms=int(item.timeline_start_ms)
                c.execute(
                    """UPDATE speech_blocks SET block_order=?,speaker_id=?,text=?,language=?,voice_override_id=?,
                       speech_source_type=?,pause_before_ms=?,pause_after_ms=?,scene_id=?,start_offset_ms=?,audio_id=?,
                       timeline_start_ms=?,timeline_end_ms=?,active_generated_audio_id=?,text_hash=?,audio_status=?,
                       timing_status=?,user_modified=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?""",
                    (item.order,item.speaker_id or None,item.text,item.language,item.voice_override_id,item.source_type_code,
                     item.pause_before_ms,item.pause_after_ms,item.scene_id or None,item.start_offset_ms,item.audio_id,
                     item.timeline_start_ms,item.timeline_end_ms,item.active_generated_audio_id,item.text_hash,
                     item.audio_status_code,item.timing_status_code,int(item.user_modified),_json(item.metadata),
                     item.updated_at,item.id,project_id),
                )
        return [self.block(project_id,item.id) for item in items if self.block(project_id,item.id) is not None]

    def delete_block(self, project_id: str, block_id: str) -> None:
        with self.database.connect() as c, c:
            cur = c.execute(
                """DELETE FROM speech_blocks WHERE id=? AND script_section_id IN (
                   SELECT s.id FROM script_sections s JOIN scripts sc ON sc.id=s.script_id WHERE sc.project_id=?)""",
                (block_id, project_id),
            )
            if cur.rowcount == 0: raise KeyError("Speech block not found.")

    def normalize_block_order(self, project_id: str, section_id: str) -> list[SpeechBlock]:
        items = self.blocks_for_section(section_id)
        with self.database.connect() as c, c:
            for order, item in enumerate(items):
                c.execute("UPDATE speech_blocks SET block_order=?,updated_at=? WHERE id=?", (order,utc_now_iso(),item.id))
        return self.blocks_for_section(section_id)

    def ensure_legacy_block(self, project_id: str, section_id: str, *, default_language: str = "en") -> list[SpeechBlock]:
        existing = self.blocks_for_section(section_id)
        if existing:
            for item in existing:
                if not item.project_id: item.project_id=project_id
            return existing
        with self.database.connect() as c:
            row = c.execute(
                """SELECT s.content,s.id,sc.language FROM script_sections s JOIN scripts sc ON sc.id=s.script_id
                   WHERE s.id=? AND sc.project_id=?""", (section_id, project_id)
            ).fetchone()
        if row is None: raise KeyError("Script section not found.")
        text = str(row["content"] or ""); language = str(row["language"] or default_language)
        item = SpeechBlock(project_id=project_id,script_section_id=section_id,order=0,text=text,language=language,
                           speech_source_type=("tts" if text.strip() else "none"))
        self.save_block(project_id,item); return [item]

    # Manual audio clips -------------------------------------------------------
    def audio_clips(self, project_id: str, scene_id: str | None = None) -> list[ManualAudioClip]:
        sql="SELECT * FROM manual_audio_clips WHERE project_id=?"; args:list[object]=[project_id]
        if scene_id is not None: sql+=" AND scene_id=?"; args.append(scene_id)
        sql+=" ORDER BY start_ms,id"
        with self.database.connect() as c: rows=c.execute(sql,tuple(args)).fetchall()
        return [ManualAudioClip.from_record(row) for row in rows]

    def save_audio_clip(self, item: ManualAudioClip) -> ManualAudioClip:
        item.validate(); item.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            owner=c.execute("SELECT type FROM media_assets WHERE id=? AND project_id=?",(item.media_id,item.project_id)).fetchone()
            if owner is None or str(owner["type"])!="audio": raise KeyError("Choose project audio for this clip.")
            c.execute("""INSERT INTO manual_audio_clips(id,project_id,scene_id,media_id,start_ms,duration_ms,source_in_ms,volume,muted,fade_in_ms,fade_out_ms,metadata_json,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET scene_id=excluded.scene_id,media_id=excluded.media_id,start_ms=excluded.start_ms,duration_ms=excluded.duration_ms,source_in_ms=excluded.source_in_ms,volume=excluded.volume,muted=excluded.muted,fade_in_ms=excluded.fade_in_ms,fade_out_ms=excluded.fade_out_ms,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                      (item.id,item.project_id,item.scene_id or None,item.media_id,item.start_ms,item.duration_ms,item.source_in_ms,item.volume,int(item.muted),item.fade_in_ms,item.fade_out_ms,_json(item.metadata),item.created_at,item.updated_at))
        return item

    def delete_audio_clip(self, project_id: str, clip_id: str) -> None:
        with self.database.connect() as c,c:
            cur=c.execute("DELETE FROM manual_audio_clips WHERE id=? AND project_id=?",(clip_id,project_id))
            if cur.rowcount==0: raise KeyError("Audio clip not found.")

    # UI state -----------------------------------------------------------------
    def save_state(self, project_id: str, **updates: object) -> dict[str, object]:
        current = self.state(project_id); current.update({k:v for k,v in updates.items() if k in {"previewQuality","activeSceneId","activeLayerId","activeSpeakerId","metadata"}})
        now=utc_now_iso()
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO phase22_project_state(project_id,preview_quality,active_scene_id,active_layer_id,active_speaker_id,metadata_json,updated_at)
                       VALUES(?,?,?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET preview_quality=excluded.preview_quality,active_scene_id=excluded.active_scene_id,active_layer_id=excluded.active_layer_id,active_speaker_id=excluded.active_speaker_id,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                      (project_id,str(current.get("previewQuality","auto")),str(current.get("activeSceneId","")),str(current.get("activeLayerId","")),str(current.get("activeSpeakerId","")),_json(current.get("metadata",{})),now))
        return current

    def state(self, project_id: str) -> dict[str, object]:
        with self.database.connect() as c: row=c.execute("SELECT * FROM phase22_project_state WHERE project_id=?",(project_id,)).fetchone()
        if row is None:return {"previewQuality":"auto","activeSceneId":"","activeLayerId":"","activeSpeakerId":"","metadata":{}}
        try:meta=json.loads(str(row["metadata_json"] or "{}"))
        except Exception:meta={}
        return {"previewQuality":str(row["preview_quality"]),"activeSceneId":str(row["active_scene_id"]),"activeLayerId":str(row["active_layer_id"]),"activeSpeakerId":str(row["active_speaker_id"]),"metadata":meta if isinstance(meta,dict) else {}}

    # Duplication ---------------------------------------------------------------
    def duplicate_project(self, source_project_id: str, target_project_id: str, *, media_map: dict[str,str] | None=None, scene_map: dict[str,str] | None=None) -> dict[str, dict[str, str]]:
        maps={"speaker":{},"block":{},"audioClip":{}}; target_sections=self._section_map(source_project_id,target_project_id);media_map=media_map or {};scene_map=scene_map or {}
        for speaker in self.speakers(source_project_id):
            old=speaker.id;clone=deepcopy(speaker);clone.speaker_id=str(uuid4());clone.project_id=target_project_id;clone.created_at=clone.updated_at=utc_now_iso();self.save_speaker(clone);maps["speaker"][old]=clone.id
        for block in self.blocks_for_project(source_project_id):
            target_section=target_sections.get(block.script_section_id)
            if not target_section:continue
            old=block.id;clone=deepcopy(block);clone.block_id=str(uuid4());clone.project_id=target_project_id;clone.script_section_id=target_section
            clone.speaker_id=maps["speaker"].get(block.speaker_id,"") if block.speaker_id else "";clone.scene_id=scene_map.get(block.scene_id,"") if block.scene_id else ""
            # Takes are project-owned output. Never point a duplicate back to the source project.
            clone.audio_id="";clone.active_generated_audio_id="";clone.audio_status="not_generated";clone.timing_status="not_generated"
            clone.created_at=clone.updated_at=utc_now_iso();self.save_block(target_project_id,clone);maps["block"][old]=clone.id
        for clip in self.audio_clips(source_project_id):
            mapped_media=media_map.get(clip.media_id,"")
            if not mapped_media:continue
            old=clip.id;clone=deepcopy(clip);clone.clip_id=str(uuid4());clone.project_id=target_project_id;clone.media_id=mapped_media;clone.scene_id=scene_map.get(clip.scene_id,"") if clip.scene_id else "";clone.created_at=clone.updated_at=utc_now_iso();self.save_audio_clip(clone);maps["audioClip"][old]=clone.id
        state=self.state(source_project_id);self.save_state(target_project_id,previewQuality=state.get("previewQuality","auto"),metadata=deepcopy(state.get("metadata",{})))
        return maps

    def _section_map(self, source_project_id: str, target_project_id: str) -> dict[str, str]:
        with self.database.connect() as c:
            source=c.execute("""SELECT s.id,s.section_order FROM script_sections s JOIN scripts sc ON sc.id=s.script_id WHERE sc.project_id=? ORDER BY s.section_order""",(source_project_id,)).fetchall()
            target=c.execute("""SELECT s.id,s.section_order FROM script_sections s JOIN scripts sc ON sc.id=s.script_id WHERE sc.project_id=? ORDER BY s.section_order""",(target_project_id,)).fetchall()
        by_order={int(row["section_order"]):str(row["id"]) for row in target};return {str(row["id"]):by_order.get(int(row["section_order"]),"") for row in source}

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from domain.dub_audio import DubAudioOutput
from domain.dub_mix_settings import DubMixSettings
from domain.dub_segment import DubSegment
from domain.dubbing_project import DubbingProject
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase


def _j(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


class DubbingRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def get_project(self, project_id: str) -> DubbingProject | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM dubbing_projects WHERE project_id=?", (project_id,)).fetchone()
        return DubbingProject.from_record(row) if row else None

    def save_project(self, item: DubbingProject) -> DubbingProject:
        item.validate(); item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute('''INSERT INTO dubbing_projects(project_id,source_media_id,source_language,target_language,transcript_id,translation_id,target_voice_id,subtitle_track_id,status,settings_json,metadata_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET source_media_id=excluded.source_media_id,source_language=excluded.source_language,target_language=excluded.target_language,transcript_id=excluded.transcript_id,translation_id=excluded.translation_id,target_voice_id=excluded.target_voice_id,subtitle_track_id=excluded.subtitle_track_id,status=excluded.status,settings_json=excluded.settings_json,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
            (item.project_id,item.source_media_id or None,item.source_language,item.target_language,item.transcript_id or None,item.translation_id or None,item.target_voice_id,item.subtitle_track_id or None,item.status_code,_j(item.settings),_j(item.metadata),item.created_at,item.updated_at))
        return item

    def segments(self, project_id: str) -> list[DubSegment]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM dub_segments WHERE project_id=? ORDER BY segment_order,created_at", (project_id,)).fetchall()
        return [DubSegment.from_record(row) for row in rows]

    def segment(self, project_id: str, segment_id: str) -> DubSegment | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM dub_segments WHERE project_id=? AND id=?", (project_id, segment_id)).fetchone()
        return DubSegment.from_record(row) if row else None

    def segment_for_translation(self, project_id: str, translation_segment_id: str) -> DubSegment | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM dub_segments WHERE project_id=? AND translation_segment_id=?", (project_id, translation_segment_id)).fetchone()
        return DubSegment.from_record(row) if row else None

    def save_segment(self, item: DubSegment) -> DubSegment:
        item.validate(); item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute('''INSERT INTO dub_segments(id,project_id,source_transcript_segment_id,translation_segment_id,segment_order,source_start_ms,source_end_ms,target_text,voice_id,generated_audio_id,generated_audio_path,generated_duration_ms,timing_mode,timing_status,audio_status,start_offset_ms,stretch_factor,locked,user_modified,speaker_label,source_hash,generation_hash,metadata_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_transcript_segment_id=excluded.source_transcript_segment_id,translation_segment_id=excluded.translation_segment_id,segment_order=excluded.segment_order,source_start_ms=excluded.source_start_ms,source_end_ms=excluded.source_end_ms,target_text=excluded.target_text,voice_id=excluded.voice_id,generated_audio_id=excluded.generated_audio_id,generated_audio_path=excluded.generated_audio_path,generated_duration_ms=excluded.generated_duration_ms,timing_mode=excluded.timing_mode,timing_status=excluded.timing_status,audio_status=excluded.audio_status,start_offset_ms=excluded.start_offset_ms,stretch_factor=excluded.stretch_factor,locked=excluded.locked,user_modified=excluded.user_modified,speaker_label=excluded.speaker_label,source_hash=excluded.source_hash,generation_hash=excluded.generation_hash,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
            (item.id,item.project_id,item.source_transcript_segment_id or None,item.translation_segment_id or None,item.order,item.source_start_ms,item.source_end_ms,item.target_text,item.voice_id,item.generated_audio_id or None,item.generated_audio_path,item.generated_duration_ms,item.timing_mode_code,item.timing_status_code,item.audio_status_code,item.start_offset_ms,item.stretch_factor,int(item.locked),int(item.user_modified),item.speaker_label,item.source_hash,item.generation_hash,_j(item.metadata),item.created_at,item.updated_at))
        return item

    def delete_segment_audio(self, project_id: str, segment_id: str) -> str:
        segment = self.segment(project_id, segment_id)
        if segment is None: raise KeyError("Dub segment not found.")
        old_path = segment.generated_audio_path
        segment.generated_audio_id=""; segment.generated_audio_path=""; segment.generated_duration_ms=0
        segment.generation_hash=""; segment.audio_status="pending"; segment.timing_status="not_generated"; segment.stretch_factor=1.0
        self.save_segment(segment)
        return old_path

    def get_mix_settings(self, project_id: str) -> DubMixSettings:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM dub_mix_settings WHERE project_id=?", (project_id,)).fetchone()
        return DubMixSettings.from_record(row) if row else DubMixSettings(project_id=project_id)

    def save_mix_settings(self, item: DubMixSettings) -> DubMixSettings:
        item.validate(); item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute('''INSERT INTO dub_mix_settings(project_id,mode,original_volume,dub_volume,duck_normal_volume,duck_under_volume,duck_fade_ms,metadata_json,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET mode=excluded.mode,original_volume=excluded.original_volume,dub_volume=excluded.dub_volume,duck_normal_volume=excluded.duck_normal_volume,duck_under_volume=excluded.duck_under_volume,duck_fade_ms=excluded.duck_fade_ms,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
            (item.project_id,item.mode_code,item.original_volume,item.dub_volume,item.duck_normal_volume,item.duck_under_volume,item.duck_fade_ms,_j(item.metadata),item.updated_at))
        return item

    def outputs(self, project_id: str, output_type: str | None = None) -> list[DubAudioOutput]:
        query="SELECT * FROM dub_audio_outputs WHERE project_id=?"; args:list[object]=[project_id]
        if output_type: query+=" AND output_type=?"; args.append(output_type)
        query+=" ORDER BY created_at DESC"
        with self.database.connect() as c: rows=c.execute(query,tuple(args)).fetchall()
        return [DubAudioOutput.from_record(row) for row in rows]

    def latest_output(self, project_id: str, output_type: str="final_mix") -> DubAudioOutput | None:
        values=self.outputs(project_id,output_type); return values[0] if values else None

    def save_output(self, item: DubAudioOutput) -> DubAudioOutput:
        with self.database.connect() as c,c:
            c.execute('''INSERT INTO dub_audio_outputs(id,project_id,source_media_id,target_language,voice_profile_id,file_path,duration_ms,fingerprint,output_type,status,settings_json,metadata_json,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET file_path=excluded.file_path,duration_ms=excluded.duration_ms,fingerprint=excluded.fingerprint,status=excluded.status,settings_json=excluded.settings_json,metadata_json=excluded.metadata_json''',
            (item.id,item.project_id,item.source_media_id or None,item.target_language,item.voice_profile_id,item.file_path,item.duration_ms,item.fingerprint,item.output_type,item.status_code,_j(item.settings),_j(item.metadata),item.created_at))
        return item

    def mark_outputs_outdated(self, project_id: str) -> None:
        with self.database.connect() as c,c:
            c.execute("UPDATE dub_audio_outputs SET status='outdated' WHERE project_id=? AND status='ready'", (project_id,))

    def reset_audio(self, project_id: str) -> list[str]:
        paths=[s.generated_audio_path for s in self.segments(project_id) if s.generated_audio_path]
        paths += [o.file_path for o in self.outputs(project_id) if o.file_path]
        with self.database.connect() as c,c:
            c.execute("DELETE FROM dub_audio_outputs WHERE project_id=?",(project_id,))
            c.execute("UPDATE dub_segments SET generated_audio_id=NULL,generated_audio_path='',generated_duration_ms=0,generation_hash='',audio_status='pending',timing_status='not_generated',timing_mode='natural',start_offset_ms=0,stretch_factor=1.0,updated_at=? WHERE project_id=?",(utc_now_iso(),project_id))
        return paths

    def duplicate_project(
        self, source_project_id: str, target_project_id: str, target_audio_root: str | Path | None = None, *,
        media_map: dict[str,str] | None = None, transcript_map: dict[str,str] | None = None,
        translation_map: dict[str,str] | None = None, subtitle_map: dict[str,str] | None = None,
        transcript_segment_map: dict[str,str] | None = None, translation_segment_map: dict[str,str] | None = None,
    ) -> dict[str,str]:
        source=self.get_project(source_project_id)
        if source is None: return {}
        media_map=media_map or {}; transcript_map=transcript_map or {}; translation_map=translation_map or {}; subtitle_map=subtitle_map or {}
        transcript_segment_map=transcript_segment_map or {}; translation_segment_map=translation_segment_map or {}
        clone=deepcopy(source); clone.project_id=target_project_id
        clone.source_media_id=media_map.get(source.source_media_id,source.source_media_id)
        clone.transcript_id=transcript_map.get(source.transcript_id,source.transcript_id)
        clone.translation_id=translation_map.get(source.translation_id,source.translation_id)
        clone.subtitle_track_id=subtitle_map.get(source.subtitle_track_id,source.subtitle_track_id)
        clone.created_at=clone.updated_at=utc_now_iso(); self.save_project(clone)
        mapping:dict[str,str]={}; root=Path(target_audio_root) if target_audio_root else None
        for item in self.segments(source_project_id):
            old=item.id; old_audio_id=item.generated_audio_id; old_audio_path=item.generated_audio_path
            item.segment_id=str(uuid4()); item.project_id=target_project_id; item.created_at=item.updated_at=utc_now_iso()
            item.source_transcript_segment_id=transcript_segment_map.get(item.source_transcript_segment_id,item.source_transcript_segment_id)
            item.translation_segment_id=translation_segment_map.get(item.translation_segment_id,item.translation_segment_id)
            if old_audio_path and root and Path(old_audio_path).is_file():
                source_path=Path(old_audio_path); root.mkdir(parents=True,exist_ok=True)
                target=root/f"{item.id}{source_path.suffix or '.wav'}"; target.write_bytes(source_path.read_bytes())
                item.generated_audio_path=str(target); item.generated_audio_id=""
                item.metadata["duplicatedFromGeneratedAudioId"]=old_audio_id
            elif old_audio_path:
                item.generated_audio_id=""; item.generated_audio_path=""; item.generated_duration_ms=0; item.generation_hash=""
                item.audio_status="pending"; item.timing_status="not_generated"; item.stretch_factor=1.0
            self.save_segment(item); mapping[old]=item.id
        mix=deepcopy(self.get_mix_settings(source_project_id)); mix.project_id=target_project_id; self.save_mix_settings(mix)
        return mapping

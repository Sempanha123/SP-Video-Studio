from __future__ import annotations

import json
from copy import deepcopy
from uuid import uuid4

from domain.project import utc_now_iso
from domain.short_candidate import ShortCandidate
from domain.short_project import ShortProject
from domain.short_segment import ShortSegment
from storage.database import SQLiteDatabase


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class ShortRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def get_project(self, project_id: str) -> ShortProject | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM shorts_projects WHERE project_id=?", (project_id,)).fetchone()
        return ShortProject.from_record(row) if row else None

    def save_project(self, item: ShortProject) -> ShortProject:
        item.validate(); item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            owner = c.execute("SELECT 1 FROM projects WHERE id=?", (item.project_id,)).fetchone()
            if owner is None:
                raise KeyError("Shorts metadata project does not exist.")
            c.execute(
                """INSERT INTO shorts_projects(
                    project_id,source_type,source_id,target_duration_ms,target_aspect_ratio,language,platform,style,status,
                    source_project_id,source_entity_ids_json,source_fingerprint,metadata_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(project_id) DO UPDATE SET
                    source_type=excluded.source_type,source_id=excluded.source_id,target_duration_ms=excluded.target_duration_ms,
                    target_aspect_ratio=excluded.target_aspect_ratio,language=excluded.language,platform=excluded.platform,
                    style=excluded.style,status=excluded.status,source_project_id=excluded.source_project_id,
                    source_entity_ids_json=excluded.source_entity_ids_json,source_fingerprint=excluded.source_fingerprint,
                    metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (item.project_id,item.source_type_code,item.source_id,item.target_duration_ms,item.target_aspect_ratio,
                 item.language,item.platform,item.style,item.status_code,item.source_project_id,_json(item.source_entity_ids),
                 item.source_fingerprint,_json(item.metadata),item.created_at,item.updated_at),
            )
        return item

    def list_candidates(self, project_id: str) -> list[ShortCandidate]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM short_candidates WHERE project_id=? ORDER BY created_at DESC,id", (project_id,)).fetchall()
        return [ShortCandidate.from_record(row) for row in rows]

    def get_candidate(self, candidate_id: str) -> ShortCandidate | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM short_candidates WHERE id=?", (candidate_id,)).fetchone()
        return ShortCandidate.from_record(row) if row else None

    def save_candidate(self, item: ShortCandidate, segments: list[ShortSegment] | None = None) -> ShortCandidate:
        item.validate(); item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            owner = c.execute("SELECT 1 FROM projects WHERE id=?", (item.project_id,)).fetchone()
            if owner is None:
                raise KeyError("Short candidate project does not exist.")
            c.execute(
                """INSERT INTO short_candidates(
                    id,project_id,source_type,source_id,title,hook,start_ms,end_ms,language,status,source_project_id,
                    source_entity_ids_json,source_fingerprint,score_metadata_json,metadata_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET source_type=excluded.source_type,source_id=excluded.source_id,title=excluded.title,
                    hook=excluded.hook,start_ms=excluded.start_ms,end_ms=excluded.end_ms,language=excluded.language,status=excluded.status,
                    source_project_id=excluded.source_project_id,source_entity_ids_json=excluded.source_entity_ids_json,
                    source_fingerprint=excluded.source_fingerprint,score_metadata_json=excluded.score_metadata_json,
                    metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (item.id,item.project_id,item.source_type_code,item.source_id,item.title,item.hook,item.start_ms,item.end_ms,
                 item.language,item.status_code,item.source_project_id,_json(item.source_entity_ids),item.source_fingerprint,
                 _json(item.score_metadata),_json(item.metadata),item.created_at,item.updated_at),
            )
            if segments is not None:
                c.execute("DELETE FROM short_segments WHERE candidate_id=?", (item.id,))
                for order, segment in enumerate(segments):
                    segment.candidate_id = item.id; segment.order = order; segment.validate()
                    c.execute(
                        "INSERT INTO short_segments(id,candidate_id,segment_order,source_start_ms,source_end_ms,source_entity_id,metadata_json) VALUES(?,?,?,?,?,?,?)",
                        (segment.id,item.id,segment.order,segment.source_start_ms,segment.source_end_ms,segment.source_entity_id,_json(segment.metadata)),
                    )
        return item

    def segments(self, candidate_id: str) -> list[ShortSegment]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM short_segments WHERE candidate_id=? ORDER BY segment_order,id", (candidate_id,)).fetchall()
        return [ShortSegment.from_record(row) for row in rows]

    def delete_candidate(self, project_id: str, candidate_id: str) -> None:
        with self.database.connect() as c, c:
            cur = c.execute("DELETE FROM short_candidates WHERE id=? AND project_id=?", (candidate_id,project_id))
            if cur.rowcount == 0:
                raise KeyError("Short candidate not found.")

    def duplicate_candidate(self, project_id: str, candidate_id: str, *, target_project_id: str | None = None) -> ShortCandidate:
        source = self.get_candidate(candidate_id)
        if source is None or source.project_id != project_id:
            raise KeyError("Short candidate not found.")
        clone = deepcopy(source); clone.candidate_id = str(uuid4()); clone.project_id = target_project_id or project_id
        clone.title = f"{source.title} Copy"; clone.status = "draft"; clone.created_at = clone.updated_at = utc_now_iso()
        segments=[]
        for segment in self.segments(candidate_id):
            item=deepcopy(segment); item.segment_id=str(uuid4()); item.candidate_id=clone.id; segments.append(item)
        self.save_candidate(clone,segments); return clone

    def duplicate_project(self, source_project_id: str, target_project_id: str) -> dict[str, str]:
        result: dict[str,str] = {}
        source_meta = self.get_project(source_project_id)
        if source_meta is not None:
            clone = deepcopy(source_meta); clone.project_id=target_project_id; clone.created_at=clone.updated_at=utc_now_iso()
            # The duplicate is independent. Retain provenance but never point writable entities back to source project.
            clone.source_project_id = source_meta.source_project_id or source_project_id
            self.save_project(clone)
        for candidate in reversed(self.list_candidates(source_project_id)):
            clone=deepcopy(candidate); clone.candidate_id=str(uuid4()); clone.project_id=target_project_id
            clone.created_at=clone.updated_at=utc_now_iso()
            segments=[]
            for segment in self.segments(candidate.id):
                item=deepcopy(segment); item.segment_id=str(uuid4()); item.candidate_id=clone.id; segments.append(item)
            self.save_candidate(clone,segments); result[candidate.id]=clone.id
        return result
    def remap_duplicate_sources(
        self,
        source_project_id: str,
        target_project_id: str,
        candidate_map: dict[str,str],
        *,
        media_map: dict[str,str] | None=None,
        transcript_map: dict[str,str] | None=None,
        transcript_segment_map: dict[str,str] | None=None,
        scene_map: dict[str,str] | None=None,
    ) -> None:
        media_map=media_map or {}; transcript_map=transcript_map or {}; transcript_segment_map=transcript_segment_map or {}; scene_map=scene_map or {}

        def remap_id(value: str) -> str:
            return media_map.get(value, transcript_map.get(value, transcript_segment_map.get(value, scene_map.get(value, value))))

        source_meta=self.get_project(source_project_id); target_meta=self.get_project(target_project_id)
        if source_meta is not None and target_meta is not None:
            if source_meta.source_type_code in {"video","manual","dub"}: target_meta.source_id=media_map.get(source_meta.source_id,target_meta.source_id)
            elif source_meta.source_type_code=="transcript": target_meta.source_id=transcript_map.get(source_meta.source_id,target_meta.source_id)
            elif source_meta.source_type_code in {"scenes","news","story"}: target_meta.source_id=target_project_id
            target_meta.source_entity_ids=[remap_id(x) for x in source_meta.source_entity_ids]
            self.save_project(target_meta)

        for source_id,target_id in candidate_map.items():
            source=self.get_candidate(source_id); target=self.get_candidate(target_id)
            if source is None or target is None: continue
            if source.source_type_code in {"video","manual","dub"}: target.source_id=media_map.get(source.source_id,target.source_id)
            elif source.source_type_code=="transcript": target.source_id=transcript_map.get(source.source_id,target.source_id)
            elif source.source_type_code in {"scenes","news","story"}: target.source_id=target_project_id
            target.source_entity_ids=[remap_id(x) for x in source.source_entity_ids]
            segments=self.segments(target.id)
            for segment in segments:
                segment.source_entity_id=remap_id(segment.source_entity_id)
                for key,mapping in (("mediaId",media_map),("sceneId",scene_map),("transcriptId",transcript_map)):
                    value=str(segment.metadata.get(key,"") or "")
                    if value: segment.metadata[key]=mapping.get(value,value)
                values=segment.metadata.get("transcriptSegmentIds")
                if isinstance(values,list): segment.metadata["transcriptSegmentIds"]=[transcript_segment_map.get(str(x),str(x)) for x in values]
            for key,mapping in (("mediaId",media_map),("sceneId",scene_map),("transcriptId",transcript_map)):
                value=str(target.metadata.get(key,"") or "")
                if value: target.metadata[key]=mapping.get(value,value)
            ids=target.metadata.get("sourceSceneIds")
            if isinstance(ids,list): target.metadata["sourceSceneIds"]=[scene_map.get(str(x),str(x)) for x in ids]
            self.save_candidate(target,segments)


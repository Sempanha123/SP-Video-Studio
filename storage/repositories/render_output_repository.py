from __future__ import annotations

import json

from domain.render_output import RenderOutput
from storage.database import SQLiteDatabase


class RenderOutputRepository:
    def __init__(self, database: SQLiteDatabase) -> None: self.database=database

    def create(self, item: RenderOutput) -> RenderOutput:
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO render_outputs(id,project_id,render_job_id,file_path,width,height,fps,duration_ms,video_codec,audio_codec,file_size,thumbnail_path,created_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(item.id,item.project_id,item.render_job_id,item.file_path,item.width,item.height,item.fps,item.duration_ms,item.video_codec,item.audio_codec,item.file_size,item.thumbnail_path,item.created_at,json.dumps(item.metadata,ensure_ascii=False,separators=(",",":"))))
        return item

    def get(self, output_id: str) -> RenderOutput|None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM render_outputs WHERE id=?",(output_id,)).fetchone()
        return RenderOutput.from_record(row) if row else None

    def for_job(self, job_id: str) -> RenderOutput|None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM render_outputs WHERE render_job_id=?",(job_id,)).fetchone()
        return RenderOutput.from_record(row) if row else None

    def list_for_project(self, project_id: str, limit: int=50) -> list[RenderOutput]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM render_outputs WHERE project_id=? ORDER BY created_at DESC LIMIT ?",(project_id,max(1,min(int(limit),200)))).fetchall()
        return [RenderOutput.from_record(r) for r in rows]


    def update(self, item: RenderOutput) -> RenderOutput:
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE render_outputs SET file_path=?,width=?,height=?,fps=?,duration_ms=?,video_codec=?,audio_codec=?,file_size=?,thumbnail_path=?,metadata_json=? WHERE id=? AND project_id=?""",(item.file_path,item.width,item.height,item.fps,item.duration_ms,item.video_codec,item.audio_codec,item.file_size,item.thumbnail_path,json.dumps(item.metadata,ensure_ascii=False,separators=(",",":")),item.id,item.project_id))
            if cur.rowcount==0: raise KeyError("Render output does not belong to this project.")
        return item

    def list_recent(self, limit: int=20) -> list[RenderOutput]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM render_outputs ORDER BY created_at DESC LIMIT ?",(max(1,min(int(limit),100)),)).fetchall()
        return [RenderOutput.from_record(r) for r in rows]

    def delete_record(self, project_id: str, output_id: str) -> RenderOutput:
        item=self.get(output_id)
        if item is None or item.project_id!=project_id: raise KeyError("Render output does not belong to this project.")
        with self.database.connect() as c,c: c.execute("DELETE FROM render_outputs WHERE id=? AND project_id=?",(output_id,project_id))
        return item

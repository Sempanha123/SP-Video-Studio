from __future__ import annotations

import json

from domain.render_job import RenderJob
from storage.database import SQLiteDatabase


class RenderJobRepository:
    def __init__(self, database: SQLiteDatabase) -> None: self.database=database

    def create(self, job: RenderJob) -> RenderJob:
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO render_jobs(id,project_id,preset_id,status,output_path,started_at,completed_at,progress,expected_duration_ms,actual_duration_ms,settings_json,error_message,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",self._values(job))
        return job

    def update(self, job: RenderJob) -> RenderJob:
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE render_jobs SET preset_id=?,status=?,output_path=?,started_at=?,completed_at=?,progress=?,expected_duration_ms=?,actual_duration_ms=?,settings_json=?,error_message=?,metadata_json=? WHERE id=? AND project_id=?""",(job.preset,job.status_code,job.output_path,job.started_at,job.completed_at,float(job.progress),job.expected_duration_ms,job.actual_duration_ms,json.dumps(job.settings,ensure_ascii=False,separators=(",",":")),job.error_message,json.dumps(job.metadata,ensure_ascii=False,separators=(",",":")),job.id,job.project_id))
            if cur.rowcount==0: raise KeyError("Render job does not belong to this project.")
        return job

    def get(self, job_id: str) -> RenderJob|None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM render_jobs WHERE id=?",(job_id,)).fetchone()
        return RenderJob.from_record(row) if row else None

    def list_for_project(self, project_id: str, limit: int=50) -> list[RenderJob]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM render_jobs WHERE project_id=? ORDER BY created_at DESC LIMIT ?",(project_id,max(1,min(int(limit),200)))).fetchall()
        return [RenderJob.from_record(r) for r in rows]

    def delete(self, project_id: str, job_id: str) -> None:
        with self.database.connect() as c,c:
            cur=c.execute("DELETE FROM render_jobs WHERE id=? AND project_id=?",(job_id,project_id))
            if cur.rowcount==0: raise KeyError("Render job does not belong to this project.")

    @staticmethod
    def _values(job:RenderJob):
        return (job.id,job.project_id,job.preset,job.status_code,job.output_path,job.started_at,job.completed_at,float(job.progress),job.expected_duration_ms,job.actual_duration_ms,json.dumps(job.settings,ensure_ascii=False,separators=(",",":")),job.error_message,json.dumps(job.metadata,ensure_ascii=False,separators=(",",":")),job.created_at)

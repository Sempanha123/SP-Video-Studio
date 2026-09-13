from __future__ import annotations
import json
from domain.autosave_state import ProjectAutosaveState
from domain.recovery_snapshot import RecoverySnapshot
from domain.recovery_session import RecoverySession


def _json(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def _decode(value,default):
    try:
        v=json.loads(value or "")
        return v if isinstance(v,type(default)) else default
    except Exception:return default

class RecoveryRepository:
    def __init__(self,database): self.database=database
    def get_autosave(self,project_id:str)->ProjectAutosaveState|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM autosave_state WHERE project_id=?",(project_id,)).fetchone()
        if not r:return None
        return ProjectAutosaveState(project_id=str(r['project_id']),project_revision=int(r['project_revision']),saved_revision=int(r['saved_revision']),status=str(r['status']),last_modified_at=float(r['last_modified_at']),last_saved_at=float(r['last_saved_at']),scheduled_at=(float(r['scheduled_at']) if r['scheduled_at'] is not None else None),saving_revision=int(r['saving_revision']),dirty_topics=set(_decode(r['dirty_topics_json'],[])),failure_message=str(r['failure_message'] or ''))
    def save_autosave(self,s:ProjectAutosaveState)->None:
        with self.database.connect() as c,c:c.execute("""INSERT INTO autosave_state(project_id,project_revision,saved_revision,status,last_modified_at,last_saved_at,scheduled_at,saving_revision,dirty_topics_json,failure_message) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET project_revision=excluded.project_revision,saved_revision=excluded.saved_revision,status=excluded.status,last_modified_at=excluded.last_modified_at,last_saved_at=excluded.last_saved_at,scheduled_at=excluded.scheduled_at,saving_revision=excluded.saving_revision,dirty_topics_json=excluded.dirty_topics_json,failure_message=excluded.failure_message""",(s.project_id,s.project_revision,s.saved_revision,s.status_code,s.last_modified_at,s.last_saved_at,s.scheduled_at,s.saving_revision,_json(sorted(s.dirty_topics)),s.failure_message))
    def list_dirty(self)->list[ProjectAutosaveState]:
        with self.database.connect() as c:ids=[str(r[0]) for r in c.execute("SELECT project_id FROM autosave_state WHERE project_revision>saved_revision OR status IN ('dirty','scheduled','saving','failed')").fetchall()]
        return [x for x in (self.get_autosave(i) for i in ids) if x]
    def save_session(self,s:RecoverySession)->None:
        with self.database.connect() as c,c:c.execute("""INSERT INTO recovery_sessions(id,started_at,closed_at,clean_shutdown,app_version,metadata_json) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET closed_at=excluded.closed_at,clean_shutdown=excluded.clean_shutdown,metadata_json=excluded.metadata_json""",(s.session_id,s.started_at,s.closed_at,int(s.clean_shutdown),s.app_version,_json(s.metadata)))
    def save_snapshot(self,s:RecoverySnapshot)->None:
        with self.database.connect() as c,c:
            cols={str(x[1]) for x in c.execute('PRAGMA table_info(recovery_snapshots)')}
            if 'schema_version' in cols:
                c.execute("""INSERT INTO recovery_snapshots(id,project_id,session_id,project_revision,created_at,reason,snapshot_type,status,path,size,checksum,metadata_json,schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,path=excluded.path,size=excluded.size,checksum=excluded.checksum,metadata_json=excluded.metadata_json,schema_version=excluded.schema_version""",(s.id,s.project_id,s.session_id,s.project_revision,s.created_at,s.reason,s.type_code,s.status_code,s.path,s.size,s.checksum,_json(s.metadata),int(s.schema_version)))
            else:
                c.execute("""INSERT INTO recovery_snapshots(id,project_id,session_id,project_revision,created_at,reason,snapshot_type,status,path,size,checksum,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,path=excluded.path,size=excluded.size,checksum=excluded.checksum,metadata_json=excluded.metadata_json""",(s.id,s.project_id,s.session_id,s.project_revision,s.created_at,s.reason,s.type_code,s.status_code,s.path,s.size,s.checksum,_json(s.metadata)))
    def snapshot(self,snapshot_id:str)->RecoverySnapshot|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM recovery_snapshots WHERE id=?",(snapshot_id,)).fetchone()
        return self._snapshot(r) if r else None
    def snapshots(self,project_id:str|None=None)->list[RecoverySnapshot]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM recovery_snapshots"+(" WHERE project_id=?" if project_id else "")+" ORDER BY created_at DESC",((project_id,) if project_id else ())).fetchall()
        return [self._snapshot(r) for r in rows]
    def delete_snapshot(self,snapshot_id:str)->None:
        with self.database.connect() as c,c:c.execute("DELETE FROM recovery_snapshots WHERE id=?",(snapshot_id,))
    def delete_project_snapshots(self,project_id:str)->None:
        with self.database.connect() as c,c:c.execute("DELETE FROM recovery_snapshots WHERE project_id=?",(project_id,))
    def upsert_interrupted(self,job_key,project_id,job_type,source_id,state,retry_mode,detected_at,metadata):
        with self.database.connect() as c,c:c.execute("""INSERT INTO interrupted_jobs(job_key,project_id,job_type,source_id,state,retry_mode,detected_at,metadata_json) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(job_key) DO UPDATE SET state=excluded.state,retry_mode=excluded.retry_mode,detected_at=excluded.detected_at,metadata_json=excluded.metadata_json""",(job_key,project_id,job_type,source_id,state,retry_mode,detected_at,_json(metadata)))
    def interrupted(self):
        with self.database.connect() as c:rows=c.execute("SELECT * FROM interrupted_jobs ORDER BY detected_at DESC").fetchall()
        return [{k:r[k] for k in r.keys()}|{"metadata":_decode(r['metadata_json'],{})} for r in rows]
    @staticmethod
    def _snapshot(r):
        keys=set(r.keys());schema=int(r['schema_version']) if 'schema_version' in keys else int(_decode(r['metadata_json'],{}).get('projectSchemaVersion',1) or 1)
        return RecoverySnapshot(snapshot_id=str(r['id']),project_id=str(r['project_id']),session_id=str(r['session_id']),project_revision=int(r['project_revision']),created_at=str(r['created_at']),reason=str(r['reason']),snapshot_type=str(r['snapshot_type']),status=str(r['status']),path=str(r['path']),size=int(r['size']),checksum=str(r['checksum']),metadata=_decode(r['metadata_json'],{}),schema_version=schema)

from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path


def utc_iso():return datetime.now(timezone.utc).isoformat()

def _merge_json(value,updates):
    try:data=json.loads(value or '{}');data=data if isinstance(data,dict) else {}
    except Exception:data={}
    data.update(updates);return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))

class InterruptedJobRecoveryService:
    """Marks heavy work interrupted after an unclean shutdown; never auto-resumes it."""
    def __init__(self,database,recovery_repository,*,batch_recovery=None,logger=None):self.database=database;self.repository=recovery_repository;self.batch_recovery=batch_recovery;self.logger=logger
    def recover_interrupted_jobs(self)->dict[str,int]:
        counts={'batch':0,'render':0,'stt':0,'translation':0,'dub':0}
        if self.batch_recovery:
            try:
                r=self.batch_recovery.recover_startup();counts['batch']=int(r.get('interruptedItems',0))
            except Exception:
                if self.logger:self.logger.exception('Batch recovery scan failed')
        with self.database.connect() as c,c:
            tables={str(r[0]) for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if 'render_jobs' in tables:
                rows=c.execute("SELECT id,project_id,status,output_path,metadata_json FROM render_jobs WHERE status IN ('queued','preparing','rendering','validating')").fetchall()
                for r in rows:
                    meta=_merge_json(r['metadata_json'],{'interrupted':True,'retryAvailable':True,'partialOutput':bool(r['output_path'] and Path(str(r['output_path'])).exists())})
                    c.execute("UPDATE render_jobs SET status='interrupted',error_message=?,metadata_json=? WHERE id=?",('Render was interrupted before completion.',meta,r['id']))
                    self._record(c,f"render:{r['id']}",str(r['project_id']),'render',str(r['id']),'restart',{'outputPath':str(r['output_path'] or '')});counts['render']+=1
            if 'transcripts' in tables:
                rows=c.execute("SELECT id,project_id,status,metadata_json FROM transcripts WHERE status IN ('queued','preparing','transcribing','processing')").fetchall()
                for r in rows:
                    c.execute("UPDATE transcripts SET status='failed',metadata_json=? WHERE id=?",(_merge_json(r['metadata_json'],{'interrupted':True,'retryAvailable':True,'retryMode':'restart'}),r['id']))
                    self._record(c,f"stt:{r['id']}",str(r['project_id']),'stt',str(r['id']),'restart',{});counts['stt']+=1
            if 'translations' in tables:
                rows=c.execute("SELECT id,project_id,status,metadata_json FROM translations WHERE status='translating'").fetchall()
                for r in rows:
                    c.execute("UPDATE translations SET status='failed',metadata_json=? WHERE id=?",(_merge_json(r['metadata_json'],{'interrupted':True,'retryAvailable':True,'resumeCompletedSegments':True}),r['id']))
                    self._record(c,f"translation:{r['id']}",str(r['project_id']),'translation',str(r['id']),'resume_segments',{});counts['translation']+=1
            if 'dub_segments' in tables:
                rows=c.execute("SELECT id,project_id,audio_status,metadata_json FROM dub_segments WHERE audio_status IN ('generating','processing')").fetchall()
                for r in rows:
                    c.execute("UPDATE dub_segments SET audio_status='interrupted',metadata_json=? WHERE id=?",(_merge_json(r['metadata_json'],{'interrupted':True,'retryAvailable':True}),r['id']))
                    self._record(c,f"dub:{r['id']}",str(r['project_id']),'dub',str(r['id']),'resume_segments',{});counts['dub']+=1
        return counts
    def _record(self,c,key,project_id,job_type,source_id,retry_mode,metadata):
        c.execute("""INSERT INTO interrupted_jobs(job_key,project_id,job_type,source_id,state,retry_mode,detected_at,metadata_json) VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(job_key) DO UPDATE SET state=excluded.state,retry_mode=excluded.retry_mode,detected_at=excluded.detected_at,metadata_json=excluded.metadata_json""",(key,project_id,job_type,source_id,'interrupted',retry_mode,utc_iso(),json.dumps(metadata,ensure_ascii=False,sort_keys=True,separators=(',',':'))))
    def list_interrupted(self):return self.repository.interrupted()

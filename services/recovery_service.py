from __future__ import annotations
from datetime import datetime,timezone
from domain.recovery_session import RecoverySession
from domain.recovery_snapshot import RecoverySnapshotType
from domain.recovery_errors import RecoveryRestoreFailed,RecoverySnapshotCorrupt,RecoveryVersionUnsupported


def utc_iso():return datetime.now(timezone.utc).isoformat()

class RecoveryService:
    def __init__(self,repository,store,snapshots,codec,autosave,integrity=None,job_recovery=None,*,app_version='0',logger=None):
        self.repository=repository;self.store=store;self.snapshots=snapshots;self.codec=codec;self.autosave=autosave;self.integrity=integrity;self.job_recovery=job_recovery;self.app_version=str(app_version);self.logger=logger;self.session=None;self.previous_unclean=False;self.previous_marker=None
    def start_session(self)->RecoverySession:
        marker=self.store.read_session_marker();self.previous_marker=marker
        self.previous_unclean=bool(marker and not marker.get('cleanShutdown',False))
        if marker:
            try:self.store.archive_session(marker)
            except Exception:pass
        self.session=RecoverySession(started_at=utc_iso(),app_version=self.app_version,metadata={'previousUnclean':self.previous_unclean})
        self.repository.save_session(self.session);self.store.write_session_marker(self.session.to_dict())
        if self.previous_unclean and self.integrity:self.integrity.lightweight_check()
        if self.previous_unclean and self.job_recovery:self.job_recovery.recover_interrupted_jobs()
        return self.session
    def mark_clean_shutdown(self)->None:
        if self.session is None:return
        self.session.clean_shutdown=True;self.session.closed_at=utc_iso();self.repository.save_session(self.session);self.store.archive_session(self.session.to_dict());self.store.clear_session_marker()
    def recoverable(self):
        out=[]
        for snap in self.repository.snapshots():
            try:
                state=self.autosave.state(snap.project_id)
                if snap.project_revision>state.saved_revision:
                    out.append(self.summary(snap.id))
            except Exception:continue
        return out
    def summary(self,snapshot_id:str):
        snap,payload=self.snapshots.load(snapshot_id);warnings=self.codec.media_warnings(payload)
        return {**snap.to_dict(),'comparison':self.codec.compare(snap.project_id,payload),'mediaWarnings':warnings,'missingMedia':sum(1 for x in warnings if x.get('status')=='missing')}
    def recover(self,snapshot_id:str)->dict:
        snap,payload=self.snapshots.load(snapshot_id)
        backup=self.snapshots.create(snap.project_id,self.session.session_id if self.session else 'restore',snapshot_type=RecoverySnapshotType.PRE_RESTORE_BACKUP.value,reason='Backup before recovery',force=True)
        try:
            counts=self.codec.restore(snap.project_id,payload)
            state=self.autosave.state(snap.project_id);state.project_revision=max(state.project_revision,snap.project_revision);state.saved_revision=state.project_revision;state.dirty_topics.clear();state.complete_save(state.saved_revision);self.repository.save_autosave(state)
            return {'projectId':snap.project_id,'restored':True,'tables':counts,'mediaWarnings':self.codec.media_warnings(payload),'backupSnapshotId':backup.id if backup else ''}
        except Exception as exc:
            if backup:
                try:
                    _,old=self.snapshots.load(backup.id);self.codec.restore(snap.project_id,old)
                except Exception:pass
            raise RecoveryRestoreFailed('Recovery could not be applied. Your saved project was kept.') from exc
    def discard(self,snapshot_id:str):self.snapshots.discard(snapshot_id)
    def open_saved(self,snapshot_id:str):
        snap=self.repository.snapshot(snapshot_id);return snap.project_id if snap else ''

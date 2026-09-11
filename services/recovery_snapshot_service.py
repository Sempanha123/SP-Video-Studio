from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from domain.recovery_snapshot import RecoverySnapshot,RecoverySnapshotType,RecoverySnapshotStatus
from domain.recovery_errors import RecoveryDiskFull,RecoverySnapshotCorrupt,RecoveryVersionUnsupported


def utc_iso():return datetime.now(timezone.utc).isoformat()

class RecoverySnapshotService:
    PERIODIC_SECONDS=180
    def __init__(self,repository,store,codec,autosave,*,app_version='0',logger=None):
        self.repository=repository;self.store=store;self.codec=codec;self.autosave=autosave;self.app_version=str(app_version);self.logger=logger;self._last_periodic={};self._low_disk_warned=False
    def create(self,project_id:str,session_id:str,*,snapshot_type='periodic',reason='',force=False)->RecoverySnapshot|None:
        state=self.autosave.state(project_id)
        if not force and not state.dirty:return None
        payload=self.codec.capture(project_id)
        metadata={'appVersion':self.app_version,'projectSchemaVersion':int(payload.get('schemaVersion',0)),'savedRevision':state.saved_revision,'dirty':state.dirty}
        from uuid import uuid4
        sid=str(uuid4());manifest={'createdAt':utc_iso(),'reason':reason or snapshot_type,'snapshotType':snapshot_type,'projectRevision':state.project_revision,'appVersion':self.app_version,'projectSchemaVersion':metadata['projectSchemaVersion']}
        try:path,size,checksum=self.store.create_snapshot(sid,project_id,manifest,payload)
        except RecoveryDiskFull:
            self._low_disk_warned=True;raise
        snap=RecoverySnapshot(snapshot_id=sid,project_id=project_id,session_id=session_id,project_revision=state.project_revision,created_at=manifest['createdAt'],reason=manifest['reason'],snapshot_type=snapshot_type,path=str(path),size=size,checksum=checksum,metadata=metadata)
        self.repository.save_snapshot(snap);self.store.prune(project_id,keep_ids={sid});self._sync_pruned_metadata(project_id)
        if snapshot_type==RecoverySnapshotType.PERIODIC.value:self._last_periodic[project_id]=datetime.now(timezone.utc).timestamp()
        return snap
    def periodic_if_due(self,project_id:str,session_id:str,*,now:float)->RecoverySnapshot|None:
        state=self.autosave.state(project_id)
        if not state.dirty:return None
        last=float(self._last_periodic.get(project_id,0))
        if now-last<self.PERIODIC_SECONDS:return None
        try:return self.create(project_id,session_id,snapshot_type='periodic',reason='Periodic recovery protection')
        except RecoveryDiskFull:return None
    def load(self,snapshot_id:str):
        snap=self.repository.snapshot(snapshot_id)
        if snap is None:raise KeyError('Recovery snapshot not found.')
        try:env=self.store.load_snapshot(snap.path)
        except RecoverySnapshotCorrupt:
            snap.status=RecoverySnapshotStatus.CORRUPT;self.repository.save_snapshot(snap);raise
        if env.get('unsupported'):
            snap.status=RecoverySnapshotStatus.UNSUPPORTED;self.repository.save_snapshot(snap);raise RecoveryVersionUnsupported('This recovery copy was created by a newer app version.')
        return snap,env['payload']
    def discard(self,snapshot_id:str)->None:
        snap=self.repository.snapshot(snapshot_id)
        if snap:
            self.store.discard(snap.path);self.repository.delete_snapshot(snapshot_id)
    def delete_project(self,project_id:str)->None:
        self.store.delete_project(project_id);self.repository.delete_project_snapshots(project_id)
    def list(self,project_id:str|None=None):return self.repository.snapshots(project_id)
    def _sync_pruned_metadata(self,project_id):
        existing={str(p) for p in self.store.list_project(project_id)}
        for snap in self.repository.snapshots(project_id):
            if snap.path not in existing:self.repository.delete_snapshot(snap.id)

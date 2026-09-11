from __future__ import annotations
import hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from domain.recovery_errors import RecoveryDiskFull, RecoverySnapshotCorrupt, RecoverySnapshotFailed
from storage.atomic_write import atomic_write_json


def utc_iso()->str: return datetime.now(timezone.utc).isoformat()
def canonical(value:Any)->bytes: return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

class RecoveryStore:
    SCHEMA_VERSION=1
    MIN_FREE_BYTES=128*1024*1024
    def __init__(self,root:Path,*,retention:int=8,min_free_bytes:int|None=None):
        self.root=Path(root); self.sessions=self.root/"sessions"; self.projects=self.root/"projects"; self.retention=max(2,int(retention)); self.min_free_bytes=self.MIN_FREE_BYTES if min_free_bytes is None else int(min_free_bytes)
        self.sessions.mkdir(parents=True,exist_ok=True); self.projects.mkdir(parents=True,exist_ok=True)
    @property
    def marker_path(self)->Path:return self.sessions/"current.json"
    def write_session_marker(self,data:dict[str,Any])->Path:return atomic_write_json(self.marker_path,data)
    def read_session_marker(self)->dict[str,Any]|None:
        try:return json.loads(self.marker_path.read_text(encoding="utf-8")) if self.marker_path.is_file() else None
        except (OSError,json.JSONDecodeError):return None
    def archive_session(self,data:dict[str,Any])->Path:
        sid=str(data.get("sessionId") or "unknown"); path=self.sessions/f"{sid}.json"; atomic_write_json(path,data); return path
    def clear_session_marker(self)->None:
        try:self.marker_path.unlink(missing_ok=True)
        except OSError:pass
    def has_space(self,estimated_bytes:int=1)->bool:
        try:return shutil.disk_usage(self.root).free >= self.min_free_bytes+max(0,int(estimated_bytes))
        except OSError:return True
    def create_snapshot(self,snapshot_id:str,project_id:str,manifest:dict[str,Any],payload:dict[str,Any])->tuple[Path,int,str]:
        if not self.has_space(len(canonical(payload))): raise RecoveryDiskFull("Recovery snapshots are paused because disk space is low.")
        manifest=dict(manifest); manifest["schemaVersion"]=self.SCHEMA_VERSION; manifest["projectId"]=project_id; manifest["snapshotId"]=snapshot_id
        checksum=hashlib.sha256(canonical({"manifest":manifest,"payload":payload})).hexdigest()
        envelope={"manifest":manifest,"payload":payload,"checksum":checksum}
        folder=self.projects/project_id; folder.mkdir(parents=True,exist_ok=True)
        path=folder/f"{snapshot_id}.spvrecovery"
        try:atomic_write_json(path,envelope)
        except OSError as exc: raise RecoverySnapshotFailed("Could not create recovery snapshot.") from exc
        return path,path.stat().st_size,checksum
    def load_snapshot(self,path:str|Path)->dict[str,Any]:
        source=Path(path)
        try: envelope=json.loads(source.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise RecoverySnapshotCorrupt("This recovery copy is damaged and cannot be restored.") from exc
        manifest=envelope.get("manifest");payload=envelope.get("payload");expected=str(envelope.get("checksum") or "")
        if not isinstance(manifest,dict) or not isinstance(payload,dict): raise RecoverySnapshotCorrupt("This recovery copy is damaged and cannot be restored.")
        if int(manifest.get("schemaVersion",0))>self.SCHEMA_VERSION: return {**envelope,"unsupported":True}
        actual=hashlib.sha256(canonical({"manifest":manifest,"payload":payload})).hexdigest()
        if not expected or actual!=expected: raise RecoverySnapshotCorrupt("This recovery copy is damaged and cannot be restored.")
        envelope["unsupported"]=False; return envelope
    def list_project(self,project_id:str)->list[Path]:
        folder=self.projects/project_id
        return sorted(folder.glob("*.spvrecovery"),key=lambda p:p.stat().st_mtime if p.exists() else 0,reverse=True) if folder.is_dir() else []
    def prune(self,project_id:str,*,keep_ids:set[str]|None=None)->list[Path]:
        keep_ids=keep_ids or set(); paths=self.list_project(project_id); removed=[]; kept=sum(1 for p in paths if p.stem in keep_ids)
        for path in paths:
            if path.stem in keep_ids: continue
            if kept<self.retention: kept+=1; continue
            try:path.unlink();removed.append(path)
            except OSError:pass
        return removed
    def discard(self,path:str|Path)->None: Path(path).unlink(missing_ok=True)
    def delete_project(self,project_id:str)->None:
        folder=(self.projects/project_id)
        if folder.is_dir(): shutil.rmtree(folder,ignore_errors=False)

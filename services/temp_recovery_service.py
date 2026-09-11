from __future__ import annotations
import json,shutil,time
from pathlib import Path

class TempRecoveryService:
    def __init__(self,temp_root:Path,*,logger=None):self.root=Path(temp_root);self.logger=logger
    def classify(self,path:str|Path,*,now:float|None=None,age_seconds:int=86400)->str:
        p=Path(path);now=time.time() if now is None else float(now)
        if not p.exists():return 'safe-to-delete'
        manifest=p/'recovery-manifest.json'
        if manifest.is_file():
            try:data=json.loads(manifest.read_text(encoding='utf-8'))
            except Exception:return 'unknown'
            stage=str(data.get('stage') or '')
            if stage in {'running','rendering','tts','stt','translation'}:return 'recoverable'
            if bool(data.get('safe_cleanup')) and now-p.stat().st_mtime>=age_seconds:return 'safe-to-delete'
            return 'stale'
        return 'safe-to-delete' if now-p.stat().st_mtime>=age_seconds else 'unknown'
    def cleanup(self,path:str|Path)->bool:
        p=Path(path).resolve();root=self.root.resolve()
        if p==root or root not in p.parents:raise ValueError('Temporary cleanup path escaped application temp storage.')
        if self.classify(p)!='safe-to-delete':return False
        shutil.rmtree(p,ignore_errors=False);return True

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,TimeoutError

class ShutdownService:
    """One bounded clean-exit coordinator. Heavy work is stopped/paused by registered hooks."""
    def __init__(self,autosave,recovery,snapshots,*,timeout_seconds:float=5.0,logger=None):
        self.autosave=autosave;self.recovery=recovery;self.snapshots=snapshots;self.timeout_seconds=float(timeout_seconds);self.logger=logger;self._heavy_hooks=[]
    def register_heavy_job_hook(self,hook):self._heavy_hooks.append(hook)
    def prepare_exit(self)->bool:
        session=self.recovery.session
        dirty=list(self.autosave.dirty_projects())
        for pid in dirty:
            try:self.snapshots.create(pid,session.session_id if session else 'shutdown',snapshot_type='pre_close',reason='Recovery point before application close')
            except Exception:
                if self.logger:self.logger.exception('Could not create pre-close recovery snapshot for %s',pid)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.autosave.flush_all,reason='shutdown')
            try:ok=bool(future.result(timeout=self.timeout_seconds))
            except TimeoutError:ok=False
            except Exception:ok=False
        if not ok:return False
        for hook in tuple(self._heavy_hooks):
            try:hook()
            except Exception:
                if self.logger:self.logger.exception('Heavy-job shutdown hook failed')
        self.recovery.mark_clean_shutdown();return True

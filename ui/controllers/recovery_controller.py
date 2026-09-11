from __future__ import annotations

try:
    from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
except ImportError:  # test/headless fallback
    class QObject:
        def __init__(self,*a,**k): pass
    class Signal:
        def __init__(self,*a,**k): pass
        def emit(self,*a,**k): pass
    def Slot(*a,**k):
        def deco(fn): return fn
        return deco
    def Property(*a,**k):
        def deco(fn): return property(fn)
        return deco
    class QTimer:
        def __init__(self,*a,**k): self.timeout=self
        def setInterval(self,*a): pass
        def start(self): pass
        def stop(self): pass
        def connect(self,*a): pass


class RecoveryController(QObject):
    stateChanged=Signal()
    recoveryChanged=Signal()
    operationSucceeded=Signal(str)
    operationFailed=Signal(str)

    def __init__(self,autosave,recovery,snapshots,shutdown,logger=None,parent=None):
        super().__init__(parent);self.autosave=autosave;self.recovery=recovery;self.snapshots=snapshots;self.shutdown=shutdown;self.logger=logger
        self._current_project='';self._recoveries=[];self._timer=QTimer(self);self._timer.setInterval(300);self._timer.timeout.connect(self._tick);self._timer.start()
        self.autosave.on_change(lambda _s:self.stateChanged.emit())
        try:
            from PySide6.QtCore import QCoreApplication
            app=QCoreApplication.instance()
            if app is not None: app.aboutToQuit.connect(self._clean_exit)
        except Exception:
            pass
        self.refreshRecoveries()
    @Property(str,notify=stateChanged)
    def currentProjectId(self):return self._current_project
    @Property(str,notify=stateChanged)
    def saveState(self):return self.autosave.display_state(self._current_project) if self._current_project else 'Saved'
    @Property(bool,notify=recoveryChanged)
    def hasRecoverableWork(self):return bool(self._recoveries)
    @Property('QVariantList',notify=recoveryChanged)
    def recoveries(self):return list(self._recoveries)
    @Property('QVariantList',notify=stateChanged)
    def interruptedJobs(self):
        svc=getattr(self.recovery,'job_recovery',None);return svc.list_interrupted() if svc else []
    @Slot(str)
    def setCurrentProject(self,project_id):self._current_project=str(project_id or '');self.stateChanged.emit()
    @Slot(result=bool)
    def manualSave(self):
        if not self._current_project:return True
        ok=self.autosave.critical_flush(self._current_project,reason='manual_ctrl_s')
        if ok:self.operationSucceeded.emit('This project was saved successfully.')
        else:self.operationFailed.emit('Your latest changes could not be saved.')
        self.stateChanged.emit();return ok
    @Slot(str,result=bool)
    def criticalFlush(self,reason):
        if not self._current_project:return True
        ok=self.autosave.critical_flush(self._current_project,reason=str(reason or 'critical'));self.stateChanged.emit();return ok
    @Slot()
    def refreshRecoveries(self):
        try:self._recoveries=self.recovery.recoverable()
        except Exception:self._recoveries=[]
        self.recoveryChanged.emit()
    @Slot(str,result='QVariantMap')
    def review(self,snapshot_id):
        try:return self.recovery.summary(snapshot_id)
        except Exception as exc:self.operationFailed.emit(str(exc));return {}
    @Slot(str,result=bool)
    def recoverSnapshot(self,snapshot_id):
        try:
            self.recovery.recover(snapshot_id);self.refreshRecoveries();self.operationSucceeded.emit('Your work was recovered.');return True
        except Exception as exc:self.operationFailed.emit(str(exc));return False
    @Slot(str,result=bool)
    def discardSnapshot(self,snapshot_id):
        try:self.recovery.discard(snapshot_id);self.refreshRecoveries();return True
        except Exception as exc:self.operationFailed.emit(str(exc));return False
    @Slot(str,result=str)
    def openSavedVersion(self,snapshot_id):return self.recovery.open_saved(snapshot_id)
    @Slot(result=bool)
    def prepareExit(self):return bool(self.shutdown.prepare_exit())
    @Slot()
    def _clean_exit(self):
        if not self.shutdown.prepare_exit():
            # Leave the session marker unclean so the next launch offers recovery.
            return
    @Slot()
    def _tick(self):
        try:
            now=self.autosave.clock();self.autosave.tick(now)
            session=self.recovery.session
            if session:
                for pid in self.autosave.dirty_projects():self.snapshots.periodic_if_due(pid,session.session_id,now=now)
        except Exception:
            if self.logger:self.logger.exception('Autosave/recovery timer failed')
        self.stateChanged.emit()

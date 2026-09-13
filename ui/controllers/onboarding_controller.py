from __future__ import annotations

import logging
from pathlib import Path

try:
    from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
except ImportError:  # focused tests can exercise the service without Qt installed
    class QObject:
        def __init__(self, *args, **kwargs): pass
    class Signal:
        def __init__(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass
    def Slot(*args, **kwargs): return lambda fn: fn
    def Property(*args, **kwargs): return lambda fn: property(fn)
    class QUrl:
        def __init__(self, value=""): self.value = value
        def toLocalFile(self): return str(self.value).removeprefix("file:///").removeprefix("file://")


class OnboardingController(QObject):
    changed = Signal()
    readinessChanged = Signal()
    modelsChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    openModelsRequested = Signal()
    openTemplatesRequested = Signal()
    openSettingsRequested = Signal(str)
    firstProjectRequested = Signal(str, str, str, str, int)
    closeRequested = Signal()
    _readinessReady = Signal(object, object)
    _modelsReady = Signal(object, object)

    def __init__(self, service, *, worker_pool=None, logger=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.workers = worker_pool
        self.logger = logger or logging.getLogger("sp_video_studio.onboarding")
        self._readiness = {}
        self._models = []
        self._checking = False
        self._discovering_models = False
        try:
            self._readinessReady.connect(self._apply_readiness)
            self._modelsReady.connect(self._apply_models)
        except Exception:
            pass

    @Property(bool, notify=changed)
    def shouldShow(self): return bool(self.service.should_show)

    @Property(str, notify=changed)
    def status(self): return self.service.state.status

    @Property(int, notify=changed)
    def onboardingVersion(self): return int(self.service.state.onboarding_version)

    @Property(int, notify=changed)
    def currentStep(self): return int(self.service.state.current_step)

    @Property(str, notify=changed)
    def stepId(self): return self.service.state.step_id

    @Property(str, notify=changed)
    def defaultContentLanguage(self): return self.service.state.default_project_language

    @Property(str, notify=changed)
    def projectFolder(self): return self.service.settings.current.default_projects_folder

    @Property(str, notify=changed)
    def theme(self): return self.service.settings.current.theme

    @Property(str, notify=changed)
    def performanceProfile(self): return self.service.settings.current.performance_profile

    @Property(str, notify=changed)
    def reduceMotionMode(self): return self.service.settings.current.reduce_motion

    @Property(str, notify=changed)
    def interfaceTextSize(self): return self.service.settings.current.interface_text_size

    @Property("QVariantList", notify=changed)
    def languages(self):
        try: return self.service.languages_for_setup()
        except Exception as exc:
            self._fail(exc); return []

    @Property("QVariantMap", notify=readinessChanged)
    def readiness(self): return dict(self._readiness)

    @Property(bool, notify=readinessChanged)
    def checkingReadiness(self): return self._checking

    @Property("QVariantList", notify=modelsChanged)
    def models(self): return list(self._models)

    @Property(bool, notify=modelsChanged)
    def discoveringModels(self): return self._discovering_models

    @Property("QVariantMap", notify=changed)
    def completionSummary(self):
        try: return self.service.summary()
        except Exception: return {}

    @Slot()
    def begin(self):
        self.service.begin(); self.changed.emit()

    @Slot()
    def runAgain(self):
        self.service.reopen(); self.changed.emit()

    @Slot()
    def skip(self):
        self.service.skip(); self.changed.emit(); self.closeRequested.emit()

    @Slot()
    def next(self):
        self.service.next_step(); self.changed.emit()

    @Slot()
    def back(self):
        self.service.previous_step(); self.changed.emit()

    @Slot(int)
    def goToStep(self, index):
        self.service.set_step(index); self.changed.emit()

    @Slot(str)
    def setContentLanguage(self, code):
        try:self.service.set_content_language(code); self.changed.emit()
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def setTheme(self, value):
        try:self.service.set_theme(value); self.changed.emit()
        except Exception as exc:self._fail(exc)

    @Slot(bool)
    def setReduceMotion(self, value):
        try:self.service.set_reduce_motion(value); self.changed.emit()
        except Exception as exc:self._fail(exc)

    @Slot(bool)
    def setLargeText(self, value):
        try:self.service.set_large_text(value); self.changed.emit()
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def setPerformanceProfile(self, value):
        try:self.service.set_performance_profile(value); self.changed.emit()
        except Exception as exc:self._fail(exc)

    @Slot(str, result="QVariantMap")
    def validateProjectFolder(self, value):
        return self.service.validate_project_folder(self._local_path(value))

    @Slot(str, result=bool)
    def setProjectFolder(self, value):
        result = self.service.set_project_folder(self._local_path(value))
        if result.get("valid"):
            self.changed.emit(); self.operationSucceeded.emit("New projects will use this folder."); return True
        self.operationFailed.emit(str(result.get("message") or "This folder cannot be used for projects.")); return False

    @Slot()
    def refreshReadiness(self):
        if self._checking:return
        self._checking=True; self.readinessChanged.emit()
        if self.workers is None:
            try:self._apply_readiness(self.service.readiness_snapshot(), None)
            except Exception as exc:self._apply_readiness(None, exc)
            return
        future=self.workers.submit(self.service.readiness_snapshot)
        future.add_done_callback(lambda f:self._readinessReady.emit(None if f.exception() else f.result(), f.exception()))

    @Slot(object, object)
    def _apply_readiness(self, result, error):
        self._checking=False
        if error is not None:self._fail(error); self._readiness={}
        else:self._readiness=dict(result or {})
        self.readinessChanged.emit()

    @Slot()
    def refreshModels(self):
        if self._discovering_models:return
        self._discovering_models=True; self.modelsChanged.emit()
        if self.workers is None:
            try:self._apply_models(self.service.model_snapshot(),None)
            except Exception as exc:self._apply_models(None,exc)
            return
        future=self.workers.submit(self.service.model_snapshot)
        future.add_done_callback(lambda f:self._modelsReady.emit(None if f.exception() else f.result(), f.exception()))

    @Slot(object, object)
    def _apply_models(self, result, error):
        self._discovering_models=False
        if error is not None:
            self.logger.info("Onboarding model discovery failed", exc_info=error); self._models=[]
        else:self._models=list(result or [])
        self.modelsChanged.emit()

    @Slot()
    def continueWithoutAI(self):
        self.service.mark_continue_without_ai(); self.changed.emit(); self.next()

    @Slot()
    def openModels(self): self.openModelsRequested.emit()

    @Slot()
    def openTemplates(self): self.openTemplatesRequested.emit()

    @Slot(str, str, str, str, int)
    def createFirstProject(self, title, workflow, language, aspect, fps=30):
        clean=str(title or "").strip()
        if not clean:self.operationFailed.emit("Project name is required."); return
        self.firstProjectRequested.emit(clean, str(workflow or "video"), str(language or self.defaultContentLanguage), str(aspect or "16:9"), int(fps or 30))

    @Slot(str)
    def recordFirstProject(self, project_id):
        self.service.record_first_project(project_id); self.service.complete(project_id); self.changed.emit()

    @Slot()
    def finish(self):
        self.service.complete(); self.changed.emit(); self.closeRequested.emit()

    @Slot(str)
    def dismissTip(self, tip_id):
        self.service.dismiss_tip(tip_id); self.changed.emit()

    @Slot(str, result=bool)
    def shouldShowTip(self, tip_id): return self.service.should_show_tip(tip_id)

    @Slot(str)
    def openSettings(self, section="General"): self.openSettingsRequested.emit(section or "General")

    def _local_path(self, value):
        text=str(value or "")
        try:
            if text.startswith("file:"):
                local=QUrl(text).toLocalFile()
                if local:return local
        except Exception: pass
        return str(Path(text).expanduser())

    def _fail(self, exc):
        self.logger.exception("Onboarding action failed")
        self.operationFailed.emit(str(exc).strip() or "Setup could not complete that action. You can continue and try again later.")

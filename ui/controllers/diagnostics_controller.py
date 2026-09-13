from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QGuiApplication

from domain.diagnostic_result import DiagnosticResult
from services.diagnostics_preferences_service import DiagnosticsPreferencesService
from services.diagnostics_service import DiagnosticCancelled, DiagnosticsService
from services.platform_service import reveal_in_folder
from services.support_bundle_service import SupportBundleService


class DiagnosticsController(QObject):
    changed = Signal()
    logsChanged = Signal()
    bundleChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    _workReady = Signal(object)
    _workFailed = Signal(str)
    _bundleReady = Signal(object)

    def __init__(
        self,
        diagnostics: DiagnosticsService,
        support_bundles: SupportBundleService,
        preferences: DiagnosticsPreferencesService,
        worker_pool,
        logger=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.diagnostics = diagnostics
        self.support_bundles = support_bundles
        self.preferences = preferences
        self.worker_pool = worker_pool
        self.logger = logger
        self._results: list[DiagnosticResult] = []
        self._logs: list[dict[str, str]] = []
        self._running = False
        self._mode = ""
        self._cancel = threading.Event()
        self._last_bundle = None
        self._workReady.connect(self._apply_results)
        self._workFailed.connect(self._apply_failure)
        self._bundleReady.connect(self._apply_bundle)
        self.refreshLogs()

    @Property("QVariantList", notify=changed)
    def results(self) -> list[dict[str, object]]:
        return [item.to_dict(include_technical=True) for item in self._results]

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return self._running

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property("QVariantList", notify=logsChanged)
    def logs(self) -> list[dict[str, str]]:
        return list(self._logs)

    @Property(str, notify=logsChanged)
    def logSeverity(self) -> str:
        return self.preferences.log_severity

    @Property("QVariantMap", constant=True)
    def bundleReview(self) -> dict[str, list[str]]:
        return self.support_bundles.review()

    @Property(str, notify=bundleChanged)
    def lastBundlePath(self) -> str:
        return str(self._last_bundle.path) if self._last_bundle else ""

    @Property("QVariantList", notify=bundleChanged)
    def lastBundleFiles(self) -> list[str]:
        return list(self._last_bundle.files) if self._last_bundle else []

    @Slot()
    def runQuick(self) -> None:
        self._start("quick", lambda: self.diagnostics.quick_check(self._cancel))

    @Slot(str)
    def runFull(self, project_id: str = "") -> None:
        self._start("full", lambda: self.diagnostics.full_diagnostics(self._cancel, project_id))

    @Slot(str)
    def diagnoseProject(self, project_id: str) -> None:
        if not project_id:
            self.operationFailed.emit("Open a project before running project diagnostics.")
            return
        self._start("project", lambda: self.diagnostics.diagnose_project(project_id))

    @Slot(str)
    def diagnoseRender(self, technical_text: str) -> None:
        self._results = [self.diagnostics.diagnose_render_failure(technical_text)]
        self.changed.emit()

    @Slot()
    def cancel(self) -> None:
        if self._running:
            self._cancel.set()

    @Slot(str)
    def setLogSeverity(self, value: str) -> None:
        try:
            self.preferences.set_log_severity(value)
            self.refreshLogs()
        except Exception as exc:
            self.operationFailed.emit(str(exc))

    @Slot()
    def refreshLogs(self) -> None:
        self._logs = self.diagnostics.recent_logs(self.preferences.log_severity, self.preferences.log_limit)
        self.logsChanged.emit()

    @Slot(str)
    def copyText(self, value: str) -> None:
        QGuiApplication.clipboard().setText(self.diagnostics.redaction.redact_text(value))
        self.operationSucceeded.emit("Copied sanitized diagnostic text.")

    @Slot()
    def copyShortReport(self) -> None:
        QGuiApplication.clipboard().setText(self.diagnostics.short_report(self._results))
        self.operationSucceeded.emit("Copied sanitized diagnostic report.")

    @Slot()
    def createSupportBundle(self) -> None:
        if self._running:
            return
        self._running = True
        self._mode = "bundle"
        self.changed.emit()
        future = self.worker_pool.submit(
            self.support_bundles.create,
            list(self._results),
            log_limit=self.preferences.log_limit,
        )
        future.add_done_callback(self._bundle_done)

    @Slot()
    def openLogsFolder(self) -> None:
        try:
            reveal_in_folder(Path(self.diagnostics.paths.logs))
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "Logs folder could not be opened.")

    @Slot()
    def openBundleFolder(self) -> None:
        if not self._last_bundle:
            return
        try:
            reveal_in_folder(Path(self._last_bundle.path))
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "Support bundle folder could not be opened.")

    @Slot()
    def rebuildAppDirectories(self) -> None:
        try:
            self.diagnostics.rebuild_app_owned_directories()
            self.operationSucceeded.emit("Missing app-owned folders were recreated safely.")
            self.runQuick()
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "App-owned folders could not be repaired.")

    def _start(self, mode: str, fn) -> None:
        if self._running:
            return
        self._cancel = threading.Event()
        self._running = True
        self._mode = mode
        self.changed.emit()
        future = self.worker_pool.submit(fn)
        future.add_done_callback(self._future_done)

    def _future_done(self, future) -> None:
        try:
            self._workReady.emit(future.result())
        except DiagnosticCancelled:
            self._workFailed.emit("Diagnostics cancelled.")
        except Exception as exc:
            if self.logger:
                self.logger.exception("Diagnostics worker failed")
            self._workFailed.emit(str(exc) or "Diagnostics could not complete.")

    def _bundle_done(self, future) -> None:
        try:
            self._bundleReady.emit(future.result())
        except Exception as exc:
            if self.logger:
                self.logger.exception("Support bundle creation failed")
            self._workFailed.emit(str(exc) or "Support bundle could not be created.")

    @Slot(object)
    def _apply_results(self, value) -> None:
        self._results = list(value or [])
        self._running = False
        self._mode = ""
        self.changed.emit()
        self.operationSucceeded.emit("Diagnostics completed.")

    @Slot(str)
    def _apply_failure(self, message: str) -> None:
        self._running = False
        self._mode = ""
        self.changed.emit()
        if message == "Diagnostics cancelled.":
            self.operationSucceeded.emit(message)
        else:
            self.operationFailed.emit(message)

    @Slot(object)
    def _apply_bundle(self, bundle) -> None:
        self._last_bundle = bundle
        self._running = False
        self._mode = ""
        self.changed.emit()
        self.bundleChanged.emit()
        self.operationSucceeded.emit("Privacy-safe support bundle created locally.")

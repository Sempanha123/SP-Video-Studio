from __future__ import annotations

import threading

from app.constants import APP_VERSION
from domain.update_state import UpdateStateCode
from services.update_service import UpdateBlockedError, UpdateInstallError, UpdateService

try:
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtGui import QDesktopServices
except ImportError:  # focused non-GUI tests
    class QObject:
        def __init__(self, parent=None): pass
    class _Signal:
        def __init__(self, *args): pass
        def emit(self, *args): pass
    Signal = _Signal
    def Slot(*args, **kwargs): return lambda fn: fn
    def Property(*args, **kwargs): return lambda fn: property(fn)
    QUrl = str
    class QDesktopServices:
        @staticmethod
        def openUrl(url): return False


class _CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()
    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()
    def cancel(self) -> None:
        self._event.set()


class UpdateController(QObject):
    changed = Signal()
    updateAvailable = Signal()
    installerLaunched = Signal()

    def __init__(self, service: UpdateService, worker_pool=None, *, quit_callback=None, configured=True, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.worker_pool = worker_pool
        self.quit_callback = quit_callback or (lambda: None)
        self._configured = bool(configured)
        self._download_token: _CancelToken | None = None
        self._future = None

    @Property(str, notify=changed)
    def currentVersion(self): return APP_VERSION
    @Property(str, notify=changed)
    def channel(self): return "Stable"
    @Property(bool, notify=changed)
    def configured(self): return self._configured
    @Property(bool, notify=changed)
    def automaticCheck(self): return bool(self.service.state.automatic_check)
    @Property(str, notify=changed)
    def state(self): return str(self.service.state.state)
    @Property(str, notify=changed)
    def availableVersion(self): return str(self.service.state.available_version)
    @Property(float, notify=changed)
    def progress(self): return float(self.service.state.progress)
    @Property(str, notify=changed)
    def errorMessage(self): return str(self.service.state.last_error)
    @Property(str, notify=changed)
    def releaseNotes(self): return self.service.manifest.release_notes if self.service.manifest else ""
    @Property(str, notify=changed)
    def releaseNotesUrl(self): return self.service.manifest.release_notes_url if self.service.manifest else ""
    @Property(bool, notify=changed)
    def installReady(self): return self.service.state.state == UpdateStateCode.READY.value and bool(self.service.state.installer_validated)
    @Property(str, notify=changed)
    def activeWorkMessage(self):
        active = self.service.active_work()
        return "Finish or pause: " + ", ".join(active) if active else ""

    @Slot(bool)
    def setAutomaticallyCheck(self, enabled: bool):
        self.service.set_automatic_check(enabled); self.changed.emit()

    @Slot()
    def checkForUpdates(self):
        if not self._configured:
            return
        self._submit(self._check)

    def _check(self):
        manifest = self.service.check()
        self.changed.emit()
        if manifest is not None:
            self.updateAvailable.emit()
        return manifest

    @Slot()
    def downloadUpdate(self):
        if not self._configured:
            return
        self._download_token = _CancelToken()
        self._submit(lambda: self._download(self._download_token))

    def _download(self, token):
        try:
            return self.service.download(cancellation=token, progress=lambda _value: self.changed.emit())
        finally:
            self.changed.emit()

    @Slot()
    def cancelDownload(self):
        if self._download_token is not None:
            self._download_token.cancel()

    @Slot()
    def retry(self):
        if self.service.manifest is not None: self.downloadUpdate()
        else: self.checkForUpdates()

    @Slot()
    def installNow(self):
        try:
            self.service.install_ready_update()
        except (UpdateBlockedError, UpdateInstallError) as exc:
            self.service.state_service.update(last_error=str(exc)[:500])
            self.changed.emit(); return
        self.changed.emit(); self.installerLaunched.emit(); self.quit_callback()

    @Slot()
    def openReleaseNotes(self):
        url = self.releaseNotesUrl
        if url.startswith("https://"):
            QDesktopServices.openUrl(QUrl(url))

    def _submit(self, fn):
        if self.worker_pool is None:
            try: fn()
            except Exception: pass
            self.changed.emit(); return
        future = self.worker_pool.submit(fn)
        self._future = future
        def done(_future):
            try: _future.result()
            except Exception: pass
            self.changed.emit()
        future.add_done_callback(done)

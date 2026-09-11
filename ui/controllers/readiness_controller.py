from __future__ import annotations

import logging
from concurrent.futures import Future

from PySide6.QtCore import QObject, Property, Signal, Slot

from domain.system_readiness import SystemReadiness
from services.system_readiness_service import SystemReadinessService
from workers.worker_pool import WorkerPool


class ReadinessController(QObject):
    readinessChanged = Signal()
    checkingChanged = Signal()
    operationFailed = Signal(str)
    _resultReady = Signal(object)
    _resultFailed = Signal(str)

    def __init__(
        self,
        service: SystemReadinessService,
        worker_pool: WorkerPool,
        logger: logging.Logger,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.worker_pool = worker_pool
        self.logger = logger
        self._readiness = SystemReadiness().to_dict()
        self._checking = False
        self._resultReady.connect(self._apply_result)
        self._resultFailed.connect(self._apply_error)

    @Property("QVariantMap", notify=readinessChanged)
    def readiness(self) -> dict[str, object]:
        return self._readiness

    @Property(bool, notify=checkingChanged)
    def checking(self) -> bool:
        return self._checking

    @Slot()
    def recheck(self) -> None:
        if self._checking:
            return
        self._checking = True
        self.checkingChanged.emit()
        future = self.worker_pool.submit(self.service.detect)
        future.add_done_callback(self._future_done)

    def _future_done(self, future: Future[object]) -> None:
        try:
            result = future.result()
            if not isinstance(result, SystemReadiness):
                raise TypeError("Readiness service returned an unexpected result.")
            self._resultReady.emit(result)
        except Exception as exc:
            self.logger.exception("System readiness check failed")
            self._resultFailed.emit(str(exc))

    @Slot(object)
    def _apply_result(self, result: object) -> None:
        assert isinstance(result, SystemReadiness)
        self._readiness = result.to_dict()
        self._checking = False
        self.readinessChanged.emit()
        self.checkingChanged.emit()

    @Slot(str)
    def _apply_error(self, message: str) -> None:
        self._checking = False
        self.checkingChanged.emit()
        self.operationFailed.emit(message or "System readiness detection is unavailable.")

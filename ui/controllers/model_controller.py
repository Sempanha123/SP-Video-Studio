from __future__ import annotations

import logging
from concurrent.futures import Future

from PySide6.QtCore import QObject, Property, Signal, Slot

from domain.system_readiness import format_bytes
from engines.model_sources import DownloadCancelled
from services.model_download_service import ModelDownloadProgress
from services.model_service import ModelError, ModelService
from services.system_readiness_service import SystemReadinessService
from ui.models.model_list_model import ModelListModel
from workers.cancellation import CancellationToken
from workers.worker_pool import WorkerPool


class ModelController(QObject):
    modelsChanged = Signal()
    busyChanged = Signal()
    storageChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    modelStateChanged = Signal()
    _refreshReady = Signal(object)
    _refreshFailed = Signal(str)
    _progressReady = Signal(object)
    _jobFinished = Signal(str, bool, str)

    def __init__(
        self,
        service: ModelService,
        readiness_service: SystemReadinessService,
        worker_pool: WorkerPool,
        logger: logging.Logger,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.readiness_service = readiness_service
        self.worker_pool = worker_pool
        self.logger = logger
        self._model = ModelListModel(self)
        self._busy = False
        self._active_model_id = ""
        self._active_token: CancellationToken | None = None
        self._total_storage = 0
        self._refreshReady.connect(self._apply_refresh)
        self._refreshFailed.connect(self._apply_refresh_error)
        self._progressReady.connect(self._apply_progress)
        self._jobFinished.connect(self._apply_job_finished)

    @Property(QObject, constant=True)
    def models(self) -> QObject:
        return self._model

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=busyChanged)
    def activeModelId(self) -> str:
        return self._active_model_id

    @Property(str, notify=storageChanged)
    def totalModelStorage(self) -> str:
        return format_bytes(self._total_storage)

    @Slot()
    def refresh(self) -> None:
        if self._busy and not self._active_model_id:
            return
        future = self.worker_pool.submit(self._refresh_job)
        future.add_done_callback(self._refresh_done)

    def _refresh_job(self):
        readiness = self.readiness_service.detect()
        return self.service.refresh(readiness), self.service.total_storage_bytes()

    def _refresh_done(self, future: Future[object]) -> None:
        try:
            self._refreshReady.emit(future.result())
        except Exception as exc:
            self.logger.exception("Model refresh failed")
            self._refreshFailed.emit(str(exc))

    @Slot(str)
    def install(self, model_id: str) -> None:
        self._start_download_operation(model_id, repair=False)

    @Slot(str)
    def repair(self, model_id: str) -> None:
        self._start_download_operation(model_id, repair=True)

    def _start_download_operation(self, model_id: str, repair: bool) -> None:
        if self._active_model_id:
            self.operationFailed.emit("Only one AI model download can run at a time.")
            return
        try:
            self.service.registry.get(model_id)
        except KeyError:
            self.operationFailed.emit("This AI model is not in the model catalog.")
            return
        self._active_model_id = model_id
        self._active_token = CancellationToken()
        self._set_busy(True)
        self._model.update_model(model_id, {"status": "downloading", "statusDisplay": "Downloading", "errorMessage": ""})

        def progress(value: ModelDownloadProgress) -> None:
            self._progressReady.emit(value)

        def job() -> object:
            assert self._active_token is not None
            if repair:
                return self.service.repair(model_id, self._active_token, progress)
            return self.service.install(model_id, self._active_token, progress)

        future = self.worker_pool.submit(job)
        future.add_done_callback(lambda item: self._model_job_done(model_id, item, "repaired" if repair else "installed"))

    @Slot(str)
    def cancelDownload(self, model_id: str) -> None:
        if self._active_model_id == model_id and self._active_token is not None:
            self._active_token.cancel()

    @Slot(str)
    def removePartial(self, model_id: str) -> None:
        try:
            self.service.remove_partial(model_id)
            self.operationSucceeded.emit("Partial model download removed.")
            self.modelStateChanged.emit()
            self.refresh()
        except Exception as exc:
            self.logger.exception("Removing partial model download failed")
            self.operationFailed.emit(_user_error(exc))

    @Slot(str)
    def verify(self, model_id: str) -> None:
        self._submit_simple(model_id, "verify", self.service.verify, "Model verification completed.")

    @Slot(str)
    def remove(self, model_id: str) -> None:
        if self._active_model_id == model_id:
            self.cancelDownload(model_id)
            self.operationFailed.emit("Cancel the active download before removing this model.")
            return
        self._submit_simple(model_id, "remove", self.service.remove, "AI model removed.")

    @Slot(str)
    def openFolder(self, model_id: str) -> None:
        try:
            self.service.open_folder(model_id)
        except Exception as exc:
            self.operationFailed.emit(_user_error(exc))

    @Slot(str, result="QVariantMap")
    def modelDetails(self, model_id: str) -> dict[str, object]:
        return self._model.get(model_id) or {}

    def _submit_simple(self, model_id: str, action: str, fn, success_message: str) -> None:
        if self._active_model_id:
            self.operationFailed.emit("Wait for the active model download to finish or cancel it first.")
            return
        self._set_busy(True)
        future = self.worker_pool.submit(fn, model_id)

        def done(item: Future[object]) -> None:
            try:
                item.result()
                self._jobFinished.emit(action, True, success_message)
            except Exception as exc:
                self.logger.exception("Model %s failed: %s", action, model_id)
                self._jobFinished.emit(action, False, _user_error(exc))

        future.add_done_callback(done)

    def _model_job_done(self, model_id: str, future: Future[object], action: str) -> None:
        try:
            future.result()
            self._jobFinished.emit(action, True, f"{self.service.registry.get(model_id).name} {action}.")
        except DownloadCancelled:
            self._jobFinished.emit(action, True, "Model download paused.")
        except Exception as exc:
            self.logger.exception("Model download operation failed: %s", model_id)
            self._jobFinished.emit(action, False, _user_error(exc))

    @Slot(object)
    def _apply_refresh(self, payload: object) -> None:
        models, total = payload
        self._model.replace(models)
        self._total_storage = int(total)
        self.modelsChanged.emit()
        self.storageChanged.emit()

    @Slot(str)
    def _apply_refresh_error(self, message: str) -> None:
        self.operationFailed.emit(message or "Model catalog could not be refreshed.")

    @Slot(object)
    def _apply_progress(self, value: object) -> None:
        assert isinstance(value, ModelDownloadProgress)
        self._model.update_model(
            value.model_id,
            {
                "status": value.state,
                "statusDisplay": value.state.replace("_", " ").title(),
                "downloadedBytes": value.downloaded_bytes,
                "totalBytes": value.total_bytes,
                "progress": value.fraction,
                "downloadSpeed": value.speed_bytes_per_second,
                "currentFile": value.current_file,
                "downloadedDisplay": format_bytes(value.downloaded_bytes),
                "totalDisplay": format_bytes(value.total_bytes),
            },
        )

    @Slot(str, bool, str)
    def _apply_job_finished(self, action: str, success: bool, message: str) -> None:
        self._active_model_id = ""
        self._active_token = None
        self._set_busy(False)
        if success:
            self.operationSucceeded.emit(message)
        else:
            self.operationFailed.emit(message)
        self.modelStateChanged.emit()
        self.refresh()

    def _set_busy(self, value: bool) -> None:
        if self._busy == value:
            return
        self._busy = value
        self.busyChanged.emit()


def _user_error(exc: Exception) -> str:
    if isinstance(exc, ModelError):
        return str(exc) or exc.user_message
    text = str(exc).strip()
    return text or "MMO Video Studio could not complete this model action."

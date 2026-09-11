from __future__ import annotations

import logging
from concurrent.futures import Future
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from domain.generated_audio import GeneratedAudio
from domain.narration import NarrationProgress
from domain.voice_config import VoiceConfig
from engines.tts.errors import TTSCancelled, TTSError, TTSOutOfMemory
from services.narration_service import NarrationService
from services.tts_service import TTSService
from workers.cancellation import CancellationToken
from workers.tts_worker import TTSWorker
from workers.worker_pool import WorkerPool


class TTSController(QObject):
    stateChanged = Signal()
    generatedChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    modelStateChanged = Signal()
    previewReady = Signal(str, str, int)
    generatedAudioAboutToRemove = Signal(str)
    _progressReady = Signal(object)
    _jobReady = Signal(object)
    _jobFailed = Signal(str)
    _previewReadyInternal = Signal(object)

    def __init__(
        self,
        narration: NarrationService,
        tts_service: TTSService,
        worker_pool: WorkerPool,
        logger: logging.Logger,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.narration = narration
        self.tts_service = tts_service
        self.worker_pool = worker_pool
        self.logger = logger
        self._project_id = ""
        self._busy = False
        self._state = "idle"
        self._status = "Ready"
        self._progress = 0.0
        self._current_chunk = 0
        self._total_chunks = 0
        self._token: CancellationToken | None = None
        self._future: Future[object] | None = None
        self._generated: list[dict[str, object]] = []
        self._active: dict[str, object] = {}
        self._current = False
        self._reference_path = ""
        self._progressReady.connect(self._apply_progress)
        self._jobReady.connect(self._apply_job_ready)
        self._jobFailed.connect(self._apply_job_failed)
        self._previewReadyInternal.connect(self._apply_preview_ready)

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(str, notify=stateChanged)
    def statusMessage(self) -> str:
        return self._status

    @Property(float, notify=stateChanged)
    def progress(self) -> float:
        return self._progress

    @Property(int, notify=stateChanged)
    def currentChunk(self) -> int:
        return self._current_chunk

    @Property(int, notify=stateChanged)
    def totalChunks(self) -> int:
        return self._total_chunks

    @Property("QVariantList", notify=generatedChanged)
    def generated(self) -> list[dict[str, object]]:
        return list(self._generated)

    @Property("QVariantMap", notify=generatedChanged)
    def activeGenerated(self) -> dict[str, object]:
        return dict(self._active)

    @Property(bool, notify=generatedChanged)
    def narrationCurrent(self) -> bool:
        return self._current

    @Property(str, notify=stateChanged)
    def referencePath(self) -> str:
        return self._reference_path

    @Slot(str)
    def setCurrentProject(self, project_id: str) -> None:
        project_id = (project_id or "").strip()
        if project_id == self._project_id:
            self.refresh()
            return
        self.cancel()
        self._project_id = project_id
        self._reference_path = ""
        self._reset_state()
        self.refresh()

    @Slot(str)
    def setReferencePath(self, value: str) -> None:
        self._reference_path = _local_path(value)
        self.stateChanged.emit()

    @Slot()
    def refresh(self) -> None:
        if not self._project_id:
            self._generated = []
            self._active = {}
            self._current = False
            self.generatedChanged.emit()
            return
        try:
            items = self.narration.list_generated(self._project_id)
            active = self.narration.active(self._project_id)
            self._generated = [_generated_map(item, self.narration.narration_is_current(self._project_id, item)) for item in items]
            self._active = _generated_map(active, self.narration.narration_is_current(self._project_id, active)) if active else {}
            self._current = bool(active and self.narration.narration_is_current(self._project_id, active))
            self.generatedChanged.emit()
        except Exception as exc:
            self.logger.exception("Could not refresh narration")
            self.operationFailed.emit(_friendly_error(exc))

    @Slot(str, str, str, float, int, str, bool, result=bool)
    def generateFull(
        self,
        mode: str,
        description: str,
        device: str,
        cfg_value: float,
        steps: int,
        seed_text: str,
        consent: bool,
    ) -> bool:
        if not self._project_id:
            self.operationFailed.emit("Open a project before generating narration.")
            return False
        config = self._config(mode, description, device, cfg_value, steps, seed_text, consent)
        return self._start_worker(TTSWorker(self.narration, self._project_id, config))

    @Slot(str, str, str, str, float, int, str, bool, result=bool)
    def generateSection(
        self,
        section_id: str,
        mode: str,
        description: str,
        device: str,
        cfg_value: float,
        steps: int,
        seed_text: str,
        consent: bool,
    ) -> bool:
        if not self._project_id or not section_id:
            self.operationFailed.emit("Select a script section first.")
            return False
        config = self._config(mode, description, device, cfg_value, steps, seed_text, consent)
        return self._start_worker(TTSWorker(self.narration, self._project_id, config, section_id=section_id))

    @Slot(str, str, str, str, float, int, str, bool, result=bool)
    def generatePreview(
        self,
        text: str,
        mode: str,
        description: str,
        device: str,
        cfg_value: float,
        steps: int,
        seed_text: str,
        consent: bool,
    ) -> bool:
        if self._busy:
            self.operationFailed.emit("Narration generation is already running.")
            return False
        if not self._project_id:
            self.operationFailed.emit("Open a project before generating a preview.")
            return False
        try:
            script, _ = self.narration.script_service.load_or_create(self._project_id)
            config = self._config(mode, description, device, cfg_value, steps, seed_text, consent)
        except Exception as exc:
            self.operationFailed.emit(_friendly_error(exc))
            return False
        token = CancellationToken()
        self._token = token
        self._set_busy(True, "preparing", "Preparing voice preview…")

        def job() -> object:
            path = self.narration.generate_preview(self._project_id, text, script.language, config, token)
            duration, _, _ = self.narration._validate_wav(path)
            return str(path), "Voice preview", duration

        self._future = self.worker_pool.submit(job)
        self._future.add_done_callback(self._preview_done)
        return True

    @Slot()
    def cancel(self) -> None:
        if self._token is not None:
            self._token.cancel()
            self._status = "Stopping after current segment…"
            self._state = "cancelling"
            self.stateChanged.emit()

    @Slot()
    def unloadModel(self) -> None:
        if self._busy:
            self.operationFailed.emit("Wait for the current narration job to stop first.")
            return

        def job() -> object:
            self.tts_service.unload()
            return True

        future = self.worker_pool.submit(job)
        future.add_done_callback(self._unload_done)

    @Slot(str, result=bool)
    def setActiveGenerated(self, generated_audio_id: str) -> bool:
        if not self._project_id or not generated_audio_id or self._busy:
            return False
        try:
            self.narration.set_active_generated(self._project_id, generated_audio_id)
            self.refresh()
            self.operationSucceeded.emit("Active narration updated.")
            return True
        except Exception as exc:
            self.logger.exception("Could not activate generated narration")
            self.operationFailed.emit(_friendly_error(exc))
            return False

    @Slot(str, result=bool)
    def deleteGenerated(self, generated_audio_id: str) -> bool:
        if not self._project_id or not generated_audio_id or self._busy:
            return False
        try:
            item = self.narration.get_generated(self._project_id, generated_audio_id)
            self.generatedAudioAboutToRemove.emit(item.file_path)
            self.narration.delete_generated(self._project_id, generated_audio_id)
            self.refresh()
            self.operationSucceeded.emit("Generated narration removed.")
            return True
        except Exception as exc:
            self.logger.exception("Could not remove generated narration")
            self.operationFailed.emit(_friendly_error(exc))
            return False

    def _config(
        self,
        mode: str,
        description: str,
        device: str,
        cfg_value: float,
        steps: int,
        seed_text: str,
        consent: bool,
    ) -> VoiceConfig:
        seed: int | None = None
        if (seed_text or "").strip():
            try:
                seed = int(seed_text.strip())
            except ValueError as exc:
                raise ValueError("Seed must be an integer.") from exc
        reference = self._reference_path if mode == "reference" else ""
        if reference:
            if not consent:
                raise ValueError("Confirm that you have permission to use the reference voice.")
            reference = str(self.narration.prepare_reference_audio(self._project_id, reference))
        return VoiceConfig(
            mode=mode or "default",
            description=description or "",
            reference_audio_path=reference,
            consent_confirmed=bool(consent),
            cfg_value=float(cfg_value),
            inference_timesteps=int(steps),
            seed=seed,
            device=device or "auto",
        )

    def _start_worker(self, worker: TTSWorker) -> bool:
        if self._busy:
            self.operationFailed.emit("Narration generation is already running.")
            return False
        token = CancellationToken()
        worker.cancellation = token
        worker.progress_callback = self._queue_progress
        self._token = token
        self._set_busy(True, "queued", "Preparing narration…")
        self._future = self.worker_pool.submit(worker.run)
        self._future.add_done_callback(self._job_done)
        return True

    def _queue_progress(self, value: NarrationProgress) -> None:
        self._progressReady.emit(value)

    def _job_done(self, future: Future[object]) -> None:
        try:
            self._jobReady.emit(future.result())
        except Exception as exc:
            self.logger.exception("Narration generation failed")
            self._jobFailed.emit(_friendly_error(exc))

    def _preview_done(self, future: Future[object]) -> None:
        try:
            self._previewReadyInternal.emit(future.result())
        except Exception as exc:
            self.logger.exception("Voice preview generation failed")
            self._jobFailed.emit(_friendly_error(exc))

    def _unload_done(self, future: Future[object]) -> None:
        try:
            future.result()
            self.modelStateChanged.emit()
            self.operationSucceeded.emit("VoxCPM2 unloaded.")
        except Exception as exc:
            self.operationFailed.emit(_friendly_error(exc))

    @Slot(object)
    def _apply_progress(self, value: object) -> None:
        if not isinstance(value, NarrationProgress):
            return
        self._state = str(value.state)
        self._status = value.message
        self._current_chunk = value.current
        self._total_chunks = value.total
        self._progress = value.ratio
        self.stateChanged.emit()

    @Slot(object)
    def _apply_job_ready(self, value: object) -> None:
        self._set_busy(False, "completed", "Narration ready")
        self.modelStateChanged.emit()
        self.refresh()
        if isinstance(value, GeneratedAudio):
            self.operationSucceeded.emit("Narration generated.")

    @Slot(str)
    def _apply_job_failed(self, message: str) -> None:
        cancelled = message.lower().startswith("cancel") or "cancelled" in message.lower()
        self._set_busy(False, "cancelled" if cancelled else "failed", "Generation cancelled" if cancelled else message)
        self.modelStateChanged.emit()
        if cancelled:
            self.operationSucceeded.emit("Narration generation cancelled.")
        else:
            self.operationFailed.emit(message)

    @Slot(object)
    def _apply_preview_ready(self, value: object) -> None:
        path, name, duration = value
        self._set_busy(False, "completed", "Voice preview ready")
        self.modelStateChanged.emit()
        self.previewReady.emit(str(path), str(name), int(duration))
        self.operationSucceeded.emit("Voice preview generated.")

    def _set_busy(self, busy: bool, state: str, message: str) -> None:
        self._busy = busy
        self._state = state
        self._status = message
        if not busy:
            self._token = None
            self._future = None
            self._current_chunk = 0
            self._total_chunks = 0
            self._progress = 1.0 if state == "completed" else 0.0
        self.stateChanged.emit()

    def _reset_state(self) -> None:
        self._busy = False
        self._state = "idle"
        self._status = "Ready"
        self._progress = 0.0
        self._current_chunk = 0
        self._total_chunks = 0
        self._token = None
        self._future = None
        self.stateChanged.emit()


def _generated_map(item: GeneratedAudio | None, current: bool) -> dict[str, object]:
    if item is None:
        return {}
    value = item.to_dict()
    value["current"] = bool(current)
    seconds = max(0, item.duration_ms // 1000)
    value["durationDisplay"] = f"{seconds // 60:02d}:{seconds % 60:02d}"
    return value


def _local_path(value: str) -> str:
    raw = str(value or "")
    if raw.startswith("file:"):
        parsed = urlparse(raw)
        path = unquote(parsed.path)
        if parsed.netloc:
            path = f"//{parsed.netloc}{path}"
        if len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path
    return QUrl(raw).toLocalFile() if raw else ""


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, TTSCancelled):
        return "Narration generation cancelled."
    if isinstance(exc, TTSOutOfMemory):
        return "VoxCPM2 ran out of GPU memory. Try CPU, Low Memory mode, or a shorter section."
    if isinstance(exc, TTSError):
        return str(exc) or "VoxCPM2 could not complete this narration request."
    text = str(exc).strip()
    return text or "MMO Video Studio could not generate narration."

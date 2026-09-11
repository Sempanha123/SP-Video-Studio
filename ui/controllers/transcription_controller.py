from __future__ import annotations

import logging
from concurrent.futures import Future
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from domain.transcript import Transcript, TranscriptStatus
from engines.stt.errors import STTCancelled, STTError
from engines.stt.types import TranscriptionRequest
from services.transcription_service import TranscriptionService
from ui.models.transcript_segment_model import TranscriptSegmentListModel
from workers.cancellation import CancellationToken
from workers.worker_pool import WorkerPool


class TranscriptionController(QObject):
    contextChanged = Signal()
    transcriptChanged = Signal()
    stateChanged = Signal()
    modelsChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    playbackRequested = Signal(str, int, bool)
    _progressReady = Signal(str, object, int, int, str)
    _jobReady = Signal(object)
    _jobFailed = Signal(object)

    def __init__(self, service: TranscriptionService, worker_pool: WorkerPool, logger=None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.worker_pool = worker_pool
        self.logger = logger or logging.getLogger("sp_video_studio.transcription_controller")
        self.segmentModel = TranscriptSegmentListModel(self)
        self._project_id = ""
        self._media_id = ""
        self._media_name = ""
        self._media_type = ""
        self._transcript: Transcript | None = None
        self._busy = False
        self._state = "idle"
        self._status = "Select audio or video to transcribe."
        self._progress: float = 0.0
        self._progress_known = False
        self._processed_ms = 0
        self._duration_ms = 0
        self._token: CancellationToken | None = None
        self._future: Future[object] | None = None
        self._dirty: dict[str, str] = {}
        self._save_state = "Saved"
        self._autosave = QTimer(self)
        self._autosave.setSingleShot(True)
        self._autosave.setInterval(1200)
        self._autosave.timeout.connect(self.saveEdits)
        self._progressReady.connect(self._apply_progress)
        self._jobReady.connect(self._apply_result)
        self._jobFailed.connect(self._apply_failure)

    @Property(QObject, constant=True)
    def segments(self):
        return self.segmentModel

    @Property(str, notify=contextChanged)
    def currentProjectId(self) -> str:
        return self._project_id

    @Property(str, notify=contextChanged)
    def mediaId(self) -> str:
        return self._media_id

    @Property(str, notify=contextChanged)
    def mediaName(self) -> str:
        return self._media_name

    @Property(str, notify=contextChanged)
    def mediaType(self) -> str:
        return self._media_type

    @Property(bool, notify=contextChanged)
    def canTranscribe(self) -> bool:
        return self._media_type in {"audio", "video"}

    @Property("QVariantMap", notify=transcriptChanged)
    def transcript(self) -> dict[str, object]:
        if self._transcript is None:
            return {}
        result = self._transcript.to_dict()
        probability = self._transcript.language_probability
        result["languageName"] = {"en": "English", "km": "Khmer"}.get(self._transcript.detected_language or "", self._transcript.detected_language or "Unknown")
        result["languageProbabilityText"] = f"{probability * 100:.0f}%" if probability is not None else ""
        result["statusName"] = self._transcript.status_code.replace("_", " ").title()
        return result

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

    @Property(bool, notify=stateChanged)
    def progressKnown(self) -> bool:
        return self._progress_known

    @Property(int, notify=stateChanged)
    def processedMs(self) -> int:
        return self._processed_ms

    @Property(int, notify=stateChanged)
    def durationMs(self) -> int:
        return self._duration_ms

    @Property(str, notify=stateChanged)
    def saveState(self) -> str:
        return self._save_state

    @Property("QVariantList", notify=modelsChanged)
    def models(self) -> list[dict[str, object]]:
        recommended = self.service.recommended_model_id()
        result = []
        for model in self.service.supported_models():
            installation = self.service.model_service.repository.get(model.model_id)
            installed = bool(installation and installation.status_code == "installed")
            result.append({
                "id": model.model_id,
                "name": model.name,
                "installed": installed,
                "recommended": model.model_id == recommended,
                "description": model.description,
            })
        return result

    @Property(str, notify=modelsChanged)
    def recommendedModelId(self) -> str:
        return self.service.recommended_model_id()

    @Slot(str)
    def setCurrentProject(self, project_id: str) -> None:
        project_id = (project_id or "").strip()
        if project_id == self._project_id:
            return
        if self._dirty:
            self.saveEdits()
        self.cancel()
        self._project_id = project_id
        self._media_id = ""
        self._media_name = ""
        self._media_type = ""
        self._transcript = None
        self.segmentModel.replace([])
        self.contextChanged.emit(); self.transcriptChanged.emit(); self.modelsChanged.emit()

    @Slot(str)
    def mediaRemoving(self, media_id: str) -> None:
        if media_id and media_id == self._media_id:
            self.cancel()
            self._media_id = ""
            self._media_name = ""
            self._media_type = ""
            self._transcript = None
            self.segmentModel.replace([])
            self.contextChanged.emit(); self.transcriptChanged.emit()

    @Slot(str, result=bool)
    def setMedia(self, media_id: str) -> bool:
        media_id = (media_id or "").strip()
        if self._dirty:
            self.saveEdits()
        self._media_id = media_id
        self._transcript = None
        self.segmentModel.replace([])
        if not media_id or not self._project_id:
            self._media_name = ""
            self._media_type = ""
            self.contextChanged.emit(); self.transcriptChanged.emit()
            return False
        try:
            asset = self.service.media_service.get_media(self._project_id, media_id)
            self._media_name = asset.name
            self._media_type = asset.type
            transcript, segments = self.service.get_active(self._project_id, media_id)
            self._transcript = transcript
            self.segmentModel.replace(segments)
            self._duration_ms = int(asset.duration_ms or (transcript.duration_ms if transcript else 0))
            self._status = "Transcript ready" if transcript else ("Ready to transcribe" if self.canTranscribe else "Images cannot be transcribed")
            self.contextChanged.emit(); self.transcriptChanged.emit(); self.stateChanged.emit(); self.modelsChanged.emit()
            return self.canTranscribe
        except Exception as exc:
            self.logger.exception("Could not load transcription context")
            self.operationFailed.emit(self._friendly(exc))
            return False

    @Slot(str, str, str, bool, bool, bool, int, int, str, str, str, result=bool)
    def start(
        self,
        model_id: str,
        language: str,
        device: str,
        word_timestamps: bool,
        vad_enabled: bool,
        batch_mode: bool,
        batch_size: int,
        beam_size: int,
        compute_type: str,
        initial_prompt: str,
        hotwords: str,
    ) -> bool:
        if self._busy:
            self.operationFailed.emit("A transcription is already running.")
            return False
        if not self.canTranscribe or not self._media_id:
            self.operationFailed.emit("Select an audio or video file first.")
            return False
        model_id = model_id or self.service.recommended_model_id()
        if not model_id:
            self.operationFailed.emit("No speech recognition model is installed.")
            return False
        asset = self.service.media_service.get_media(self._project_id, self._media_id)
        request = TranscriptionRequest(
            project_id=self._project_id,
            media_id=self._media_id,
            model_id=model_id,
            source_path=asset.project_path,
            language=language or "auto",
            word_timestamps=word_timestamps,
            vad_enabled=vad_enabled,
            device=device or "auto",
            compute_type=compute_type or "auto",
            beam_size=int(beam_size),
            batch_mode=batch_mode,
            batch_size=int(batch_size),
            initial_prompt=initial_prompt or "",
            hotwords=hotwords or "",
        )
        self._token = CancellationToken()
        self._busy = True
        self._state = "preparing"
        self._status = "Preparing transcription…"
        self._progress = 0.0
        self._progress_known = bool(asset.duration_ms)
        self._processed_ms = 0
        self._duration_ms = int(asset.duration_ms or 0)
        self.stateChanged.emit()

        def report(state, fraction, processed, duration, message):
            self._progressReady.emit(state, fraction, processed, duration, message)

        def job():
            return self.service.transcribe(request, self._token, report)

        self._future = self.worker_pool.submit(job)
        self._future.add_done_callback(self._done)
        return True

    @Slot()
    def cancel(self) -> None:
        if self._token is not None and self._busy:
            self._token.cancel()
            self._state = "cancelling"
            self._status = "Stopping transcription…"
            self.stateChanged.emit()

    @Slot(str, str)
    def editSegment(self, segment_id: str, text: str) -> None:
        if self._transcript is None:
            return
        segment = self.segmentModel.segment(segment_id)
        if segment is None or segment.text == text:
            return
        self._dirty[segment_id] = text
        self.segmentModel.update_text(segment_id, text, text != segment.original_text)
        self._save_state = "Unsaved"
        self.stateChanged.emit()
        self._autosave.start()

    @Slot(result=bool)
    def saveEdits(self) -> bool:
        if self._transcript is None or not self._dirty:
            self._save_state = "Saved"
            self.stateChanged.emit()
            return True
        self._autosave.stop()
        self._save_state = "Saving…"
        self.stateChanged.emit()
        try:
            for segment_id, text in list(self._dirty.items()):
                self.service.update_segment(self._project_id, self._transcript.transcript_id, segment_id, text)
            self._dirty.clear()
            self._save_state = "Saved"
            self.stateChanged.emit()
            return True
        except Exception as exc:
            self._save_state = "Save failed"
            self.stateChanged.emit()
            self.operationFailed.emit("Your transcript could not be saved. Unsaved edits remain open.")
            self.logger.exception("Transcript autosave failed")
            return False

    @Slot(str, result=bool)
    def resetSegment(self, segment_id: str) -> bool:
        if self._transcript is None:
            return False
        try:
            self._dirty.pop(segment_id, None)
            self.service.reset_segment(self._project_id, self._transcript.transcript_id, segment_id)
            self._reload()
            return True
        except Exception as exc:
            self.operationFailed.emit(self._friendly(exc)); return False

    @Slot(str)
    def setSearch(self, query: str) -> None:
        self.segmentModel.set_search(query)

    @Slot(str)
    def exportTxt(self, value: str) -> None:
        if self._transcript is None:
            return
        try:
            self.saveEdits()
            destination = Path(_local_path(value))
            self.service.export_txt(self._project_id, self._transcript.transcript_id, destination)
            self.operationSucceeded.emit("Transcript exported.")
        except Exception as exc:
            self.operationFailed.emit(self._friendly(exc))

    @Slot()
    def copyFullTranscript(self) -> None:
        if self._transcript is None:
            return
        self.saveEdits()
        text = self.service.combined_text(self._project_id, self._transcript.transcript_id)
        QGuiApplication.clipboard().setText(text)
        self.operationSucceeded.emit("Transcript copied.")

    @Slot(str, int, bool)
    def playSegment(self, media_id: str, start_ms: int, autoplay: bool = True) -> None:
        self.playbackRequested.emit(media_id or self._media_id, max(0, int(start_ms)), autoplay)

    @Slot(result=bool)
    def deleteActiveTranscript(self) -> bool:
        if self._transcript is None:
            return False
        try:
            transcript_id = self._transcript.transcript_id
            self.service.delete(self._project_id, transcript_id)
            self._transcript = None
            self.segmentModel.replace([])
            self.transcriptChanged.emit()
            self.operationSucceeded.emit("Transcript deleted. Source media was not changed.")
            return True
        except Exception as exc:
            self.operationFailed.emit(self._friendly(exc)); return False

    @Slot()
    def unloadModel(self) -> None:
        if self._busy:
            self.operationFailed.emit("Wait for transcription to stop before unloading Whisper.")
            return
        self.worker_pool.submit(self.service.unload)

    def _done(self, future: Future[object]) -> None:
        try:
            self._jobReady.emit(future.result())
        except Exception as exc:
            self._jobFailed.emit(exc)

    @Slot(str, object, int, int, str)
    def _apply_progress(self, state: str, fraction, processed: int, duration: int, message: str) -> None:
        self._state = state
        self._status = message
        self._processed_ms = max(0, int(processed))
        self._duration_ms = max(0, int(duration))
        if fraction is None:
            self._progress_known = False
        else:
            self._progress_known = True
            self._progress = max(0.0, min(1.0, float(fraction)))
        self.stateChanged.emit()

    @Slot(object)
    def _apply_result(self, result) -> None:
        transcript, segments = result
        self._busy = False
        self._state = "completed"
        self._status = "No speech detected." if not segments else "Transcript ready"
        self._progress = 1.0
        self._progress_known = True
        self._transcript = transcript
        self.segmentModel.replace(segments)
        self._dirty.clear()
        self._save_state = "Saved"
        self.stateChanged.emit(); self.transcriptChanged.emit()
        self.operationSucceeded.emit("Transcription completed.")

    @Slot(object)
    def _apply_failure(self, exc) -> None:
        self._busy = False
        if isinstance(exc, STTCancelled):
            self._state = "cancelled"
            self._status = "Transcription cancelled."
        else:
            self._state = "failed"
            self._status = self._friendly(exc)
            self.operationFailed.emit(self._status)
            self.logger.exception("Transcription job failed", exc_info=(type(exc), exc, exc.__traceback__))
        self.stateChanged.emit()

    def _reload(self) -> None:
        if not self._media_id:
            return
        transcript, segments = self.service.get_active(self._project_id, self._media_id)
        self._transcript = transcript
        self.segmentModel.replace(segments)
        self.transcriptChanged.emit()

    @staticmethod
    def _friendly(exc: Exception) -> str:
        if isinstance(exc, STTError):
            return str(exc).strip() or exc.user_message
        return str(exc).strip() or "MMO Video Studio could not complete this transcription action."


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

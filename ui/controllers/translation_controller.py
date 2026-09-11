from __future__ import annotations

import logging
from concurrent.futures import Future
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from domain.language import language_name
from domain.translation import Translation, TranslationSourceType
from engines.translation.errors import TranslationCancelled, TranslationError
from services.translation_service import TranslationService
from ui.models.translation_segment_model import TranslationSegmentListModel
from workers.cancellation import CancellationToken
from workers.worker_pool import WorkerPool


class TranslationController(QObject):
    contextChanged = Signal()
    translationChanged = Signal()
    stateChanged = Signal()
    sourcesChanged = Signal()
    documentsChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    playbackRequested = Signal(str, int, bool)
    _progressReady = Signal(int, int, str)
    _jobReady = Signal(object)
    _jobFailed = Signal(object)

    def __init__(self, service: TranslationService, worker_pool: WorkerPool, logger=None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.worker_pool = worker_pool
        self.logger = logger or logging.getLogger("sp_video_studio.translation_controller")
        self.segmentModel = TranslationSegmentListModel(self)
        self._project_id = ""
        self._translation: Translation | None = None
        self._busy = False
        self._status = "Choose a transcript or script to translate."
        self._progress = 0.0
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

    @Property("QVariantList", notify=sourcesChanged)
    def sources(self) -> list[dict[str, object]]:
        if not self._project_id:
            return []
        try:
            return self.service.source_options(self._project_id)
        except Exception:
            return []

    @Property("QVariantList", notify=documentsChanged)
    def documents(self) -> list[dict[str, object]]:
        if not self._project_id:
            return []
        result: list[dict[str, object]] = []
        try:
            for item in self.service.list_for_project(self._project_id):
                reviewed, total, fraction = self.service.review_progress(self._project_id, item.translation_id)
                result.append({
                    "id": item.translation_id,
                    "sourceType": item.source_type_code,
                    "sourceId": item.source_id,
                    "sourceLanguage": item.source_language,
                    "sourceLanguageName": language_name(item.source_language),
                    "targetLanguage": item.target_language,
                    "targetLanguageName": language_name(item.target_language),
                    "engineId": item.engine_id,
                    "modelId": item.model_id,
                    "status": item.status_code,
                    "statusName": item.status_code.replace("_", " ").title(),
                    "reviewed": reviewed,
                    "total": total,
                    "reviewProgress": fraction,
                    "updatedAt": item.updated_at,
                })
        except Exception:
            return []
        return result

    @Property("QVariantMap", notify=translationChanged)
    def translation(self) -> dict[str, object]:
        if self._translation is None:
            return {}
        reviewed, total, fraction = self.service.review_progress(self._project_id, self._translation.translation_id)
        data = self._translation.to_dict()
        data.update({
            "sourceLanguageName": language_name(self._translation.source_language),
            "targetLanguageName": language_name(self._translation.target_language),
            "statusName": self._translation.status_code.replace("_", " ").title(),
            "reviewedCount": reviewed,
            "segmentCount": total,
            "reviewProgress": fraction,
            "reviewProgressText": f"{reviewed} / {total}",
        })
        return data

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(float, notify=stateChanged)
    def progress(self) -> float:
        return self._progress

    @Property(str, notify=stateChanged)
    def statusMessage(self) -> str:
        return self._status

    @Property(str, notify=stateChanged)
    def saveState(self) -> str:
        return self._save_state

    @Property("QVariantList", constant=True)
    def providers(self) -> list[dict[str, object]]:
        return [dict(item) for item in self.service.providers()]

    @Slot(str)
    def setCurrentProject(self, project_id: str) -> None:
        project_id = (project_id or "").strip()
        if project_id == self._project_id:
            return
        self.saveEdits()
        self.cancel()
        self._project_id = project_id
        self._translation = None
        self.segmentModel.replace([])
        self._status = "Choose a transcript or script to translate."
        self.contextChanged.emit(); self.translationChanged.emit(); self.sourcesChanged.emit(); self.documentsChanged.emit(); self.stateChanged.emit()

    @Slot(str, result=bool)
    def loadTranslation(self, translation_id: str) -> bool:
        if not self._project_id:
            return False
        if self._dirty and not self.saveEdits():
            return False
        try:
            translation, segments = self.service.get(self._project_id, translation_id)
            self._translation = translation
            self.segmentModel.replace(segments)
            self._status = "Review translations before publishing."
            self.translationChanged.emit(); self.stateChanged.emit()
            return True
        except Exception as exc:
            self.operationFailed.emit(self._friendly(exc))
            return False

    @Slot(str, str, str, str, str, str, result=bool)
    def createTranslation(
        self,
        source_type: str,
        source_id: str,
        target_language: str,
        engine_id: str,
        device: str,
        keep_terms_text: str,
    ) -> bool:
        if not self._project_id:
            return False
        keep_terms = tuple(item.strip() for item in keep_terms_text.replace(",", "\n").splitlines() if item.strip())
        try:
            if source_type == TranslationSourceType.TRANSCRIPT.value:
                translation = self.service.create_from_transcript(
                    self._project_id, source_id, target_language, engine_id=engine_id,
                    device=device, keep_terms=keep_terms,
                )
            elif source_type == TranslationSourceType.SCRIPT.value:
                translation = self.service.create_from_script(
                    self._project_id, source_id, target_language, engine_id=engine_id,
                    device=device, keep_terms=keep_terms,
                )
            else:
                raise ValueError("Choose a transcript or script source.")
            self._translation = translation
            self.segmentModel.replace(self.service.repository.segments(translation.translation_id))
            self.documentsChanged.emit(); self.translationChanged.emit()
            if engine_id == self.service.LOCAL_ENGINE_ID:
                self.startTranslation()
            else:
                self._status = "Manual translation ready for review."
                self.stateChanged.emit()
            return True
        except Exception as exc:
            self.operationFailed.emit(self._friendly(exc))
            return False

    @Slot(str, str, str, result=bool)
    def createManual(self, text: str, source_language: str, target_language: str) -> bool:
        try:
            translation = self.service.create_manual(self._project_id, text, source_language, target_language)
            self._translation = translation
            self.segmentModel.replace(self.service.repository.segments(translation.translation_id))
            self.documentsChanged.emit(); self.translationChanged.emit()
            return True
        except Exception as exc:
            self.operationFailed.emit(self._friendly(exc)); return False

    @Slot(result=bool)
    def startTranslation(self) -> bool:
        if self._busy or self._translation is None:
            return False
        if not self.saveEdits():
            return False
        self._busy = True
        self._progress = 0.0
        self._status = "Preparing translation…"
        self._token = CancellationToken()
        self.stateChanged.emit()
        project_id = self._project_id
        translation_id = self._translation.translation_id
        token = self._token

        def progress(done: int, total: int, message: str) -> None:
            self._progressReady.emit(done, total, message)

        future = self.worker_pool.submit(self.service.translate_document, project_id, translation_id, token, progress)
        self._future = future
        future.add_done_callback(self._future_done)
        return True

    def _future_done(self, future: Future[object]) -> None:
        try:
            self._jobReady.emit(future.result())
        except Exception as exc:
            self._jobFailed.emit(exc)

    @Slot()
    def cancel(self) -> None:
        if self._token is not None:
            self._status = "Stopping after current segment…"
            self._token.cancel()
            self.stateChanged.emit()

    @Slot(str, str)
    def queueEdit(self, segment_id: str, text: str) -> None:
        if not segment_id or self._translation is None:
            return
        self._dirty[segment_id] = text
        item = self.segmentModel.segment(segment_id)
        if item is not None:
            item.translated_text = text
            item.edited = text != item.machine_translation
            item.reviewed = False
            self.segmentModel.update_item(item)
        self._save_state = "Unsaved"
        self._autosave.start()
        self.stateChanged.emit()

    @Slot(result=bool)
    def saveEdits(self) -> bool:
        if not self._dirty or self._translation is None:
            return True
        self._autosave.stop()
        self._save_state = "Saving…"
        self.stateChanged.emit()
        try:
            for segment_id, text in list(self._dirty.items()):
                updated = self.service.edit_segment(self._project_id, self._translation.translation_id, segment_id, text)
                self.segmentModel.update_item(updated)
            self._dirty.clear()
            self._save_state = "Saved"
            self.translationChanged.emit(); self.stateChanged.emit()
            return True
        except Exception as exc:
            self._save_state = "Save Failed"
            self.operationFailed.emit("Your translation edits could not be saved. The unsaved text is still open.")
            self.logger.exception("Translation autosave failed", exc_info=exc)
            self.stateChanged.emit()
            return False

    @Slot(str, bool)
    def markReviewed(self, segment_id: str, reviewed: bool) -> None:
        if self._translation is None or not self.saveEdits(): return
        try:
            updated = self.service.mark_reviewed(self._project_id, self._translation.translation_id, segment_id, reviewed)
            self.segmentModel.update_item(updated); self.translationChanged.emit()
        except Exception as exc: self.operationFailed.emit(self._friendly(exc))

    @Slot(str, bool)
    def setLocked(self, segment_id: str, locked: bool) -> None:
        if self._translation is None or not self.saveEdits(): return
        try:
            updated = self.service.set_locked(self._project_id, self._translation.translation_id, segment_id, locked)
            self.segmentModel.update_item(updated); self.translationChanged.emit()
        except Exception as exc: self.operationFailed.emit(self._friendly(exc))

    @Slot(str)
    def resetSegment(self, segment_id: str) -> None:
        if self._translation is None: return
        try:
            updated = self.service.reset_segment(self._project_id, self._translation.translation_id, segment_id)
            self._dirty.pop(segment_id, None); self.segmentModel.update_item(updated); self.translationChanged.emit()
        except Exception as exc: self.operationFailed.emit(self._friendly(exc))

    @Slot(str, bool)
    def retranslateSegment(self, segment_id: str, replace_manual: bool = False) -> None:
        if self._translation is None or self._busy or not self.saveEdits(): return
        self._busy = True; self._status = "Retranslating segment…"; self._token = CancellationToken(); self.stateChanged.emit()
        project_id = self._project_id; translation_id = self._translation.translation_id; token = self._token
        future = self.worker_pool.submit(
            self.service.retranslate_segment, project_id, translation_id, segment_id,
            replace_manual=replace_manual, cancellation=token,
        )
        self._future = future; future.add_done_callback(self._segment_future_done)

    def _segment_future_done(self, future: Future[object]) -> None:
        try:
            updated = future.result(); self._jobReady.emit(self._translation)
            if updated is not None: QTimer.singleShot(0, lambda: self.segmentModel.update_item(updated))
        except Exception as exc: self._jobFailed.emit(exc)

    @Slot()
    def syncSource(self) -> None:
        if self._translation is None or not self.saveEdits(): return
        try:
            self._translation = self.service.sync_source(self._project_id, self._translation.translation_id)
            self.segmentModel.replace(self.service.repository.segments(self._translation.translation_id))
            self.translationChanged.emit(); self.documentsChanged.emit(); self.operationSucceeded.emit("Translation synced with source")
        except Exception as exc: self.operationFailed.emit(self._friendly(exc))

    @Slot(bool)
    def approve(self, force: bool = False) -> None:
        if self._translation is None or not self.saveEdits(): return
        try:
            self._translation = self.service.approve(self._project_id, self._translation.translation_id, force=force)
            self.translationChanged.emit(); self.documentsChanged.emit(); self.operationSucceeded.emit("Translation approved")
        except Exception as exc: self.operationFailed.emit(self._friendly(exc))

    @Slot(str)
    def setSearch(self, query: str) -> None:
        self.segmentModel.set_search(query)

    @Slot(str)
    def setFilter(self, mode: str) -> None:
        self.segmentModel.set_filter(mode)

    @Slot(str, bool, result=bool)
    def exportTxt(self, url_or_path: str, bilingual: bool) -> bool:
        if self._translation is None or not self.saveEdits(): return False
        try:
            path = self._local_path(url_or_path)
            self.service.export_txt(self._project_id, self._translation.translation_id, path, bilingual=bilingual)
            self.operationSucceeded.emit("Translation exported")
            return True
        except Exception as exc:
            self.operationFailed.emit(self._friendly(exc)); return False

    @Slot()
    def copyTranslation(self) -> None:
        if self._translation is None: return
        try:
            QGuiApplication.clipboard().setText(self.service.combined_translation_text(self._project_id, self._translation.translation_id))
            self.operationSucceeded.emit("Translation copied")
        except Exception as exc: self.operationFailed.emit(self._friendly(exc))

    @Slot(str, int, bool)
    def playSource(self, media_id: str, start_ms: int, autoplay: bool = True) -> None:
        if media_id:
            self.playbackRequested.emit(media_id, max(0, start_ms), autoplay)

    @Slot()
    def deleteCurrent(self) -> None:
        if self._translation is None: return
        try:
            self.service.delete(self._project_id, self._translation.translation_id)
            self._translation = None; self.segmentModel.replace([])
            self.translationChanged.emit(); self.documentsChanged.emit(); self.operationSucceeded.emit("Translation deleted")
        except Exception as exc: self.operationFailed.emit(self._friendly(exc))

    @Slot(int, int, str)
    def _apply_progress(self, done: int, total: int, message: str) -> None:  # type: ignore[no-redef]
        self._progress = done / total if total else 0.0
        self._status = message
        self.stateChanged.emit()

    @Slot(object)
    def _apply_result(self, result: object) -> None:
        self._busy = False; self._token = None; self._future = None; self._progress = 1.0
        if isinstance(result, Translation): self._translation = result
        if self._translation is not None:
            self.segmentModel.replace(self.service.repository.segments(self._translation.translation_id))
        self._status = "Translation ready for review."
        self.translationChanged.emit(); self.documentsChanged.emit(); self.stateChanged.emit()

    @Slot(object)
    def _apply_failure(self, error: object) -> None:
        self._busy = False; self._token = None; self._future = None
        if isinstance(error, TranslationCancelled): self._status = "Translation stopped. Completed rows were kept."
        else:
            self._status = "Translation failed."
            self.operationFailed.emit(self._friendly(error if isinstance(error, Exception) else Exception(str(error))))
        if self._translation is not None:
            try: self.segmentModel.replace(self.service.repository.segments(self._translation.translation_id))
            except Exception: pass
        self.translationChanged.emit(); self.documentsChanged.emit(); self.stateChanged.emit()

    @staticmethod
    def _local_path(url_or_path: str) -> Path:
        value = str(url_or_path or "")
        if value.startswith("file:"):
            parsed = urlparse(value); return Path(unquote(parsed.path.lstrip("/") if parsed.netloc else parsed.path))
        return Path(value)

    @staticmethod
    def _friendly(exc: Exception) -> str:
        if isinstance(exc, TranslationError):
            return str(exc) or exc.user_message
        return str(exc) or "Translation could not be completed."

from __future__ import annotations

import logging
from concurrent.futures import Future
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from services.media_service import MediaImportSummary, MediaService, MediaServiceError
from services.platform_service import reveal_in_folder
from ui.models.media_format import format_duration, format_file_size, format_fps, format_resolution
from ui.models.media_list_model import MediaListModel
from workers.cancellation import CancellationToken
from workers.worker_pool import WorkerPool


class MediaController(QObject):
    mediaChanged = Signal()
    currentProjectChanged = Signal()
    filterChanged = Signal()
    importStateChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    mediaAboutToRemove = Signal(str)
    importSummaryReady = Signal(object)
    _progressReady = Signal(int, int, str, str, float)
    _importReady = Signal(object)
    _importFailed = Signal(str)

    def __init__(
        self,
        service: MediaService,
        worker_pool: WorkerPool,
        logger: logging.Logger,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.worker_pool = worker_pool
        self.logger = logger
        self._model = MediaListModel(self)
        self._project_id = ""
        self._search = ""
        self._type_filter = "all"
        self._sort = "recent"
        self._importing = False
        self._import_progress = 0.0
        self._import_status = ""
        self._cancellation: CancellationToken | None = None
        self._progressReady.connect(self._apply_progress)
        self._importReady.connect(self._apply_import_result)
        self._importFailed.connect(self._apply_import_error)

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property(str, notify=currentProjectChanged)
    def currentProjectId(self) -> str:
        return self._project_id

    @Property(int, notify=mediaChanged)
    def visibleCount(self) -> int:
        return self._model.rowCount()

    @Property(str, notify=filterChanged)
    def searchText(self) -> str:
        return self._search

    @Property(str, notify=filterChanged)
    def typeFilter(self) -> str:
        return self._type_filter

    @Property(str, notify=filterChanged)
    def sortMode(self) -> str:
        return self._sort

    @Property(bool, notify=importStateChanged)
    def importing(self) -> bool:
        return self._importing

    @Property(float, notify=importStateChanged)
    def importProgress(self) -> float:
        return self._import_progress

    @Property(str, notify=importStateChanged)
    def importStatus(self) -> str:
        return self._import_status

    @Slot(str)
    def setCurrentProject(self, project_id: str) -> None:
        project_id = (project_id or "").strip()
        if project_id == self._project_id:
            self.refresh()
            return
        self._project_id = project_id
        self.currentProjectChanged.emit()
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        if not self._project_id:
            self._model.replace_assets([])
            self.mediaChanged.emit()
            return
        try:
            self.service.refresh_missing(self._project_id)
            assets = self.service.list_media(
                self._project_id,
                search=self._search,
                media_type=self._type_filter,
                sort=self._sort,
            )
            self._model.replace_assets(assets)
            self.mediaChanged.emit()
        except Exception as exc:
            self.logger.exception("Could not refresh media library")
            self.operationFailed.emit(self._friendly_error(exc))

    @Slot(str)
    def setSearchText(self, value: str) -> None:
        value = value or ""
        if value == self._search:
            return
        self._search = value
        self.filterChanged.emit()
        self.refresh()

    @Slot(str)
    def setTypeFilter(self, value: str) -> None:
        normalized = value if value in {"all", "video", "audio", "image"} else "all"
        if normalized == self._type_filter:
            return
        self._type_filter = normalized
        self.filterChanged.emit()
        self.refresh()

    @Slot(str)
    def setSortMode(self, value: str) -> None:
        normalized = value if value in {"recent", "name", "type", "size"} else "recent"
        if normalized == self._sort:
            return
        self._sort = normalized
        self.filterChanged.emit()
        self.refresh()

    @Slot("QVariantList", result=bool)
    def importUrls(self, values: list[object]) -> bool:
        paths = self._local_paths(values)
        if not paths:
            self.operationFailed.emit("Choose local media files to import.")
            return False
        return self._start_import(paths)

    @Slot("QVariantList", result=bool)
    def importPaths(self, values: list[object]) -> bool:
        paths = [str(value) for value in values if str(value).strip()]
        return self._start_import(paths)

    def _start_import(self, paths: list[str]) -> bool:
        if not self._project_id:
            self.operationFailed.emit("Open a project before importing media.")
            return False
        if self._importing:
            self.operationFailed.emit("A media import is already running.")
            return False
        self._importing = True
        self._import_progress = 0.0
        self._import_status = f"Preparing {len(paths)} file{'s' if len(paths) != 1 else ''}"
        self._cancellation = CancellationToken()
        self.importStateChanged.emit()
        future = self.worker_pool.submit(
            self.service.import_many,
            self._project_id,
            [Path(path) for path in paths],
            cancellation=self._cancellation,
            progress=self._queue_progress,
        )
        future.add_done_callback(self._future_done)
        return True

    @Slot()
    def cancelImport(self) -> None:
        if self._cancellation is not None:
            self._cancellation.cancel()
            self._import_status = "Cancelling import…"
            self.importStateChanged.emit()

    @Slot(str, result=bool)
    def removeMedia(self, asset_id: str) -> bool:
        if not self._project_id:
            return False
        try:
            self.mediaAboutToRemove.emit(asset_id)
            self.service.remove_media(self._project_id, asset_id)
            self.refresh()
            self.operationSucceeded.emit("Media removed. Your original file was not changed.")
            return True
        except Exception as exc:
            self.logger.exception("Media removal failed")
            self.operationFailed.emit(self._friendly_error(exc))
            return False

    @Slot(str, result="QVariantMap")
    def mediaDetails(self, asset_id: str) -> dict[str, object]:
        if not self._project_id:
            return {}
        try:
            asset = self.service.get_media(self._project_id, asset_id)
            return {
                "id": asset.asset_id,
                "name": asset.name,
                "type": asset.type.title(),
                "status": str(asset.status).replace("_", " ").title(),
                "duration": format_duration(asset.duration_ms),
                "resolution": format_resolution(asset.width, asset.height),
                "fps": format_fps(asset.fps),
                "videoCodec": asset.codec or "",
                "audioCodec": asset.audio_codec or "",
                "sampleRate": f"{asset.sample_rate} Hz" if asset.sample_rate else "",
                "channels": str(asset.channels) if asset.channels else "",
                "fileSize": format_file_size(asset.file_size),
                "originalPath": asset.original_path,
                "projectPath": asset.project_path,
                "importedAt": self._display_time(asset.imported_at),
                "thumbnail": QUrl.fromLocalFile(asset.thumbnail_path).toString()
                if asset.thumbnail_path and Path(asset.thumbnail_path).is_file()
                else "",
            }
        except Exception as exc:
            self.operationFailed.emit(self._friendly_error(exc))
            return {}

    @Slot(str)
    def revealMedia(self, asset_id: str) -> None:
        if not self._project_id:
            return
        try:
            asset = self.service.get_media(self._project_id, asset_id)
            reveal_in_folder(asset.project_path)
        except Exception as exc:
            self.logger.exception("Reveal media failed")
            self.operationFailed.emit(self._friendly_error(exc))

    def _queue_progress(self, index: int, total: int, name: str, stage: str, fraction: float) -> None:
        self._progressReady.emit(index, total, name, stage, fraction)

    def _future_done(self, future: Future[object]) -> None:
        try:
            result = future.result()
            if not isinstance(result, MediaImportSummary):
                raise TypeError("Media import returned an unexpected result.")
            self._importReady.emit(result)
        except Exception as exc:
            self.logger.exception("Media import batch failed")
            self._importFailed.emit(self._friendly_error(exc))

    @Slot(int, int, str, str, float)
    def _apply_progress(self, index: int, total: int, name: str, stage: str, fraction: float) -> None:
        overall = ((max(1, index) - 1) + max(0.0, min(1.0, fraction))) / max(1, total)
        self._import_progress = max(0.0, min(1.0, overall))
        self._import_status = f"Importing {index} of {total} · {name} · {stage}"
        self.importStateChanged.emit()

    @Slot(object)
    def _apply_import_result(self, value: object) -> None:
        assert isinstance(value, MediaImportSummary)
        self._importing = False
        self._import_progress = 1.0 if value.imported_count else 0.0
        if value.cancelled:
            self._import_status = "Import cancelled"
        else:
            self._import_status = "Import complete"
        self._cancellation = None
        self.importStateChanged.emit()
        self.refresh()
        payload = {
            "imported": value.imported_count,
            "failed": value.failed_count,
            "cancelled": value.cancelled,
            "failures": [
                {"name": item.name, "path": item.path, "reason": item.reason}
                for item in value.failures
            ],
        }
        self.importSummaryReady.emit(payload)
        if value.cancelled:
            self.operationSucceeded.emit("Import cancelled. Completed files were kept safely.")
        elif value.failed_count and value.imported_count:
            self.operationSucceeded.emit(
                f"{value.imported_count} file{'s' if value.imported_count != 1 else ''} imported; "
                f"{value.failed_count} could not be imported."
            )
        elif value.failed_count:
            self.operationFailed.emit(
                f"{value.failed_count} file{'s' if value.failed_count != 1 else ''} could not be imported."
            )
        else:
            self.operationSucceeded.emit(
                f"{value.imported_count} file{'s' if value.imported_count != 1 else ''} imported."
            )

    @Slot(str)
    def _apply_import_error(self, message: str) -> None:
        self._importing = False
        self._import_progress = 0.0
        self._import_status = "Import failed"
        self._cancellation = None
        self.importStateChanged.emit()
        self.operationFailed.emit(message or "Media import failed.")

    @staticmethod
    def _local_paths(values: Iterable[object]) -> list[str]:
        paths: list[str] = []
        for value in values:
            if hasattr(value, "isLocalFile") and hasattr(value, "toLocalFile"):
                try:
                    if value.isLocalFile():
                        local = value.toLocalFile()
                        if local:
                            paths.append(str(local))
                    continue
                except Exception:
                    pass
            text = str(value)
            if text.startswith("file:"):
                parsed = urlparse(text)
                local = unquote(parsed.path)
                if parsed.netloc:
                    local = f"//{parsed.netloc}{local}"
                if len(local) >= 3 and local[0] == "/" and local[2] == ":":
                    local = local[1:]
                if local:
                    paths.append(local)
            elif "://" not in text and text.strip():
                paths.append(text)
        return paths

    @staticmethod
    def _display_time(value: str) -> str:
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%b %d, %Y · %H:%M")
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        if isinstance(exc, MediaServiceError):
            return str(exc).strip() or exc.user_message
        return str(exc).strip() or "SP Video Studio could not complete this media action."

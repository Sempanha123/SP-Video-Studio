from __future__ import annotations

import logging
from concurrent.futures import Future
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from app.paths import AppPaths
from domain.settings import AppSettings
from media.ffmpeg_locator import FFmpegLocator
from services.accessibility_service import AccessibilityService
from services.project_service import ProjectService
from services.settings_service import SettingsService
from workers.worker_pool import WorkerPool


class SettingsController(QObject):
    settingsChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    readinessRelevantChanged = Signal()
    mediaToolValidationChanged = Signal()
    _mediaToolValidationReady = Signal(object)
    _mediaToolValidationFailed = Signal(str)

    def __init__(
        self,
        service: SettingsService,
        paths: AppPaths,
        project_service: ProjectService,
        ffmpeg_locator: FFmpegLocator,
        worker_pool: WorkerPool,
        logger: logging.Logger,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.paths = paths
        self.project_service = project_service
        self.ffmpeg_locator = ffmpeg_locator
        self.worker_pool = worker_pool
        self.logger = logger
        self.accessibility = AccessibilityService(service)
        self._validating_media_tool = False
        self._mediaToolValidationReady.connect(self._apply_media_tool_validation)
        self._mediaToolValidationFailed.connect(self._apply_media_tool_validation_error)

    @property
    def current(self) -> AppSettings:
        return self.service.current

    @Property(str, notify=settingsChanged)
    def theme(self) -> str:
        return self.current.theme

    @Property(str, notify=settingsChanged)
    def language(self) -> str:
        return self.current.language

    @Property(bool, notify=settingsChanged)
    def openLastProject(self) -> bool:
        return self.current.open_last_project

    @Property(bool, notify=settingsChanged)
    def showWelcomeHome(self) -> bool:
        return self.current.show_welcome_home

    @Property(str, notify=settingsChanged)
    def projectFolder(self) -> str:
        return self.current.default_projects_folder

    @Property(str, notify=settingsChanged)
    def performanceProfile(self) -> str:
        return self.current.performance_profile

    @Property(int, notify=settingsChanged)
    def defaultFps(self) -> int:
        return self.current.default_fps

    @Property(str, notify=settingsChanged)
    def defaultAspectRatio(self) -> str:
        return self.current.default_aspect_ratio

    @Property(str, notify=settingsChanged)
    def preferredEncoder(self) -> str:
        return self.current.preferred_encoder

    @Property(str, notify=settingsChanged)
    def ffmpegMode(self) -> str:
        return self.current.ffmpeg_mode

    @Property(str, notify=settingsChanged)
    def ffmpegPath(self) -> str:
        return self.current.ffmpeg_path

    @Property(str, notify=settingsChanged)
    def ffprobePath(self) -> str:
        return self.current.ffprobe_path

    @Property(bool, notify=settingsChanged)
    def debugLogging(self) -> bool:
        return self.current.debug_logging

    @Property(bool, notify=settingsChanged)
    def showTechnicalDetails(self) -> bool:
        return self.current.show_technical_error_details

    @Property(bool, notify=settingsChanged)
    def readinessOnStartup(self) -> bool:
        return self.current.readiness_check_on_startup

    @Property(str, notify=settingsChanged)
    def reduceMotionMode(self) -> str:
        return self.accessibility.current().reduce_motion_mode

    @Property(bool, notify=settingsChanged)
    def reduceMotionEffective(self) -> bool:
        return self.accessibility.current().reduce_motion_effective

    @Property(str, notify=settingsChanged)
    def interfaceTextSize(self) -> str:
        return self.accessibility.current().interface_text_size

    @Property(float, notify=settingsChanged)
    def interfaceTextScale(self) -> float:
        return self.accessibility.current().text_scale

    @Property(bool, notify=settingsChanged)
    def strongerFocusIndicator(self) -> bool:
        return self.accessibility.current().stronger_focus_indicator

    @Property(bool, notify=mediaToolValidationChanged)
    def mediaToolValidating(self) -> bool:
        return self._validating_media_tool

    @Property("QVariantMap", notify=settingsChanged)
    def storagePaths(self) -> dict[str, str]:
        return {
            "Application Data": str(self.paths.root),
            "Projects": self.current.default_projects_folder,
            "Cache": str(self.paths.cache),
            "Models": str(self.paths.models),
            "Temporary": str(self.paths.temp),
            "Logs": str(self.paths.logs),
            "Exports": str(self.paths.exports),
        }

    @Slot(str)
    def setTheme(self, value: str) -> None:
        self._update(theme=value)

    @Slot(str)
    def setLanguage(self, value: str) -> None:
        self._update(language=value)

    @Slot(bool)
    def setOpenLastProject(self, value: bool) -> None:
        self._update(open_last_project=value)

    @Slot(bool)
    def setShowWelcomeHome(self, value: bool) -> None:
        self._update(show_welcome_home=value)

    @Slot(str)
    def setPerformanceProfile(self, value: str) -> None:
        self._update(performance_profile=value)

    @Slot(int)
    def setDefaultFps(self, value: int) -> None:
        self._update(default_fps=value)

    @Slot(str)
    def setDefaultAspectRatio(self, value: str) -> None:
        self._update(default_aspect_ratio=value)

    @Slot(bool)
    def setDebugLogging(self, value: bool) -> None:
        self._update(debug_logging=value)

    @Slot(bool)
    def setShowTechnicalDetails(self, value: bool) -> None:
        self._update(show_technical_error_details=value)

    @Slot(bool)
    def setReadinessOnStartup(self, value: bool) -> None:
        self._update(readiness_check_on_startup=value)

    @Slot(str)
    def setReduceMotion(self, value: str) -> None:
        try:
            self.accessibility.set_reduce_motion(value)
            self.settingsChanged.emit()
        except Exception as exc:
            self.logger.exception("Reduce Motion update failed")
            self.operationFailed.emit(str(exc) or "Reduce Motion could not be updated.")

    @Slot(str)
    def setInterfaceTextSize(self, value: str) -> None:
        try:
            self.accessibility.set_interface_text_size(value)
            self.settingsChanged.emit()
        except Exception as exc:
            self.logger.exception("Interface text size update failed")
            self.operationFailed.emit(str(exc) or "Interface text size could not be updated.")

    @Slot(bool)
    def setStrongerFocusIndicator(self, value: bool) -> None:
        try:
            self.accessibility.set_stronger_focus_indicator(value)
            self.settingsChanged.emit()
        except Exception as exc:
            self.logger.exception("Focus indicator preference update failed")
            self.operationFailed.emit(str(exc) or "Focus indicator preference could not be updated.")

    @Slot(str, result=bool)
    def setProjectFolder(self, value: str) -> bool:
        try:
            path = self._local_path(value)
            settings = self.service.set_project_folder(path)
            self.project_service.set_project_root(Path(settings.default_projects_folder))
            self.settingsChanged.emit()
            self.readinessRelevantChanged.emit()
            self.operationSucceeded.emit("Default projects folder updated.")
            return True
        except Exception as exc:
            self.logger.exception("Could not update project folder")
            self.operationFailed.emit(str(exc) or "The selected projects folder could not be used.")
            return False

    @Slot()
    def resetProjectFolder(self) -> None:
        self.setProjectFolder(str(self.paths.default_projects_root))

    @Slot(str, result=bool)
    def setCustomFFmpeg(self, value: str) -> bool:
        if self._validating_media_tool:
            return False
        path = self._local_path(value)
        candidate = Path(path).expanduser()
        if not candidate.is_file():
            self.operationFailed.emit("The selected FFmpeg executable was not found.")
            return False
        self._validating_media_tool = True
        self.mediaToolValidationChanged.emit()
        future = self.worker_pool.submit(self._validate_media_tool, str(candidate))
        future.add_done_callback(self._media_tool_future_done)
        return True

    def _validate_media_tool(self, path: str) -> tuple[str, str]:
        info = self.ffmpeg_locator.validate_path(path, "ffmpeg")
        if not info.available or not info.path:
            raise ValueError(info.error or "The selected FFmpeg executable is invalid.")
        ffmpeg, ffprobe = self.ffmpeg_locator.discover(info.path, None)
        if not ffmpeg.available or not ffmpeg.path:
            raise ValueError(ffmpeg.error or "The selected FFmpeg executable is invalid.")
        return ffmpeg.path, ffprobe.path if ffprobe.available and ffprobe.path else ""

    def _media_tool_future_done(self, future: Future[object]) -> None:
        try:
            result = future.result()
            self._mediaToolValidationReady.emit(result)
        except Exception as exc:
            self._mediaToolValidationFailed.emit(str(exc))

    @Slot(object)
    def _apply_media_tool_validation(self, result: object) -> None:
        try:
            ffmpeg_path, ffprobe_path = result
            self.service.update(
                ffmpeg_mode="custom",
                ffmpeg_path=str(ffmpeg_path),
                ffprobe_path=str(ffprobe_path),
            )
            self.settingsChanged.emit()
            self.readinessRelevantChanged.emit()
            self.operationSucceeded.emit("FFmpeg path saved.")
        except Exception as exc:
            self.logger.exception("Could not save validated FFmpeg path")
            self.operationFailed.emit(str(exc) or "FFmpeg settings could not be saved.")
        finally:
            self._validating_media_tool = False
            self.mediaToolValidationChanged.emit()

    @Slot(str)
    def _apply_media_tool_validation_error(self, message: str) -> None:
        self._validating_media_tool = False
        self.mediaToolValidationChanged.emit()
        self.operationFailed.emit(message or "The selected FFmpeg executable is invalid.")

    @Slot()
    def useAutoDetectedFFmpeg(self) -> None:
        self._update(ffmpeg_mode="auto", ffmpeg_path="", ffprobe_path="")
        self.readinessRelevantChanged.emit()

    @Slot()
    def resetSettings(self) -> None:
        try:
            settings = self.service.reset_defaults()
            self.project_service.set_project_root(Path(settings.default_projects_folder))
            self.settingsChanged.emit()
            self.readinessRelevantChanged.emit()
            self.operationSucceeded.emit("Application settings were reset to defaults.")
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "Settings could not be reset.")

    @Slot(str)
    def openStorageFolder(self, name: str) -> None:
        path_value = self.storagePaths.get(name)
        if not path_value:
            self.operationFailed.emit("That storage location is unavailable.")
            return
        try:
            path = Path(path_value).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except OSError:
            self.logger.exception("Could not open storage folder: %s", path_value)
            self.operationFailed.emit("The folder could not be opened.")

    def _update(self, **changes: object) -> None:
        try:
            self.service.update(**changes)
            self.settingsChanged.emit()
        except Exception as exc:
            self.logger.exception("Settings update failed")
            self.operationFailed.emit(str(exc) or "This setting could not be saved.")

    @staticmethod
    def _local_path(value: str) -> str:
        if value.startswith("file:"):
            return QUrl(value).toLocalFile()
        return value

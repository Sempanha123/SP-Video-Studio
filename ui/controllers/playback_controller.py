from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from domain.media import MediaStatus
from domain.playback import PlaybackSelection, PlaybackState, SEEK_STEP_MS
from services.media_service import MediaService, MediaServiceError
from services.playback_service import PlaybackService
from services.platform_service import reveal_in_folder
from ui.models.media_format import format_duration, format_fps, format_resolution


class PlaybackController(QObject):
    selectedMediaChanged = Signal()
    playbackChanged = Signal()
    volumeChanged = Signal()
    errorChanged = Signal()
    currentProjectChanged = Signal()
    playRequested = Signal()
    pauseRequested = Signal()
    stopRequested = Signal()
    seekRequested = Signal(int)
    releaseRequested = Signal()
    operationFailed = Signal(str)

    def __init__(
        self,
        media_service: MediaService,
        playback_service: PlaybackService,
        logger: logging.Logger,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.media_service = media_service
        self.playback = playback_service
        self.logger = logger
        self._project_id = ""
        self._selected: dict[str, object] = {}
        self._source_url = ""

    @Property(str, notify=currentProjectChanged)
    def currentProjectId(self) -> str:
        return self._project_id

    @Property("QVariantMap", notify=selectedMediaChanged)
    def selectedMedia(self) -> dict[str, object]:
        return self._selected

    @Property(str, notify=selectedMediaChanged)
    def selectedMediaId(self) -> str:
        return str(self._selected.get("id", ""))

    @Property(str, notify=selectedMediaChanged)
    def selectedType(self) -> str:
        return str(self._selected.get("type", ""))

    @Property(str, notify=selectedMediaChanged)
    def sourceUrl(self) -> str:
        return self._source_url

    @Property(str, notify=playbackChanged)
    def state(self) -> str:
        return self.playback.state.value

    @Property(int, notify=playbackChanged)
    def position(self) -> int:
        return self.playback.snapshot.position_ms

    @Property(int, notify=playbackChanged)
    def duration(self) -> int:
        return self.playback.snapshot.duration_ms

    @Property(str, notify=playbackChanged)
    def positionText(self) -> str:
        return format_duration(self.playback.snapshot.position_ms)

    @Property(str, notify=playbackChanged)
    def durationText(self) -> str:
        return format_duration(self.playback.snapshot.duration_ms)

    @Property(int, notify=volumeChanged)
    def volume(self) -> int:
        return self.playback.snapshot.volume

    @Property(bool, notify=volumeChanged)
    def muted(self) -> bool:
        return self.playback.snapshot.muted

    @Property(str, notify=errorChanged)
    def errorMessage(self) -> str:
        return self.playback.snapshot.error_message

    @Property(bool, notify=selectedMediaChanged)
    def videoAvailable(self) -> bool:
        return self.selectedType == "video"

    @Property(bool, notify=selectedMediaChanged)
    def audioAvailable(self) -> bool:
        return self.selectedType == "audio"

    @Property(bool, notify=selectedMediaChanged)
    def imageAvailable(self) -> bool:
        return self.selectedType == "image"

    @Property(bool, notify=playbackChanged)
    def seekEnabled(self) -> bool:
        return self.selectedType in {"video", "audio"} and self.duration > 0

    @Property(int, constant=True)
    def keyboardSeekInterval(self) -> int:
        return SEEK_STEP_MS

    @Slot(str)
    def setCurrentProject(self, project_id: str) -> None:
        project_id = (project_id or "").strip()
        if project_id == self._project_id:
            return
        self.clear()
        self._project_id = project_id
        self.currentProjectChanged.emit()

    @Slot(str, result=bool)
    def setMedia(self, media_id: str) -> bool:
        media_id = (media_id or "").strip()
        if not media_id or not self._project_id:
            self.clear()
            return False
        try:
            asset = self.media_service.get_media(self._project_id, media_id)
            managed_path = Path(asset.project_path)
            if str(asset.status) == MediaStatus.MISSING.value or not managed_path.is_file():
                self.clear()
                self.operationFailed.emit("File Missing")
                return False
            if str(asset.status) != MediaStatus.READY.value:
                self.clear()
                self.operationFailed.emit("This media is not ready to preview.")
                return False

            self.releaseRequested.emit()
            selection = PlaybackSelection(
                media_id=asset.asset_id,
                project_id=asset.project_id,
                media_type=asset.type,
                name=asset.name,
                path=str(managed_path),
                duration_ms=int(asset.duration_ms or 0),
                width=asset.width,
                height=asset.height,
                fps=asset.fps,
                sample_rate=asset.sample_rate,
                channels=asset.channels,
            )
            self.playback.select(selection)
            self._source_url = self.local_path_to_url(managed_path)
            self._selected = {
                "id": asset.asset_id,
                "name": asset.name,
                "type": asset.type,
                "sourceUrl": self._source_url,
                "projectPath": asset.project_path,
                "duration": format_duration(asset.duration_ms),
                "durationMs": int(asset.duration_ms or 0),
                "resolution": format_resolution(asset.width, asset.height),
                "fps": format_fps(asset.fps),
                "sampleRate": f"{asset.sample_rate / 1000:g} kHz" if asset.sample_rate else "",
                "channels": self._channels_text(asset.channels),
                "status": str(asset.status),
            }
            self.selectedMediaChanged.emit()
            self.errorChanged.emit()
            self.playbackChanged.emit()
            return True
        except Exception as exc:
            self.logger.exception("Could not select media for preview")
            self.clear()
            self.operationFailed.emit(self._friendly_error(exc))
            return False


    @Slot(str, str, int, result=bool)
    def setExternalAudio(self, path: str, name: str = "Generated narration", duration_ms: int = 0) -> bool:
        candidate = Path(path)
        if not candidate.is_file():
            self.operationFailed.emit("Generated audio could not be found.")
            return False
        self.releaseRequested.emit()
        selection = PlaybackSelection(
            media_id=f"generated:{candidate.name}", project_id=self._project_id, media_type="audio",
            name=name or candidate.name, path=str(candidate), duration_ms=max(0, int(duration_ms)),
        )
        self.playback.select(selection)
        self._source_url = self.local_path_to_url(candidate)
        self._selected = {"id": selection.media_id, "name": selection.name, "type": "audio", "sourceUrl": self._source_url, "projectPath": str(candidate), "duration": format_duration(duration_ms), "durationMs": duration_ms, "resolution": "", "fps": "", "sampleRate": "", "channels": "", "status": "ready"}
        self.selectedMediaChanged.emit(); self.errorChanged.emit(); self.playbackChanged.emit()
        return True

    @Slot(str)
    def externalAudioRemoving(self, path: str) -> None:
        selected_path = str(self._selected.get("projectPath", "")) if self._selected else ""
        if selected_path and Path(selected_path).resolve() == Path(path).resolve():
            self.clear()

    @Slot()
    def play(self) -> None:
        allowed, restart = self.playback.request_play()
        if not allowed:
            return
        if restart:
            self.seekRequested.emit(0)
        self.playRequested.emit()

    @Slot()
    def pause(self) -> None:
        if self.playback.request_pause():
            self.pauseRequested.emit()

    @Slot()
    def togglePlayback(self) -> None:
        if self.playback.state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()

    @Slot(int)
    def seek(self, position_ms: int) -> None:
        if not self.seekEnabled:
            return
        position = self.playback.seek(position_ms)
        self.seekRequested.emit(position)
        self.playbackChanged.emit()

    @Slot(int)
    def seekRelative(self, delta_ms: int) -> None:
        if not self.seekEnabled:
            return
        position = self.playback.seek_relative(delta_ms)
        self.seekRequested.emit(position)
        self.playbackChanged.emit()

    @Slot(int, bool)
    def keyboardSeek(self, direction: int, large: bool = False) -> None:
        if not self.seekEnabled:
            return
        position = self.playback.keyboard_seek(direction, large=large)
        self.seekRequested.emit(position)
        self.playbackChanged.emit()

    @Slot(int)
    def setVolume(self, value: int) -> None:
        self.playback.set_volume(value)
        self.volumeChanged.emit()

    @Slot()
    def toggleMute(self) -> None:
        self.playback.toggle_mute()
        self.volumeChanged.emit()

    @Slot()
    def clear(self) -> None:
        had_selection = bool(self._selected) or self.playback.selection is not None
        self.releaseRequested.emit()
        self.playback.clear()
        self._selected = {}
        self._source_url = ""
        if had_selection:
            self.selectedMediaChanged.emit()
        self.playbackChanged.emit()
        self.errorChanged.emit()

    @Slot(str)
    def mediaRemoving(self, media_id: str) -> None:
        if media_id and media_id == self.selectedMediaId:
            self.clear()

    @Slot(int)
    def backendPositionChanged(self, position_ms: int) -> None:
        if self.playback.selection is None:
            return
        self.playback.set_position(position_ms)
        self.playbackChanged.emit()

    @Slot(int)
    def backendDurationChanged(self, duration_ms: int) -> None:
        if self.playback.selection is None:
            return
        self.playback.set_duration(duration_ms)
        self.playbackChanged.emit()

    @Slot(str)
    def backendPlaybackStateChanged(self, state: str) -> None:
        if self.playback.selection is None:
            return
        if state == "playing":
            self.playback.mark_playing()
        elif state == "paused":
            self.playback.mark_paused()
        elif state == "stopped" and self.playback.state != PlaybackState.ENDED:
            self.playback.mark_stopped()
        self.playbackChanged.emit()

    @Slot(str)
    def backendMediaStatusChanged(self, status: str) -> None:
        if self.playback.selection is None:
            return
        if status == "loading":
            self.playback.snapshot.state = PlaybackState.LOADING
        elif status == "ready":
            if self.playback.state in {PlaybackState.LOADING, PlaybackState.STOPPED}:
                self.playback.mark_ready()
        self.playbackChanged.emit()

    @Slot()
    def backendEndOfMedia(self) -> None:
        self.playback.mark_ended()
        self.playbackChanged.emit()

    @Slot(str)
    def backendError(self, message: str) -> None:
        self.logger.warning("Native preview error for %s: %s", self.selectedMediaId, message)
        self.playback.mark_error(message)
        self.errorChanged.emit()
        self.playbackChanged.emit()

    @Slot()
    def revealSelected(self) -> None:
        path = str(self._selected.get("projectPath", ""))
        if not path:
            return
        try:
            reveal_in_folder(path)
        except Exception as exc:
            self.logger.exception("Could not reveal selected preview media")
            self.operationFailed.emit(self._friendly_error(exc))

    @staticmethod
    def local_path_to_url(path: str | Path) -> str:
        return QUrl.fromLocalFile(str(Path(path))).toString()

    @staticmethod
    def _channels_text(channels: int | None) -> str:
        if channels == 1:
            return "Mono"
        if channels == 2:
            return "Stereo"
        if channels:
            return f"{channels} channels"
        return ""

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        if isinstance(exc, MediaServiceError):
            return str(exc).strip() or exc.user_message
        return str(exc).strip() or "This media could not be previewed."

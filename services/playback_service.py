from __future__ import annotations

from dataclasses import dataclass

from domain.playback import (
    LARGE_SEEK_STEP_MS,
    PLAYABLE_MEDIA_TYPES,
    SEEK_STEP_MS,
    PlaybackSelection,
    PlaybackState,
)


class PlaybackError(RuntimeError):
    pass


@dataclass(slots=True)
class PlaybackSnapshot:
    state: PlaybackState = PlaybackState.IDLE
    position_ms: int = 0
    duration_ms: int = 0
    volume: int = 100
    muted: bool = False
    previous_volume: int = 100
    error_message: str = ""


class PlaybackService:
    """Backend-agnostic playback state and control policy.

    Native decoding remains in Qt Multimedia. This service owns predictable state,
    clamping, mute/volume behavior, selection lifecycle, and keyboard seek policy.
    """

    def __init__(self) -> None:
        self.selection: PlaybackSelection | None = None
        self.snapshot = PlaybackSnapshot()

    @property
    def state(self) -> PlaybackState:
        return self.snapshot.state

    def select(self, selection: PlaybackSelection) -> None:
        self.selection = selection
        self.snapshot.position_ms = 0
        self.snapshot.duration_ms = max(0, int(selection.duration_ms or 0))
        self.snapshot.error_message = ""
        self.snapshot.state = (
            PlaybackState.LOADING
            if selection.media_type in PLAYABLE_MEDIA_TYPES
            else PlaybackState.READY
        )

    def clear(self) -> None:
        self.selection = None
        self.snapshot.state = PlaybackState.IDLE
        self.snapshot.position_ms = 0
        self.snapshot.duration_ms = 0
        self.snapshot.error_message = ""

    def mark_ready(self) -> None:
        if self.selection is None:
            self.snapshot.state = PlaybackState.IDLE
            return
        if self.snapshot.state != PlaybackState.ERROR:
            self.snapshot.state = PlaybackState.READY

    def mark_playing(self) -> None:
        if self.selection is not None and self.selection.playable:
            self.snapshot.state = PlaybackState.PLAYING
            self.snapshot.error_message = ""

    def mark_paused(self) -> None:
        if self.selection is not None and self.selection.playable:
            self.snapshot.state = PlaybackState.PAUSED

    def mark_stopped(self) -> None:
        if self.selection is not None and self.selection.playable:
            self.snapshot.state = PlaybackState.STOPPED

    def mark_ended(self) -> None:
        if self.selection is None or not self.selection.playable:
            return
        self.snapshot.position_ms = self.snapshot.duration_ms
        self.snapshot.state = PlaybackState.ENDED

    def mark_error(self, message: str) -> None:
        if self.selection is None:
            return
        self.snapshot.state = PlaybackState.ERROR
        self.snapshot.error_message = (
            (message or "").strip()
            or "This media could not be previewed."
        )

    def request_play(self) -> tuple[bool, bool]:
        """Return (allowed, restart_from_zero)."""
        if self.selection is None or not self.selection.playable:
            return False, False
        if self.snapshot.state == PlaybackState.ERROR:
            return False, False
        restart = self.snapshot.state == PlaybackState.ENDED
        if restart:
            self.snapshot.position_ms = 0
        return True, restart

    def request_pause(self) -> bool:
        return self.selection is not None and self.snapshot.state == PlaybackState.PLAYING

    def set_position(self, position_ms: int) -> int:
        maximum = max(0, int(self.snapshot.duration_ms))
        value = max(0, int(position_ms))
        if maximum > 0:
            value = min(value, maximum)
        self.snapshot.position_ms = value
        return value

    def set_duration(self, duration_ms: int) -> int:
        self.snapshot.duration_ms = max(0, int(duration_ms))
        self.snapshot.position_ms = self.clamp_seek(self.snapshot.position_ms)
        return self.snapshot.duration_ms

    def clamp_seek(self, position_ms: int) -> int:
        maximum = max(0, int(self.snapshot.duration_ms))
        value = max(0, int(position_ms))
        return min(value, maximum) if maximum > 0 else 0

    def seek(self, position_ms: int) -> int:
        if self.selection is None or not self.selection.playable:
            return 0
        return self.set_position(self.clamp_seek(position_ms))

    def seek_relative(self, delta_ms: int) -> int:
        return self.seek(self.snapshot.position_ms + int(delta_ms))

    def keyboard_seek(self, direction: int, *, large: bool = False) -> int:
        step = LARGE_SEEK_STEP_MS if large else SEEK_STEP_MS
        return self.seek_relative(step * (1 if direction >= 0 else -1))

    def set_volume(self, value: int | float) -> int:
        normalized = max(0, min(100, int(round(float(value)))))
        self.snapshot.volume = normalized
        if normalized > 0 and not self.snapshot.muted:
            self.snapshot.previous_volume = normalized
        return normalized

    def toggle_mute(self) -> bool:
        if self.snapshot.muted:
            self.snapshot.muted = False
            if self.snapshot.volume <= 0:
                self.snapshot.volume = max(1, self.snapshot.previous_volume)
        else:
            if self.snapshot.volume > 0:
                self.snapshot.previous_volume = self.snapshot.volume
            self.snapshot.muted = True
        return self.snapshot.muted

    def set_muted(self, muted: bool) -> bool:
        if bool(muted) != self.snapshot.muted:
            self.toggle_mute()
        return self.snapshot.muted

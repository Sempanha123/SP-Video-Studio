from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass

from domain.accessibility_settings import (
    AccessibilitySettings,
    InterfaceTextSize,
    ReduceMotionMode,
)


@dataclass(frozen=True, slots=True)
class AccessibilityState:
    reduce_motion_mode: str
    reduce_motion_effective: bool
    interface_text_size: str
    text_scale: float
    stronger_focus_indicator: bool


class AccessibilityService:
    """Small adapter around existing SettingsService; no second preference store."""

    SPI_GETCLIENTAREAANIMATION = 0x1042

    def __init__(self, settings_service) -> None:
        self.settings = settings_service

    def current(self) -> AccessibilityState:
        raw = self.settings.current
        prefs = AccessibilitySettings(
            reduce_motion=getattr(raw, "reduce_motion", ReduceMotionMode.SYSTEM.value),
            interface_text_size=getattr(
                raw, "interface_text_size", InterfaceTextSize.DEFAULT.value
            ),
            stronger_focus_indicator=bool(
                getattr(raw, "stronger_focus_indicator", False)
            ),
        )
        prefs.validate()
        return AccessibilityState(
            reduce_motion_mode=prefs.reduce_motion,
            reduce_motion_effective=self._resolve_reduce_motion(prefs.reduce_motion),
            interface_text_size=prefs.interface_text_size,
            text_scale=prefs.text_scale,
            stronger_focus_indicator=prefs.stronger_focus_indicator,
        )

    def set_reduce_motion(self, value: str):
        AccessibilitySettings(reduce_motion=value).validate()
        return self.settings.update(reduce_motion=value)

    def set_interface_text_size(self, value: str):
        AccessibilitySettings(interface_text_size=value).validate()
        return self.settings.update(interface_text_size=value)

    def set_stronger_focus_indicator(self, value: bool):
        return self.settings.update(stronger_focus_indicator=bool(value))

    def _resolve_reduce_motion(self, mode: str) -> bool:
        if mode == ReduceMotionMode.ON.value:
            return True
        if mode == ReduceMotionMode.OFF.value:
            return False
        detected = self.system_prefers_reduced_motion()
        return False if detected is None else detected

    @classmethod
    def system_prefers_reduced_motion(cls) -> bool | None:
        """Best-effort Windows animation preference. None means unavailable."""
        if not sys.platform.startswith("win"):
            return None
        try:
            enabled = ctypes.c_int(1)
            ok = ctypes.windll.user32.SystemParametersInfoW(
                cls.SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(enabled), 0
            )
            if not ok:
                return None
            return not bool(enabled.value)
        except Exception:
            return None

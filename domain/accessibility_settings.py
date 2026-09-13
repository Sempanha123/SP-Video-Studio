from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReduceMotionMode(StrEnum):
    SYSTEM = "system"
    ON = "on"
    OFF = "off"


class InterfaceTextSize(StrEnum):
    DEFAULT = "default"
    LARGE = "large"


SUPPORTED_REDUCE_MOTION_MODES = {item.value for item in ReduceMotionMode}
SUPPORTED_INTERFACE_TEXT_SIZES = {item.value for item in InterfaceTextSize}
TEXT_SCALE_BY_SIZE = {
    InterfaceTextSize.DEFAULT.value: 1.0,
    InterfaceTextSize.LARGE.value: 1.12,
}


@dataclass(frozen=True, slots=True)
class AccessibilitySettings:
    reduce_motion: str = ReduceMotionMode.SYSTEM.value
    interface_text_size: str = InterfaceTextSize.DEFAULT.value
    stronger_focus_indicator: bool = False

    def validate(self) -> None:
        if self.reduce_motion not in SUPPORTED_REDUCE_MOTION_MODES:
            raise ValueError("Unsupported Reduce Motion preference.")
        if self.interface_text_size not in SUPPORTED_INTERFACE_TEXT_SIZES:
            raise ValueError("Unsupported interface text size.")

    @property
    def text_scale(self) -> float:
        return TEXT_SCALE_BY_SIZE[self.interface_text_size]

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SceneTransitionType(StrEnum):
    CUT = "cut"
    FADE = "fade"
    CROSSFADE = "crossfade"
    SLIDE = "slide"


@dataclass(slots=True)
class SceneTransition:
    transition_type: str | SceneTransitionType = SceneTransitionType.CUT
    duration_ms: int = 0
    direction: str = ""

    @property
    def type_code(self) -> str:
        return self.transition_type.value if isinstance(self.transition_type, StrEnum) else str(self.transition_type)

    def validate(self) -> None:
        if self.type_code not in {item.value for item in SceneTransitionType}:
            raise ValueError("Unsupported scene transition.")
        if self.duration_ms < 0:
            raise ValueError("Transition duration cannot be negative.")
        if self.type_code == SceneTransitionType.CUT.value and self.duration_ms != 0:
            self.duration_ms = 0

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type_code, "durationMs": int(self.duration_ms), "direction": self.direction}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneTransition":
        data = data or {}
        item = cls(str(data.get("type", "cut")), int(data.get("durationMs", 0) or 0), str(data.get("direction", "") or ""))
        item.validate()
        return item

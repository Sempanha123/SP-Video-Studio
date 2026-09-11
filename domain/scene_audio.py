from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SceneAudioSettings:
    source_audio_enabled: bool = False
    source_audio_volume: float = 1.0
    narration_enabled: bool = True
    narration_volume: float = 1.0

    def validate(self) -> None:
        self.source_audio_volume = max(0.0, min(1.0, float(self.source_audio_volume)))
        self.narration_volume = max(0.0, min(1.0, float(self.narration_volume)))

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "sourceAudioEnabled": bool(self.source_audio_enabled),
            "sourceAudioVolume": self.source_audio_volume,
            "narrationEnabled": bool(self.narration_enabled),
            "narrationVolume": self.narration_volume,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SceneAudioSettings":
        data = data or {}
        item = cls(
            bool(data.get("sourceAudioEnabled", False)),
            float(data.get("sourceAudioVolume", 1.0) or 0),
            bool(data.get("narrationEnabled", True)),
            float(data.get("narrationVolume", 1.0) or 0),
        )
        item.validate()
        return item

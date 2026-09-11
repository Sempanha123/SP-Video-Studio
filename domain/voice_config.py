from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class VoiceMode(StrEnum):
    DEFAULT = "default"
    DESIGNED = "designed"
    REFERENCE = "reference"
    CONTINUATION = "continuation"


class TTSDevice(StrEnum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


@dataclass(slots=True)
class VoiceConfig:
    mode: str | VoiceMode = VoiceMode.DEFAULT
    description: str = ""
    reference_audio_path: str = ""
    prompt_audio_path: str = ""
    prompt_text: str = ""
    consent_confirmed: bool = False
    cfg_value: float = 2.0
    inference_timesteps: int = 10
    seed: int | None = None
    normalize_text: bool = False
    device: str | TTSDevice = TTSDevice.AUTO
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def mode_code(self) -> str:
        return str(self.mode)

    @property
    def device_code(self) -> str:
        return str(self.device)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode_code,
            "description": self.description,
            "referenceAudioPath": self.reference_audio_path,
            "promptAudioPath": self.prompt_audio_path,
            "promptText": self.prompt_text,
            "consentConfirmed": self.consent_confirmed,
            "cfgValue": self.cfg_value,
            "inferenceTimesteps": self.inference_timesteps,
            "seed": self.seed,
            "normalizeText": self.normalize_text,
            "device": self.device_code,
            "metadata": dict(self.metadata),
        }

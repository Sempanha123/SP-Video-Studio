from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from domain.voice_config import VoiceConfig


class TTSEngineState(StrEnum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class TTSCapabilities:
    supports_text_to_speech: bool = True
    supports_voice_design: bool = False
    supports_reference_voice: bool = False
    supports_prompt_audio: bool = False
    supports_seed: bool = False
    supports_cfg: bool = False
    supports_inference_steps: bool = False
    supports_streaming: bool = False
    supports_cpu: bool = True
    supports_cuda: bool = False
    supported_languages: tuple[str, ...] = ()
    output_sample_rate: int | None = None


@dataclass(slots=True)
class TTSRequest:
    project_id: str
    text: str
    language: str
    output_path: Path
    voice_config: VoiceConfig = field(default_factory=VoiceConfig)
    request_id: str = field(default_factory=lambda: str(uuid4()))
    script_id: str | None = None
    section_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TTSResult:
    output_path: Path
    sample_rate: int
    channels: int
    duration_ms: int
    engine_version: str = ""
    model_version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

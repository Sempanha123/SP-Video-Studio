from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


class STTEngineState(StrEnum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"


class STTDevice(StrEnum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


@dataclass(frozen=True, slots=True)
class STTCapabilities:
    supports_language_detection: bool = True
    supports_word_timestamps: bool = True
    supports_vad: bool = True
    supports_batching: bool = True
    supports_cpu: bool = True
    supports_cuda: bool = True
    supports_multilingual: bool = True
    supports_hotwords: bool = True
    supports_translation_mode: bool = False
    supports_streaming: bool = False


@dataclass(slots=True)
class TranscriptionRequest:
    project_id: str
    media_id: str
    model_id: str
    source_path: Path | str
    language: str = "auto"
    word_timestamps: bool = True
    vad_enabled: bool = True
    vad_settings: dict[str, Any] = field(default_factory=dict)
    device: str = STTDevice.AUTO.value
    compute_type: str = "auto"
    beam_size: int = 5
    batch_mode: bool = False
    batch_size: int = 4
    initial_prompt: str = ""
    hotwords: str = ""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> Path:
        return Path(self.source_path)


@dataclass(slots=True)
class STTWordResult:
    start: float
    end: float
    text: str
    probability: float | None = None


@dataclass(slots=True)
class STTSegmentResult:
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_probability: float | None = None
    temperature: float | None = None
    words: list[STTWordResult] = field(default_factory=list)


@dataclass(slots=True)
class STTTranscriptionInfo:
    language: str | None = None
    language_probability: float | None = None
    duration_seconds: float | None = None
    duration_after_vad_seconds: float | None = None
    faster_whisper_version: str = ""
    ctranslate2_version: str = ""
    model_version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class STTOutput:
    segments: Iterable[STTSegmentResult]
    info: STTTranscriptionInfo

from __future__ import annotations

from abc import abstractmethod

from engines.base import Engine
from engines.stt.types import STTCapabilities, STTEngineState, STTOutput, TranscriptionRequest


class STTEngine(Engine):
    @abstractmethod
    def load(self, *, model_path: str, device: str, compute_type: str, batch_mode: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_loaded(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def state(self) -> STTEngineState:
        raise NotImplementedError

    @abstractmethod
    def transcribe(self, request: TranscriptionRequest) -> STTOutput:
        raise NotImplementedError

    @abstractmethod
    def detect_language(self, request: TranscriptionRequest) -> tuple[str, float | None]:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: TranscriptionRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> STTCapabilities:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, object]:
        raise NotImplementedError

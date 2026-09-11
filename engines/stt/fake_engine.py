from __future__ import annotations

from engines.base import EngineCapabilities
from engines.stt.base import STTEngine
from engines.stt.errors import STTCancelled, STTInvalidRequest
from engines.stt.types import (
    STTCapabilities,
    STTEngineState,
    STTOutput,
    STTSegmentResult,
    STTTranscriptionInfo,
    STTWordResult,
    TranscriptionRequest,
)


class FakeSTTEngine(STTEngine):
    """Fast deterministic test engine. Production selection never registers it."""

    def __init__(self, *, language: str = "en") -> None:
        self._state = STTEngineState.UNLOADED
        self._language = language
        self.load_count = 0
        self.transcribe_count = 0
        self.cancel_after_segments: int | None = None

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(name="Fake STT", version="test", features={"stt"})

    def get_capabilities(self) -> STTCapabilities:
        return STTCapabilities()

    def is_available(self) -> bool:
        return True

    def load(self, *, model_path: str, device: str, compute_type: str, batch_mode: bool = False) -> None:
        self._state = STTEngineState.LOADING
        self.load_count += 1
        self._state = STTEngineState.LOADED

    def unload(self) -> None:
        self._state = STTEngineState.UNLOADING
        self._state = STTEngineState.UNLOADED

    def is_loaded(self) -> bool:
        return self._state == STTEngineState.LOADED

    def state(self) -> STTEngineState:
        return self._state

    def validate_request(self, request: TranscriptionRequest) -> None:
        if not request.project_id or not request.media_id or not request.model_id:
            raise STTInvalidRequest("Project, media and model are required.")
        if request.language not in {"auto", "en", "km"}:
            raise STTInvalidRequest("Unsupported transcription language.")
        if request.beam_size < 1 or request.beam_size > 20:
            raise STTInvalidRequest("Beam size must be between 1 and 20.")
        if request.batch_size < 1 or request.batch_size > 64:
            raise STTInvalidRequest("Batch size must be between 1 and 64.")

    def detect_language(self, request: TranscriptionRequest) -> tuple[str, float | None]:
        return (self._language if request.language == "auto" else request.language, 0.99)

    def transcribe(self, request: TranscriptionRequest) -> STTOutput:
        self.validate_request(request)
        if not self.is_loaded():
            raise STTInvalidRequest("Fake STT engine must be loaded before transcription.")
        self.transcribe_count += 1
        lang = self._language if request.language == "auto" else request.language

        def iterator():
            segments = [
                STTSegmentResult(
                    start=0.0,
                    end=2.0,
                    text="Hello" if lang == "en" else "សួស្តី",
                    avg_logprob=-0.1,
                    no_speech_probability=0.01,
                    temperature=0.0,
                    words=[STTWordResult(0.0, 1.0, "Hello" if lang == "en" else "សួស្តី", 0.98)],
                ),
                STTSegmentResult(
                    start=2.0,
                    end=4.5,
                    text="Welcome to the video." if lang == "en" else "សូមស្វាគមន៍មកកាន់វីដេអូ។",
                    avg_logprob=-0.12,
                    no_speech_probability=0.02,
                    temperature=0.0,
                    words=[STTWordResult(2.0, 3.0, "Welcome" if lang == "en" else "សូមស្វាគមន៍", 0.97)],
                ),
            ]
            for index, segment in enumerate(segments):
                if self.cancel_after_segments is not None and index >= self.cancel_after_segments:
                    raise STTCancelled()
                yield segment

        return STTOutput(
            segments=iterator(),
            info=STTTranscriptionInfo(
                language=lang,
                language_probability=0.99,
                duration_seconds=4.5,
                duration_after_vad_seconds=4.5,
                faster_whisper_version="fake",
                ctranslate2_version="fake",
                model_version=request.model_id,
            ),
        )

    def health_check(self) -> dict[str, object]:
        return {"available": True, "loaded": self.is_loaded(), "state": self._state.value}

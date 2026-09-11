from __future__ import annotations

import importlib
import importlib.metadata
import logging
from pathlib import Path
from threading import RLock

from engines.base import EngineCapabilities
from engines.stt.base import STTEngine
from engines.stt.errors import (
    STTDependencyMissing,
    STTInvalidMedia,
    STTInvalidRequest,
    STTModelLoadError,
    STTOutOfMemory,
    STTTranscriptionError,
    STTUnsupportedDevice,
)
from engines.stt.types import (
    STTCapabilities,
    STTEngineState,
    STTOutput,
    STTSegmentResult,
    STTTranscriptionInfo,
    STTWordResult,
    TranscriptionRequest,
)


class FasterWhisperEngine(STTEngine):
    """Lazy adapter for official faster-whisper 1.2.x APIs."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("sp_video_studio.stt.faster_whisper")
        self._model = None
        self._pipeline = None
        self._state = STTEngineState.UNLOADED
        self._config: tuple[str, str, str, bool] | None = None
        self._lock = RLock()

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(name="faster-whisper", version=self._package_version("faster-whisper"), features={"stt"})

    def get_capabilities(self) -> STTCapabilities:
        return STTCapabilities()

    def is_available(self) -> bool:
        return importlib.util.find_spec("faster_whisper") is not None and importlib.util.find_spec("ctranslate2") is not None

    def state(self) -> STTEngineState:
        return self._state

    def is_loaded(self) -> bool:
        return self._state == STTEngineState.LOADED and self._model is not None

    def load(self, *, model_path: str, device: str, compute_type: str, batch_mode: bool = False) -> None:
        with self._lock:
            path = Path(model_path)
            if not path.is_dir():
                raise STTModelLoadError("The installed Whisper model folder could not be found.")
            config = (str(path.resolve()), device, compute_type, bool(batch_mode))
            if self.is_loaded() and self._config == config:
                return
            if self.is_loaded():
                self.unload()
            if not self.is_available():
                raise STTDependencyMissing()
            self._state = STTEngineState.LOADING
            try:
                module = importlib.import_module("faster_whisper")
                WhisperModel = getattr(module, "WhisperModel")
                self._model = WhisperModel(
                    str(path),
                    device=device,
                    compute_type=compute_type,
                    local_files_only=True,
                )
                self._pipeline = None
                if batch_mode:
                    Pipeline = getattr(module, "BatchedInferencePipeline")
                    self._pipeline = Pipeline(model=self._model)
                self._config = config
                self._state = STTEngineState.LOADED
            except Exception as exc:
                self._model = None
                self._pipeline = None
                self._config = None
                self._state = STTEngineState.ERROR
                raise self._map_exception(exc, loading=True) from exc

    def unload(self) -> None:
        with self._lock:
            self._state = STTEngineState.UNLOADING
            self._pipeline = None
            self._model = None
            self._config = None
            self._state = STTEngineState.UNLOADED

    def validate_request(self, request: TranscriptionRequest) -> None:
        if not request.project_id or not request.media_id or not request.model_id:
            raise STTInvalidRequest("Project, media and model are required.")
        if not request.path.is_file():
            raise STTInvalidMedia("The project media file could not be found.")
        if request.language not in {"auto", "en", "km"}:
            raise STTInvalidRequest("Language must be Auto Detect, English, or Khmer.")
        if request.device not in {"auto", "cpu", "cuda"} and not request.device.startswith("cuda:"):
            raise STTUnsupportedDevice(f"Unsupported STT device: {request.device}")
        if request.beam_size < 1 or request.beam_size > 20:
            raise STTInvalidRequest("Beam size must be between 1 and 20.")
        if request.batch_size < 1 or request.batch_size > 64:
            raise STTInvalidRequest("Batch size must be between 1 and 64.")

    def detect_language(self, request: TranscriptionRequest) -> tuple[str, float | None]:
        # faster-whisper reports language in TranscriptionInfo. To avoid decoding twice,
        # the normal service reads it from the actual transcription result.
        output = self.transcribe(request)
        iterator = iter(output.segments)
        try:
            next(iterator)
        except StopIteration:
            pass
        return output.info.language or "", output.info.language_probability

    def transcribe(self, request: TranscriptionRequest) -> STTOutput:
        self.validate_request(request)
        if not self.is_loaded() or self._model is None:
            raise STTModelLoadError("The Whisper model is not loaded.")
        language = None if request.language == "auto" else request.language
        kwargs = {
            "language": language,
            "task": "transcribe",
            "beam_size": request.beam_size,
            "word_timestamps": request.word_timestamps,
            "vad_filter": request.vad_enabled,
            "initial_prompt": request.initial_prompt or None,
            "hotwords": request.hotwords or None,
        }
        if request.vad_enabled and request.vad_settings:
            kwargs["vad_parameters"] = dict(request.vad_settings)
        try:
            if request.batch_mode:
                if self._pipeline is None:
                    module = importlib.import_module("faster_whisper")
                    self._pipeline = getattr(module, "BatchedInferencePipeline")(model=self._model)
                segments, info = self._pipeline.transcribe(str(request.path), batch_size=request.batch_size, **kwargs)
            else:
                segments, info = self._model.transcribe(str(request.path), **kwargs)
        except Exception as exc:
            raise self._map_exception(exc) from exc

        def iterator():
            try:
                for segment in segments:  # generator consumption is the actual inference
                    words = []
                    for word in getattr(segment, "words", None) or []:
                        words.append(
                            STTWordResult(
                                start=float(getattr(word, "start", 0.0) or 0.0),
                                end=float(getattr(word, "end", 0.0) or 0.0),
                                text=str(getattr(word, "word", "") or ""),
                                probability=(
                                    float(getattr(word, "probability"))
                                    if getattr(word, "probability", None) is not None
                                    else None
                                ),
                            )
                        )
                    yield STTSegmentResult(
                        start=float(getattr(segment, "start", 0.0) or 0.0),
                        end=float(getattr(segment, "end", 0.0) or 0.0),
                        text=str(getattr(segment, "text", "") or ""),
                        avg_logprob=(float(segment.avg_logprob) if getattr(segment, "avg_logprob", None) is not None else None),
                        no_speech_probability=(
                            float(segment.no_speech_prob) if getattr(segment, "no_speech_prob", None) is not None else None
                        ),
                        temperature=(float(segment.temperature) if getattr(segment, "temperature", None) is not None else None),
                        words=words,
                    )
            except Exception as exc:
                raise self._map_exception(exc) from exc

        return STTOutput(
            segments=iterator(),
            info=STTTranscriptionInfo(
                language=str(getattr(info, "language", "") or "") or None,
                language_probability=(
                    float(getattr(info, "language_probability"))
                    if getattr(info, "language_probability", None) is not None
                    else None
                ),
                duration_seconds=(float(getattr(info, "duration")) if getattr(info, "duration", None) is not None else None),
                duration_after_vad_seconds=(
                    float(getattr(info, "duration_after_vad"))
                    if getattr(info, "duration_after_vad", None) is not None
                    else None
                ),
                faster_whisper_version=self._package_version("faster-whisper"),
                ctranslate2_version=self._package_version("ctranslate2"),
                model_version=request.model_id,
            ),
        )

    def health_check(self) -> dict[str, object]:
        return {
            "available": self.is_available(),
            "loaded": self.is_loaded(),
            "state": self._state.value,
            "faster_whisper_version": self._package_version("faster-whisper"),
            "ctranslate2_version": self._package_version("ctranslate2"),
            "config": self._config,
        }

    @staticmethod
    def _package_version(name: str) -> str:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return ""

    @staticmethod
    def _map_exception(exc: Exception, *, loading: bool = False) -> Exception:
        text = str(exc).lower()
        if "out of memory" in text or "cuda_error_out_of_memory" in text or "allocation" in text and "memory" in text:
            return STTOutOfMemory()
        if "cuda" in text and ("not found" in text or "cudnn" in text or "cublas" in text or "driver" in text):
            return STTUnsupportedDevice("Speech recognition could not start with CUDA. Check CTranslate2 CUDA libraries or use CPU.")
        if loading:
            return STTModelLoadError(str(exc) or STTModelLoadError.user_message)
        if isinstance(exc, (OSError, ValueError)) and ("audio" in text or "decode" in text or "av" in text):
            return STTInvalidMedia()
        return STTTranscriptionError(str(exc) or STTTranscriptionError.user_message)

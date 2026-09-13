from __future__ import annotations

import hashlib
import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SUPPORTED_FAKE_LANGUAGES = ("en", "km", "th", "vi")


def _attr(obj: object, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _deterministic_frequency(seed: str, base: int = 180, span: int = 220) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base + int.from_bytes(digest[:2], "big") % span


def _write_tone(path: Path, *, seed: str, seconds: float = 0.7, sample_rate: int = 16_000) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frequency = _deterministic_frequency(seed)
    frames = max(1, int(sample_rate * seconds))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for i in range(frames):
            sample = int(0.20 * 32767 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            handle.writeframesraw(struct.pack("<h", sample))


@dataclass(slots=True)
class FakeEngineCounters:
    loads: int = 0
    unloads: int = 0
    calls: int = 0


class FakeTTSEngine:
    """Small deterministic TTS double matching the production engine contract.

    It writes a real mono WAV using only the Python standard library. No model,
    network, CUDA, random seed, or user data is required.
    """

    def __init__(self, *, fail: bool = False) -> None:
        self._loaded = False
        self.fail = fail
        self.counters = FakeEngineCounters()

    def is_available(self) -> bool:
        return True

    def load(self, device: str = "auto") -> None:
        self._loaded = True
        self.counters.loads += 1

    def unload(self) -> None:
        self._loaded = False
        self.counters.unloads += 1

    def is_loaded(self) -> bool:
        return self._loaded

    def validate_request(self, request: object) -> None:
        text = str(_attr(request, "text", "")).strip()
        language = str(_attr(request, "language", "en")).lower()
        if not text:
            raise ValueError("Fake TTS text cannot be empty.")
        if language not in SUPPORTED_FAKE_LANGUAGES:
            raise ValueError(f"Fake TTS does not support {language}.")

    def generate(self, request: object, cancellation: object | None = None) -> object:
        self.validate_request(request)
        if cancellation is not None and bool(getattr(cancellation, "cancelled", False)):
            raise RuntimeError("Fake TTS cancelled.")
        if self.fail:
            raise RuntimeError("Injected fake TTS failure.")
        if not self._loaded:
            self.load("cpu")
        self.counters.calls += 1
        text = str(_attr(request, "text"))
        language = str(_attr(request, "language", "en"))
        output = Path(_attr(request, "output_path"))
        duration_s = min(1.8, max(0.35, 0.30 + len(text) * 0.012))
        _write_tone(output, seed=f"{language}:{text}", seconds=duration_s)
        try:
            from engines.tts.types import TTSResult
            return TTSResult(
                output_path=output,
                sample_rate=16_000,
                channels=1,
                duration_ms=int(duration_s * 1000),
                engine_version="phase39-fake-1",
                model_version="deterministic",
                metadata={"fake": True, "language": language},
            )
        except Exception:
            return SimpleNamespace(
                output_path=output,
                sample_rate=16_000,
                channels=1,
                duration_ms=int(duration_s * 1000),
                engine_version="phase39-fake-1",
                model_version="deterministic",
                metadata={"fake": True, "language": language},
            )

    def get_capabilities(self) -> object:
        try:
            from engines.tts.types import TTSCapabilities
            return TTSCapabilities(
                supports_text_to_speech=True,
                supports_cpu=True,
                supports_cuda=False,
                supported_languages=SUPPORTED_FAKE_LANGUAGES,
                output_sample_rate=16_000,
            )
        except Exception:
            return SimpleNamespace(
                supports_text_to_speech=True,
                supports_cpu=True,
                supports_cuda=False,
                supported_languages=SUPPORTED_FAKE_LANGUAGES,
                output_sample_rate=16_000,
            )

    def health_check(self) -> bool:
        return True

    def capabilities(self) -> object:
        return self.get_capabilities()


class FakeSTTEngine:
    """Deterministic STT double returning stable multilingual segments."""

    def __init__(self, *, fail: bool = False) -> None:
        self._loaded = False
        self.fail = fail
        self.counters = FakeEngineCounters()

    def is_available(self) -> bool:
        return True

    def load(self, *, model_path: str = "", device: str = "cpu", compute_type: str = "int8", batch_mode: bool = False) -> None:
        self._loaded = True
        self.counters.loads += 1

    def unload(self) -> None:
        self._loaded = False
        self.counters.unloads += 1

    def is_loaded(self) -> bool:
        return self._loaded

    def state(self) -> object:
        try:
            from engines.stt.types import STTEngineState
            return STTEngineState.LOADED if self._loaded else STTEngineState.UNLOADED
        except Exception:
            return "loaded" if self._loaded else "unloaded"

    def validate_request(self, request: object) -> None:
        path = Path(_attr(request, "source_path", ""))
        if not path.is_file():
            raise FileNotFoundError(path)
        language = str(_attr(request, "language", "auto")).lower()
        if language != "auto" and language not in SUPPORTED_FAKE_LANGUAGES:
            raise ValueError(f"Fake STT does not support {language}.")

    def _language(self, request: object) -> str:
        language = str(_attr(request, "language", "auto")).lower()
        if language in SUPPORTED_FAKE_LANGUAGES:
            return language
        metadata = _attr(request, "metadata", {}) or {}
        hinted = str(metadata.get("fixtureLanguage", "en")).lower() if isinstance(metadata, dict) else "en"
        return hinted if hinted in SUPPORTED_FAKE_LANGUAGES else "en"

    def detect_language(self, request: object) -> tuple[str, float | None]:
        self.validate_request(request)
        return self._language(request), 1.0

    def transcribe(self, request: object) -> object:
        self.validate_request(request)
        if self.fail:
            raise RuntimeError("Injected fake STT failure.")
        if not self._loaded:
            self.load()
        self.counters.calls += 1
        language = self._language(request)
        samples = {
            "en": "Hello from the deterministic interview fixture.",
            "km": "សួស្តី ពីការសាកល្បងសំឡេង។",
            "th": "สวัสดีจากชุดทดสอบเสียง",
            "vi": "Xin chào từ bộ kiểm thử âm thanh.",
        }
        text = samples[language]
        try:
            from engines.stt.types import STTOutput, STTSegmentResult, STTTranscriptionInfo, STTWordResult
            words = [
                STTWordResult(start=0.0, end=0.4, text=text.split()[0] if text.split() else text, probability=1.0)
            ]
            segment = STTSegmentResult(start=0.0, end=1.0, text=text, words=words)
            return STTOutput(
                segments=[segment],
                info=STTTranscriptionInfo(language=language, language_probability=1.0, duration_seconds=1.0),
            )
        except Exception:
            return SimpleNamespace(
                segments=[SimpleNamespace(start=0.0, end=1.0, text=text, words=[])],
                info=SimpleNamespace(language=language, language_probability=1.0, duration_seconds=1.0),
            )

    def get_capabilities(self) -> object:
        try:
            from engines.stt.types import STTCapabilities
            return STTCapabilities(
                supports_language_detection=True,
                supports_word_timestamps=True,
                supports_vad=True,
                supports_batching=True,
                supports_cpu=True,
                supports_cuda=False,
                supports_multilingual=True,
            )
        except Exception:
            return SimpleNamespace(
                supports_language_detection=True,
                supports_word_timestamps=True,
                supports_vad=True,
                supports_batching=True,
                supports_cpu=True,
                supports_cuda=False,
                supports_multilingual=True,
            )

    def health_check(self) -> dict[str, object]:
        return {"available": True, "loaded": self._loaded, "fake": True}


class FakeTranslationEngine:
    """Deterministic local translation double for the four QA languages."""

    def __init__(self, *, fail: bool = False) -> None:
        self._loaded = False
        self.fail = fail
        self.counters = FakeEngineCounters()

    def is_available(self) -> bool:
        return True

    def load(self, *, model_path: str = "", model_id: str = "", device: str = "cpu") -> None:
        self._loaded = True
        self.counters.loads += 1

    def unload(self) -> None:
        self._loaded = False
        self.counters.unloads += 1

    def is_loaded(self) -> bool:
        return self._loaded

    def supports_language_pair(self, source: str, target: str) -> bool:
        return source in SUPPORTED_FAKE_LANGUAGES and target in SUPPORTED_FAKE_LANGUAGES and source != target

    def get_supported_language_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple((a, b) for a in SUPPORTED_FAKE_LANGUAGES for b in SUPPORTED_FAKE_LANGUAGES if a != b)

    def validate_request(self, request: object) -> None:
        source = str(_attr(request, "source_language", ""))
        target = str(_attr(request, "target_language", ""))
        text = str(_attr(request, "text", "")).strip()
        if not self.supports_language_pair(source, target):
            raise ValueError(f"Unsupported fake translation pair: {source}->{target}")
        if not text:
            raise ValueError("Translation text cannot be empty.")

    def translate(self, request: object, cancellation: object | None = None) -> object:
        self.validate_request(request)
        if self.fail:
            raise RuntimeError("Injected fake translation failure.")
        if not self._loaded:
            self.load()
        self.counters.calls += 1
        source = str(_attr(request, "source_language"))
        target = str(_attr(request, "target_language"))
        text = str(_attr(request, "text"))
        translated = f"[{target}←{source}] {text}"
        try:
            from engines.translation.types import TranslationResult
            return TranslationResult(
                text=translated,
                model_id="phase39-fake",
                provider_version="1",
                metadata={"fake": True, "source": source, "target": target},
            )
        except Exception:
            return SimpleNamespace(
                text=translated,
                model_id="phase39-fake",
                provider_version="1",
                metadata={"fake": True, "source": source, "target": target},
            )

    def translate_batch(self, requests: list[object], cancellation: object | None = None) -> list[object]:
        return [self.translate(request, cancellation) for request in requests]

    def get_capabilities(self) -> object:
        try:
            from engines.translation.types import TranslationCapabilities
            return TranslationCapabilities(
                supports_batch=True,
                supports_context=True,
                supports_cpu=True,
                supports_cuda=False,
                supports_offline=True,
                requires_network=False,
                requires_credentials=False,
            )
        except Exception:
            return SimpleNamespace(
                supports_batch=True,
                supports_context=True,
                supports_cpu=True,
                supports_cuda=False,
                supports_offline=True,
                requires_network=False,
                requires_credentials=False,
            )

    def health_check(self) -> dict[str, object]:
        return {"available": True, "loaded": self._loaded, "fake": True}


class FakeDirectorProvider:
    """Deterministic structured Director/LLM test double."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, object]] = []

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, **options: object) -> str:
        if self.fail:
            raise RuntimeError("Injected fake Director failure.")
        self.calls.append(("generate", prompt))
        return f"DETERMINISTIC:{hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:12]}"

    def generate_structured(self, task: str, input: Any, schema: object | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("Injected fake Director failure.")
        self.calls.append((task, input))
        digest = hashlib.sha256(repr((task, input, context)).encode("utf-8")).hexdigest()[:12]
        return {
            "provider": "phase39-fake-director",
            "task": task,
            "planId": digest,
            "input": input,
            "context": dict(context or {}),
            "deterministic": True,
        }

    def health_check(self) -> dict[str, object]:
        return {"available": True, "fake": True}

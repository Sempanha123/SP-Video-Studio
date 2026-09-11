from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from engines.tts.base import TTSEngine
from engines.tts.errors import TTSCancelled
from engines.tts.types import TTSCapabilities, TTSEngineState, TTSRequest, TTSResult
from workers.cancellation import CancellationToken


class FakeTTSEngine(TTSEngine):
    """Tiny deterministic WAV engine used only by tests."""

    def __init__(self, sample_rate: int = 16_000) -> None:
        self.sample_rate = sample_rate
        self.state = TTSEngineState.UNLOADED
        self.load_count = 0

    def load(self, device: str = "auto") -> None:
        if self.state == TTSEngineState.LOADED:
            return
        self.state = TTSEngineState.LOADING
        self.load_count += 1
        self.state = TTSEngineState.LOADED

    def unload(self) -> None:
        self.state = TTSEngineState.UNLOADED

    def is_loaded(self) -> bool:
        return self.state == TTSEngineState.LOADED

    def get_capabilities(self) -> TTSCapabilities:
        return TTSCapabilities(
            supports_voice_design=True,
            supports_reference_voice=True,
            supports_prompt_audio=True,
            supports_seed=True,
            supports_cfg=True,
            supports_inference_steps=True,
            supports_cpu=True,
            supports_cuda=True,
            supported_languages=("en", "km"),
            output_sample_rate=self.sample_rate,
        )

    def validate_request(self, request: TTSRequest) -> None:
        if not request.text.strip():
            raise ValueError("Text is required.")

    def generate(self, request: TTSRequest, cancellation: CancellationToken | None = None) -> TTSResult:
        self.validate_request(request)
        if not self.is_loaded():
            self.load(request.voice_config.device_code)
        if cancellation and cancellation.is_cancelled:
            raise TTSCancelled()
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_s = max(0.12, min(1.0, len(request.text) / 100.0))
        frames = int(self.sample_rate * duration_s)
        with wave.open(str(request.output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            for index in range(frames):
                if cancellation and cancellation.is_cancelled:
                    raise TTSCancelled()
                sample = int(1000 * math.sin(2 * math.pi * 220 * index / self.sample_rate))
                wav.writeframesraw(struct.pack("<h", sample))
        return TTSResult(
            request.output_path,
            self.sample_rate,
            1,
            int(duration_s * 1000),
            engine_version="fake",
            model_version="fake",
        )

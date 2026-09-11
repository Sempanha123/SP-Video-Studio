from __future__ import annotations

import os
from pathlib import Path

import pytest

from engines.stt.faster_whisper_engine import FasterWhisperEngine
from engines.stt.types import TranscriptionRequest

pytestmark = [pytest.mark.integration, pytest.mark.faster_whisper]


def test_real_faster_whisper_short_transcription():
    if os.getenv("SPVS_RUN_FASTER_WHISPER_INTEGRATION") != "1":
        pytest.skip("Set SPVS_RUN_FASTER_WHISPER_INTEGRATION=1 for the real faster-whisper test")
    model_path = Path(os.getenv("SPVS_WHISPER_MODEL_PATH", "").strip())
    media_path = Path(os.getenv("SPVS_WHISPER_MEDIA_PATH", "").strip())
    if not model_path.is_dir():
        pytest.skip("SPVS_WHISPER_MODEL_PATH is not configured")
    if not media_path.is_file():
        pytest.skip("SPVS_WHISPER_MEDIA_PATH is not configured")

    engine = FasterWhisperEngine()
    if not engine.is_available():
        pytest.skip("faster-whisper/CTranslate2 runtime is not installed")
    device = os.getenv("SPVS_WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("SPVS_WHISPER_COMPUTE_TYPE", "int8" if device == "cpu" else "float16")
    engine.load(model_path=str(model_path), device=device, compute_type=compute_type)
    try:
        output = engine.transcribe(
            TranscriptionRequest(
                project_id="integration",
                media_id="fixture",
                model_id="integration-model",
                source_path=media_path,
                language=os.getenv("SPVS_WHISPER_LANGUAGE", "auto"),
                word_timestamps=True,
                vad_enabled=True,
                device=device,
                compute_type=compute_type,
            )
        )
        segments = list(output.segments)
        assert output.info.language
        assert all(segment.end >= segment.start >= 0 for segment in segments)
        assert all(word.end >= word.start >= 0 for segment in segments for word in segment.words)
    finally:
        engine.unload()

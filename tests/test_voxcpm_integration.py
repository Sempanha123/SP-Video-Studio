from __future__ import annotations

import os
from pathlib import Path

import pytest

from domain.voice_config import VoiceConfig
from engines.tts.types import TTSRequest
from engines.tts.voxcpm2_engine import VoxCPM2Engine

pytestmark = [pytest.mark.integration, pytest.mark.voxcpm]


def test_real_voxcpm_short_english_generation(tmp_path: Path):
    if os.getenv("SPVS_RUN_VOXCPM_INTEGRATION") != "1":
        pytest.skip("Set SPVS_RUN_VOXCPM_INTEGRATION=1 for the real VoxCPM2 test")
    model_path = os.getenv("SPVS_VOXCPM_MODEL_PATH", "").strip()
    if not model_path:
        pytest.skip("SPVS_VOXCPM_MODEL_PATH is not configured")
    engine = VoxCPM2Engine(Path(model_path))
    if not engine.is_available():
        pytest.skip("VoxCPM/PyTorch runtime is not installed")
    output = tmp_path / "english.wav"
    engine.load(os.getenv("SPVS_VOXCPM_DEVICE", "auto"))
    try:
        result = engine.generate(
            TTSRequest(
                project_id="integration",
                text="Hello. This is a short original speech synthesis test.",
                language="en",
                output_path=output,
                voice_config=VoiceConfig(device=os.getenv("SPVS_VOXCPM_DEVICE", "auto")),
            )
        )
        assert output.is_file() and output.stat().st_size > 44
        assert result.duration_ms > 0
        assert result.sample_rate > 0
    finally:
        engine.unload()

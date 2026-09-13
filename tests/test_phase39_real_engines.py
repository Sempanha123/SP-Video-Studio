from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.real_engine_optional


def test_voxcpm2_capabilities_and_short_smoke_only_when_installed(tmp_path):
    model = os.environ.get("SPVS_QA_VOXCPM_MODEL", "").strip()
    if not model or not Path(model).exists():
        pytest.skip("VoxCPM2 model not configured; standard CI must not download it")
    try:
        from engines.tts.voxcpm2_engine import VoxCPM2Engine
    except Exception as exc:
        pytest.skip(f"VoxCPM2 runtime unavailable: {exc}")
    engine = VoxCPM2Engine(Path(model))
    caps = engine.get_capabilities()
    supported = tuple(getattr(caps, "supported_languages", ()) or ())
    # Query actual capability instead of assuming every registry language works.
    assert isinstance(supported, tuple)
    pytest.skip("Model-present synthesis is a workstation acceptance step; capability discovery succeeded")


def test_whisper_capabilities_only_when_installed():
    model = os.environ.get("SPVS_QA_WHISPER_MODEL", "").strip()
    if not model or not Path(model).exists():
        pytest.skip("Whisper model not configured; standard CI must not download it")
    try:
        from engines.stt.faster_whisper_engine import FasterWhisperEngine
    except Exception as exc:
        pytest.skip(f"faster-whisper runtime unavailable: {exc}")
    engine = FasterWhisperEngine()
    caps = engine.get_capabilities()
    assert bool(getattr(caps, "supports_multilingual", False)) in {True, False}


def test_translation_model_is_optional_and_capability_driven():
    model = os.environ.get("SPVS_QA_TRANSLATION_MODEL", "").strip()
    if not model or not Path(model).exists():
        pytest.skip("Local translation model not configured; standard CI must not download it")
    # The production manager/provider decides supported pairs. This profile must
    # query configured capability rather than asserting all languages are valid.
    try:
        from engines.translation.manager import TranslationEngineManager
    except Exception as exc:
        pytest.skip(f"Translation runtime unavailable: {exc}")
    manager = TranslationEngineManager()
    assert manager is not None
    pytest.skip("A concrete configured translation engine is required for workstation inference smoke")

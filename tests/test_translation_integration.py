from __future__ import annotations

import os
from pathlib import Path

import pytest

from engines.translation.local_marian_engine import LocalMarianEngine
from engines.translation.types import TranslationRequest

pytestmark = [pytest.mark.integration, pytest.mark.translation]


@pytest.mark.skipif(
    os.getenv("SPVS_RUN_TRANSLATION_INTEGRATION") != "1",
    reason="Set SPVS_RUN_TRANSLATION_INTEGRATION=1 for real English↔Khmer local model tests",
)
def test_real_local_translation_models_opt_in():
    en_km = os.getenv("SPVS_TRANSLATION_EN_KM_PATH", "").strip()
    km_en = os.getenv("SPVS_TRANSLATION_KM_EN_PATH", "").strip()
    if not en_km or not km_en:
        pytest.skip("Set SPVS_TRANSLATION_EN_KM_PATH and SPVS_TRANSLATION_KM_EN_PATH to managed model folders")
    engine = LocalMarianEngine()
    engine.load(model_path=en_km, model_id="translation-en-km-opus", device="cpu")
    khmer = engine.translate(TranslationRequest(project_id="integration", source_language="en", target_language="km", text="Technology changes quickly."))
    assert khmer.text.strip()
    engine.unload()
    engine.load(model_path=km_en, model_id="translation-km-en-opus", device="cpu")
    english = engine.translate(TranslationRequest(project_id="integration", source_language="km", target_language="en", text="សួស្តី! នេះជាការសាកល្បង។"))
    assert english.text.strip()
    engine.unload()

from pathlib import Path

import pytest

from engines.translation.errors import TranslationInvalidRequest, TranslationUnsupportedLanguagePair
from engines.translation.local_marian_engine import LocalMarianEngine, MODEL_TARGET_PREFIX
from engines.translation.manual_engine import ManualTranslationEngine
from engines.translation.types import TranslationRequest


def test_marian_target_language_token_and_supported_pairs():
    assert MODEL_TARGET_PREFIX[("en", "km")] == ">>khm<< "
    assert MODEL_TARGET_PREFIX[("km", "en")] == ""
    engine = LocalMarianEngine()
    assert engine.get_supported_language_pairs() == (("en", "km"), ("km", "en"))
    with pytest.raises(TranslationInvalidRequest):
        engine.validate_request(TranslationRequest(project_id="p", source_language="en", target_language="fr", text="Hello"))


def test_manual_provider_is_offline_and_language_pair_aware():
    engine = ManualTranslationEngine()
    caps = engine.get_capabilities()
    assert caps.supports_offline and caps.supports_cpu and not caps.supports_cuda
    assert engine.supports_language_pair("km", "en")


def test_local_engine_is_lazy_and_does_not_import_transformers_at_construction():
    engine = LocalMarianEngine()
    assert not engine.is_loaded()
    assert engine.health_check()["loaded"] is False


def test_translation_optional_dependency_uses_current_direct_transformers_family():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    adapter = Path("engines/translation/local_marian_engine.py").read_text(encoding="utf-8")
    assert 'transformers>=5.17,<6' in pyproject
    assert "AutoTokenizer" in adapter and "AutoModelForSeq2SeqLM" in adapter
    assert "pipeline(" not in adapter
    assert "local_files_only=True" in adapter
    assert "truncation=False" in adapter

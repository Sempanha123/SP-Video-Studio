from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.qa_support.fake_engines import (
    FakeDirectorProvider,
    FakeSTTEngine,
    FakeTTSEngine,
    FakeTranslationEngine,
    SUPPORTED_FAKE_LANGUAGES,
)

pytestmark = pytest.mark.fast


def test_fake_tts_is_deterministic_and_offline(tmp_path):
    first = tmp_path / "a.wav"
    second = tmp_path / "b.wav"
    engine = FakeTTSEngine()
    request = lambda path: SimpleNamespace(text="សួស្តី QA", language="km", output_path=path)
    a = engine.generate(request(first)); engine.unload()
    b = engine.generate(request(second))
    assert a.duration_ms == b.duration_ms
    assert first.read_bytes() == second.read_bytes()
    assert engine.get_capabilities().supports_cuda is False


def test_fake_stt_translation_and_director_are_deterministic(tmp_path):
    source = tmp_path / "voice.wav"; source.write_bytes(b"fixture")
    stt = FakeSTTEngine(); req = SimpleNamespace(source_path=source, language="th", metadata={})
    out = stt.transcribe(req)
    assert out.info.language == "th" and list(out.segments)[0].text
    trans = FakeTranslationEngine()
    tr = SimpleNamespace(source_language="th", target_language="vi", text=list(out.segments)[0].text)
    assert trans.translate(tr).text == trans.translate(tr).text
    director = FakeDirectorProvider()
    assert director.generate_structured("plan", {"x": 1})["planId"] == director.generate_structured("plan", {"x": 1})["planId"]


@pytest.mark.parametrize("language", SUPPORTED_FAKE_LANGUAGES)
def test_fake_engine_language_matrix(language, tmp_path):
    tts = FakeTTSEngine()
    output = tmp_path / f"voice-{language}.wav"
    result = tts.generate(SimpleNamespace(text=f"QA {language}", language=language, output_path=output))
    assert Path(result.output_path).is_file()


def test_unicode_filesystem_roundtrip(tmp_path):
    values = ["ខ្មែរ", "ไทย", "Tiếng Việt", "English"]
    for value in values:
        folder = tmp_path / f"Project {value}"
        folder.mkdir()
        path = folder / f"字幕-{value}.txt"
        path.write_text(f"{value} · overlay · subtitle", encoding="utf-8")
        assert path.read_text(encoding="utf-8").startswith(value)


def test_project_controller_uses_central_language_registry():
    root = Path(__file__).resolve().parents[1]
    source = (root / "ui/controllers/project_controller.py").read_text(encoding="utf-8")
    assert "from domain.language import language_name" in source
    assert "languageName\": _language_display(project.language)" in source
    assert "LANGUAGE_NAMES =" not in source


def test_historical_entrypoint_tests_are_release_lineage_safe():
    root = Path(__file__).resolve().parents[1]
    p35 = (root / "tests/test_phase35_onboarding.py").read_text(encoding="utf-8")
    p37 = (root / "tests/test_phase37_security.py").read_text(encoding="utf-8")
    assert "remains_in_release_lineage" in p35
    assert "remains_in_release_lineage" in p37

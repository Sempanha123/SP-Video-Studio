from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.qa_support.media_fixtures import FFmpegUnavailable, validate_mp4
from tests.qa_support.workflow_harness import ReleaseWorkflowHarness

pytestmark = pytest.mark.e2e

SAMPLES = {
    "en": "English release QA",
    "km": "សួស្តី ការសាកល្បងវីដេអូ",
    "th": "สวัสดี การทดสอบวิดีโอ",
    "vi": "Xin chào kiểm thử video",
}


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    try:
        value = ReleaseWorkflowHarness(tmp_path_factory.mktemp("phase39-multilingual"))
    except FFmpegUnavailable:
        pytest.skip("FFmpeg unavailable")
    yield value
    value.close()


@pytest.mark.parametrize("language", ["en", "km", "th", "vi"])
def test_multilingual_content_matrix(harness, language):
    text = SAMPLES[language]
    project = harness.create_project("video", language, f"Project {text}")
    video = harness.copy_fixture(project, harness.fixtures.video, f"វីដេអូ-{language}.mp4")
    voice = harness.speech(project, text, speaker=f"speaker-{language}", language=language)
    subtitle = harness.subtitle(project, text, f"ចំណងជើង-{language}.srt")
    harness.record(project, "script", {"text": text})
    harness.record(project, "overlay_text", {"text": text})
    harness.record(project, "template", {"name": f"Template {text}"})
    harness.record(project, "asset_tag", {"tag": text})
    output = harness._render(
        project, video_inputs=[video], voice=voice,
        output_name=f"render-{text}.mp4",
    )
    assert validate_mp4(output)["valid"] is True
    assert subtitle.read_text(encoding="utf-8").find(text) >= 0
    assert text in json.loads(project.manifest.read_text(encoding="utf-8"))["name"]
    assert text in output.name
    events = harness.events(project)
    by_kind = {kind: payload for kind, payload in events if kind in {"script", "overlay_text", "template", "asset_tag", "speech_block", "subtitle"}}
    assert by_kind["script"]["text"] == text
    assert by_kind["overlay_text"]["text"] == text
    assert text in by_kind["template"]["name"]
    assert by_kind["asset_tag"]["tag"] == text

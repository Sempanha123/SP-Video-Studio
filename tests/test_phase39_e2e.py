from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from services.backup_service import BackupService
from services.project_migration_service import ProjectMigrationService
from tests.fixtures.phase38_legacy import make_legacy_fixture
from tests.qa_support.media_fixtures import FFmpegUnavailable, validate_mp4
from tests.qa_support.workflow_harness import ReleaseWorkflowHarness

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    root = tmp_path_factory.mktemp("phase39-e2e")
    try:
        value = ReleaseWorkflowHarness(root)
    except FFmpegUnavailable:
        pytest.skip("Mandatory E2E render profile requires FFmpeg/libx264")
    yield value
    value.close()


def _assert_render(project, output, required_events):
    assert validate_mp4(output)["valid"] is True
    event_names = [name for name, _ in project_events(project)]
    for event in required_events:
        assert event in event_names


def project_events(project):
    db = project.root.parents[1] / "qa-state.db"
    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            "SELECT kind,payload_json FROM qa_events WHERE project_id=? ORDER BY id", (project.project_id,)
        ).fetchall()
    return [(name, json.loads(payload)) for name, payload in rows]


def test_normal_video_e2e(harness):
    project, output = harness.normal_video(language="en")
    _assert_render(project, output, ["media_import", "timeline_clip", "overlay_text", "speech_block", "tts_generated", "subtitle", "audio_mix", "render"])


def test_reporter_news_e2e(harness):
    project, output = harness.reporter_news()
    _assert_render(project, output, ["news_source", "reporter_speaker", "green_screen_layer", "broll", "lower_third", "subtitle", "audio_mix", "render"])
    provenance = json.loads((project.root / "sources" / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["approved"] is True and provenance["source"].startswith("fixture://")


def test_interview_news_e2e(harness):
    project, output = harness.interview_news()
    _assert_render(project, output, ["speaker", "layout", "speech_block", "subtitle", "audio_mix", "render"])
    speakers = [payload for kind, payload in project_events(project) if kind == "speaker"]
    assert {x["name"] for x in speakers} == {"Reporter", "Guest"}
    assert len({x["voice"] for x in speakers}) == 2


def test_story_e2e(harness):
    project, output = harness.story()
    _assert_render(project, output, ["story_plan", "story_beats", "script", "scene", "speech_block", "subtitle", "audio_mix", "render"])


def test_translate_and_dub_e2e(harness):
    project, output = harness.translate_and_dub(source_language="en", target_language="km")
    _assert_render(project, output, ["transcript", "translation", "speech_block", "tts_generated", "subtitle", "audio_mix", "render"])
    translation = next(payload for kind, payload in project_events(project) if kind == "translation")
    assert translation["reviewed"] is True and translation["language"] == "km"


def test_shorts_e2e(harness):
    project, output = harness.shorts()
    _assert_render(project, output, ["manual_range", "short", "broll", "subtitle", "render"])
    short = next(payload for kind, payload in project_events(project) if kind == "short")
    assert short["aspect"] == "9:16" and short["hook"]


def test_reporter_template_e2e(harness):
    project, resolved = harness.template()
    assert resolved["templateSnapshot"]["name"] == "Reporter News"
    assert Path(resolved["presenter"]).is_file() and Path(resolved["broll"]).is_file()
    assert project.manifest.is_file()


def test_asset_library_e2e(harness):
    result = harness.asset_library()
    assert result["detached"].is_file()
    assert result["asset"].is_file()
    assert result["deleteGuard"] is True
    assert len(result["refs"]) == 2


def test_batch_factory_e2e(harness):
    result = harness.batch()
    assert result["paused"] is True
    assert len(result["outputs"]) == 3
    assert all(validate_mp4(path)["valid"] for path in result["outputs"])
    statuses = [x["status"] for x in result["states"]]
    assert "paused" in statuses and "resumed" in statuses and "failed" in statuses and "retried" in statuses


def test_recovery_e2e(harness):
    project, output = harness.recovery()
    assert json.loads(project.manifest.read_text(encoding="utf-8"))["id"] == project.project_id
    _assert_render(project, output, ["unclean_shutdown", "recovered", "render"])


@pytest.mark.migration
def test_migration_e2e_open_edit_render(tmp_path):
    db, repo, project_dir, project_id = make_legacy_fixture(tmp_path / "legacy", later=True)
    service = ProjectMigrationService(db, repo, BackupService(db, tmp_path / "migration_backups"))
    result = service.ensure_current(project_id)
    assert result.ok and result.to_version == 2
    manifest = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    manifest["phase39Edited"] = "English ខ្មែរ ไทย Tiếng Việt"
    (project_dir / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg unavailable")
    output = project_dir / "renders" / "phase39-migration-e2e.mp4"
    import subprocess
    done = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=navy:s=96x64:r=10:d=0.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(output)],
        capture_output=True, text=True, timeout=20, shell=False,
    )
    assert done.returncode == 0 and validate_mp4(output)["valid"] is True

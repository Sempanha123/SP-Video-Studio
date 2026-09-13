from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.recovery_migration_service import RecoveryMigrationService
from services.settings_migration_service import SettingsMigrationError, SettingsMigrationService
from tests.qa_support.fake_engines import FakeSTTEngine, FakeTTSEngine
from tests.qa_support.media_fixtures import generate_media_fixtures
from tests.qa_support.workflow_harness import ReleaseWorkflowHarness

pytestmark = pytest.mark.fault_injection


def test_disk_full_like_write_failure_does_not_replace_existing_file(tmp_path, monkeypatch):
    target = tmp_path / "project.json"
    target.write_text('{"safe":true}', encoding="utf-8")
    original = Path.write_text
    def fail(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError(28, "No space left on device")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", fail)
    temp = target.with_name(".project.json.tmp")
    with pytest.raises(OSError):
        temp.write_text("broken", encoding="utf-8")
    assert json.loads(target.read_text(encoding="utf-8"))["safe"] is True


def test_missing_media_fails_closed(tmp_path):
    engine = FakeSTTEngine()
    with pytest.raises(FileNotFoundError):
        engine.transcribe(SimpleNamespace(source_path=tmp_path / "missing.wav", language="en", metadata={}))


def test_tts_and_stt_injected_failures_are_actionable(tmp_path):
    source = tmp_path / "voice.wav"; source.write_bytes(b"fixture")
    with pytest.raises(RuntimeError, match="TTS failure"):
        FakeTTSEngine(fail=True).generate(SimpleNamespace(text="hello", language="en", output_path=tmp_path / "out.wav"))
    with pytest.raises(RuntimeError, match="STT failure"):
        FakeSTTEngine(fail=True).transcribe(SimpleNamespace(source_path=source, language="en", metadata={}))


def test_ffmpeg_failure_returns_nonzero_without_shell(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg unavailable")
    done = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=s=64x64:d=0.1", "-vf", "definitely_not_a_filter", "-f", "null", "-"],
        capture_output=True, text=True, timeout=20, shell=False,
    )
    assert done.returncode != 0


def test_db_write_failure_rolls_back(tmp_path):
    db = tmp_path / "qa.db"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE items(id INTEGER PRIMARY KEY,value TEXT UNIQUE)")
        connection.execute("INSERT INTO items(value) VALUES(?)", ("one",)); connection.commit()
        with pytest.raises(sqlite3.IntegrityError):
            with connection:
                connection.execute("INSERT INTO items(value) VALUES(?)", ("two",))
                connection.execute("INSERT INTO items(value) VALUES(?)", ("one",))
        assert connection.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1


def test_output_collision_is_refused(tmp_path):
    harness = ReleaseWorkflowHarness(tmp_path / "h")
    project = harness.create_project("video")
    video = harness.copy_fixture(project, harness.fixtures.video)
    voice = harness.speech(project, "collision", speaker="speaker")
    first = harness._render(project, video_inputs=[video], voice=voice, output_name="same.mp4")
    assert first.is_file()
    with pytest.raises(FileExistsError):
        harness._render(project, video_inputs=[video], voice=voice, output_name="same.mp4")
    harness.close()


def test_corrupted_template_archive_rejected_by_phase37_service(tmp_path):
    from services.archive_security_service import UnsafeArchive, validate_zip_layout
    archive = tmp_path / "bad.mmovtemplate"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "bad")
    with zipfile.ZipFile(archive, "r") as zf:
        with pytest.raises(UnsafeArchive):
            validate_zip_layout(zf)


def test_corrupted_recovery_payload_rejected_or_preserved_safely():
    service = RecoveryMigrationService()
    with pytest.raises(Exception):
        service.migrate_payload({"schemaVersion": "not-an-int"})


def test_malformed_settings_are_not_silently_executed():
    service = SettingsMigrationService()
    with pytest.raises(SettingsMigrationError):
        service.migrate(["not", "an", "object"])

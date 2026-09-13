from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from services.backup_service import BackupService
from services.project_migration_service import ProjectMigrationService
from tests.fixtures.phase38_legacy import make_legacy_fixture
from tests.qa_support.media_fixtures import FFmpegUnavailable, generate_media_fixtures, validate_mp4

pytestmark = pytest.mark.integration


def test_media_fixture_generation_and_libx264_smoke(tmp_path):
    try:
        fixtures = generate_media_fixtures(tmp_path / "media")
    except FFmpegUnavailable:
        pytest.skip("FFmpeg is unavailable")
    for path in (fixtures.video, fixtures.long_video, fixtures.green_screen, fixtures.music, fixtures.voice_wav, fixtures.image, fixtures.subtitles):
        assert path.is_file() and path.stat().st_size > 0
    assert validate_mp4(fixtures.video)["valid"] is True


def test_database_and_project_roots_are_temporary(tmp_path):
    root = tmp_path / "isolated-root"; root.mkdir()
    db = root / "qa.db"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY,value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES(?)", ("ខ្មែរ ไทย Việt",))
        connection.commit()
    assert tmp_path.resolve() in db.resolve().parents
    assert "LocalAppData" not in str(db)


@pytest.mark.migration
def test_legacy_migrate_open_edit_and_real_render(tmp_path):
    db, repo, project_dir, project_id = make_legacy_fixture(tmp_path / "legacy", later=True)
    service = ProjectMigrationService(db, repo, BackupService(db, tmp_path / "migration_backups"))
    result = service.ensure_current(project_id)
    assert result.ok and result.to_version == 2
    manifest = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    manifest["qaEdited"] = "កែសម្រួល · แก้ไข · chỉnh sửa"
    (project_dir / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is unavailable")
    output = project_dir / "renders" / "phase39-migrated.mp4"
    done = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=96x64:r=10:d=0.4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(output)],
        capture_output=True, text=True, timeout=20, shell=False,
    )
    assert done.returncode == 0 and validate_mp4(output)["valid"] is True

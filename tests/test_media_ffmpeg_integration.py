from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from media.probe import FFprobeService
from media.thumbnails import ThumbnailService
from services.media_service import MediaService
from services.project_service import ProjectService
from storage.database import SQLiteDatabase
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
pytestmark = pytest.mark.skipif(
    not FFMPEG or not FFPROBE,
    reason="FFmpeg/FFprobe are not available on this test machine",
)


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, timeout=20, shell=False)


def _tiny_video(path: Path) -> None:
    _run([
        FFMPEG,
        "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=160x90:d=0.5",
        "-c:v", "mpeg4", "-pix_fmt", "yuv420p",
        str(path),
    ])


def _tiny_wav(path: Path) -> None:
    _run([
        FFMPEG,
        "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5",
        "-c:a", "pcm_s16le",
        str(path),
    ])


def test_real_ffprobe_and_video_thumbnail(tmp_path: Path):
    video = tmp_path / "tiny.mp4"
    _tiny_video(video)
    prober = FFprobeService(lambda: FFPROBE)
    result = prober.probe(video, "video")
    assert result.duration_ms is not None and result.duration_ms > 0
    assert result.width == 160
    assert result.height == 90
    assert result.codec

    thumbnail = tmp_path / "thumb.jpg"
    ThumbnailService(lambda: FFMPEG, max_width=320).generate_video_thumbnail(
        video, thumbnail, duration_ms=result.duration_ms
    )
    assert thumbnail.is_file() and thumbnail.stat().st_size > 0


def test_real_media_service_imports_mp4_and_wav(tmp_path: Path):
    video = tmp_path / "tiny.mp4"
    audio = tmp_path / "tiny.wav"
    _tiny_video(video)
    _tiny_wav(audio)

    database = SQLiteDatabase(tmp_path / "runtime" / "app.db")
    database.initialize()
    project_repo = ProjectRepository(database)
    media_repo = MediaRepository(database)
    project_service = ProjectService(project_repo, tmp_path / "projects")
    media_service = MediaService(
        media_repo,
        project_repo,
        FFprobeService(lambda: FFPROBE),
        ThumbnailService(lambda: FFMPEG),
    )
    project_service.set_media_service(media_service)
    project = project_service.create_project("Integration", "video", "en", "16:9", 30)

    video_asset = media_service.import_file(project.project_id, video)
    audio_asset = media_service.import_file(project.project_id, audio)

    assert Path(video_asset.project_path).is_file()
    assert video_asset.thumbnail_path and Path(video_asset.thumbnail_path).is_file()
    assert video_asset.width == 160 and video_asset.height == 90
    assert Path(audio_asset.project_path).is_file()
    assert audio_asset.audio_codec
    assert audio_asset.thumbnail_path is None
    assert len(media_repo.list_by_project(project.project_id)) == 2

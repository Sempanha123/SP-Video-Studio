from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from domain.media import MediaAsset, MediaStatus
from media.file_classifier import FileClassifier
from media.media_importer import InsufficientDiskSpaceError, MediaImporter
from media.probe import (
    FFprobeService,
    FFprobeUnavailableError,
    InvalidMediaError,
    MediaProbeResult,
    MediaProbeTimeoutError,
    parse_duration_ms,
    parse_rational_fps,
)
from media.thumbnails import ThumbnailService
from services.media_service import (
    MediaImportError,
    MediaService,
    UnsafeMediaPathError,
    UnsupportedMediaError,
)
from services.project_service import ProjectService
from storage.database import SQLiteDatabase
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository


class FakeProber:
    def __init__(self, result: MediaProbeResult | None = None, error: Exception | None = None):
        self.result = result or MediaProbeResult(duration_ms=1500)
        self.error = error
        self.calls: list[tuple[Path, str | None]] = []

    def probe(self, path: str | Path, expected_type: str | None = None) -> MediaProbeResult:
        self.calls.append((Path(path), expected_type))
        if self.error:
            raise self.error
        return self.result


class FakeThumbnails:
    def __init__(self, fail: bool = False):
        self.fail = fail

    def generate(self, media_type, source, destination, *, duration_ms=None):
        if self.fail:
            from media.thumbnails import ThumbnailError

            raise ThumbnailError("thumbnail failed")
        if media_type == "audio":
            return None
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"thumb")
        return path


@pytest.fixture
def media_system(tmp_path: Path):
    database = SQLiteDatabase(tmp_path / "runtime" / "app.db")
    database.initialize()
    project_repository = ProjectRepository(database)
    media_repository = MediaRepository(database)
    project_service = ProjectService(project_repository, tmp_path / "projects")
    prober = FakeProber()
    thumbnails = FakeThumbnails()
    service = MediaService(media_repository, project_repository, prober, thumbnails)
    project_service.set_media_service(service)
    project = project_service.create_project("Media Test", "video", "en", "16:9", 30)
    return database, project_repository, media_repository, project_service, service, project, tmp_path


def make_png(path: Path, size=(96, 54)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, "navy").save(path, format="PNG")
    return path


def test_media_model_serialization_round_trip(media_system):
    _, _, repository, _, _, project, _ = media_system
    asset = MediaAsset(
        project_id=project.project_id,
        media_type="video",
        name="demo.mp4",
        original_path="C:/source/demo.mp4",
        project_path=str(Path(project.project_path) / "media" / "video" / "a.mp4"),
        file_size=123,
        duration_ms=1000,
        width=1920,
        height=1080,
        fps=29.97,
        metadata_json={"rotation": 90, "unicode": "ព័ត៌មាន"},
    )
    repository.create(asset)
    loaded = repository.get_by_id(asset.asset_id)
    assert loaded is not None
    assert loaded.to_dict()["id"] == asset.asset_id
    assert loaded.metadata_json["unicode"] == "ព័ត៌មាន"
    assert loaded.fps == pytest.approx(29.97)


def test_media_migration_schema_and_foreign_key(tmp_path: Path):
    database = SQLiteDatabase(tmp_path / "app.db")
    database.initialize()
    assert database.current_version() == 15
    with database.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(media_assets)")}
        foreign_keys = connection.execute("PRAGMA foreign_key_list(media_assets)").fetchall()
    assert {"id", "project_id", "type", "project_path", "metadata_json"} <= columns
    assert any(row["table"] == "projects" and row["on_delete"] == "CASCADE" for row in foreign_keys)


def test_file_classifier_common_formats():
    classifier = FileClassifier()
    assert classifier.classify("clip.MP4") == "video"
    assert classifier.classify("voice.wav") == "audio"
    assert classifier.classify("logo.webp") == "image"
    assert classifier.classify("notes.txt") is None


def test_rational_fps_and_duration_parsing():
    assert parse_rational_fps("30000/1001") == pytest.approx(29.97002997)
    assert parse_rational_fps("60/1") == 60
    assert parse_rational_fps("0/0") is None
    assert parse_duration_ms("2.345") == 2345
    assert parse_duration_ms("N/A") is None


def test_ffprobe_json_parsing_extracts_video_audio_and_rotation():
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1080,
                "height": 1920,
                "avg_frame_rate": "30000/1001",
                "tags": {"rotate": "90"},
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
            },
        ],
        "format": {"duration": "3.5", "format_name": "mov,mp4", "bit_rate": "800000"},
    }
    result = FFprobeService.parse_payload(payload, expected_type="video")
    assert result.duration_ms == 3500
    assert (result.width, result.height) == (1080, 1920)
    assert result.fps == pytest.approx(29.97, rel=1e-3)
    assert result.codec == "h264"
    assert result.audio_codec == "aac"
    assert result.sample_rate == 48000
    assert result.channels == 2
    assert result.rotation == 90


def test_ffprobe_rejects_wrong_stream_type():
    payload = {"streams": [{"codec_type": "audio", "codec_name": "aac"}], "format": {}}
    with pytest.raises(InvalidMediaError):
        FFprobeService.parse_payload(payload, expected_type="video")


def test_ffprobe_missing_and_timeout(tmp_path: Path):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"x")
    missing = FFprobeService(lambda: None)
    with pytest.raises(FFprobeUnavailableError):
        missing.probe(source, "video")

    def timeout_runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], timeout=1)

    timed = FFprobeService(lambda: "ffprobe", runner=timeout_runner, timeout_seconds=1)
    with pytest.raises(MediaProbeTimeoutError):
        timed.probe(source, "video")


def test_import_image_copies_and_preserves_original(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "sources" / "photo.png", (120, 80))
    original_bytes = source.read_bytes()

    asset = service.import_file(project.project_id, source)

    assert asset.type == "image"
    assert asset.width == 120 and asset.height == 80
    assert Path(asset.project_path).is_file()
    assert Path(asset.project_path) != source
    assert Path(asset.thumbnail_path).is_file()
    assert source.read_bytes() == original_bytes
    assert repository.get_by_id(asset.asset_id) is not None


def test_import_video_and_audio_use_probe_metadata(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    service.prober.result = MediaProbeResult(
        duration_ms=2500,
        width=1920,
        height=1080,
        fps=30.0,
        codec="h264",
        audio_codec="aac",
        sample_rate=48000,
        channels=2,
    )
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.wav"
    video.write_bytes(b"fake-video")
    audio.write_bytes(b"fake-audio")

    video_asset = service.import_file(project.project_id, video)
    service.prober.result = MediaProbeResult(
        duration_ms=900, audio_codec="pcm_s16le", sample_rate=44100, channels=1
    )
    audio_asset = service.import_file(project.project_id, audio)

    assert video_asset.codec == "h264"
    assert video_asset.fps == 30
    assert Path(video_asset.thumbnail_path).exists()
    assert audio_asset.audio_codec == "pcm_s16le"
    assert audio_asset.thumbnail_path is None
    assert len(repository.list_by_project(project.project_id)) == 2


def test_unicode_and_khmer_filename_are_preserved(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "sources" / "ព័ត៌មានថ្មី.png")
    asset = service.import_file(project.project_id, source)
    loaded = repository.get_by_id(asset.asset_id)
    assert asset.name == "ព័ត៌មានថ្មី.png"
    assert loaded is not None and loaded.name == "ព័ត៌មានថ្មី.png"
    assert Path(asset.project_path).name != source.name


def test_duplicate_source_import_creates_independent_collision_safe_copies(media_system):
    _, _, _, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "same.png")
    first = service.import_file(project.project_id, source)
    second = service.import_file(project.project_id, source)
    assert first.asset_id != second.asset_id
    assert first.project_path != second.project_path
    assert Path(first.project_path).exists() and Path(second.project_path).exists()


def test_unsupported_extension_does_not_create_record_or_copy(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    source = tmp_path / "notes.xyz"
    source.write_text("hello", encoding="utf-8")
    with pytest.raises(UnsupportedMediaError):
        service.import_file(project.project_id, source)
    assert repository.count_for_project(project.project_id) == 0
    assert list((Path(project.project_path) / "media").iterdir()) == []


def test_invalid_video_rolls_back_project_copy(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    service.prober.error = InvalidMediaError("corrupt")
    source = tmp_path / "broken.mp4"
    source.write_bytes(b"not video")
    with pytest.raises(MediaImportError):
        service.import_file(project.project_id, source)
    assert repository.count_for_project(project.project_id) == 0
    video_dir = Path(project.project_path) / "media" / "video"
    assert not video_dir.exists() or list(video_dir.iterdir()) == []


def test_missing_ffprobe_rolls_back_copy(media_system, tmp_path: Path):
    _, project_repo, media_repo, _, _, project, _ = media_system
    source = tmp_path / "missing-probe.mp4"
    source.write_bytes(b"fake")
    real_prober = FFprobeService(lambda: None)
    service = MediaService(media_repo, project_repo, real_prober, FakeThumbnails())
    with pytest.raises(MediaImportError):
        service.import_file(project.project_id, source)
    assert media_repo.count_for_project(project.project_id) == 0
    assert not any((Path(project.project_path) / "media" / "video").glob("*.mp4"))


def test_thumbnail_failure_does_not_fail_valid_import(media_system):
    _, project_repo, media_repo, _, service, project, tmp_path = media_system
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"valid enough for fake probe")
    failing = MediaService(media_repo, project_repo, service.prober, FakeThumbnails(fail=True))
    asset = failing.import_file(project.project_id, source)
    assert asset.status == MediaStatus.READY
    assert asset.thumbnail_path is None
    assert Path(asset.project_path).exists()


def test_video_thumbnail_command_uses_safe_argument_list():
    command = ThumbnailService.build_video_thumbnail_command(
        "C:/ffmpeg.exe",
        "C:/Media/a video.mp4",
        "C:/Project/thumb.jpg",
        duration_ms=100_000,
        max_width=480,
    )
    assert command[0] == "C:/ffmpeg.exe"
    assert command[command.index("-ss") + 1] == "10.000"
    assert "C:/Media/a video.mp4" in command
    assert "-vf" in command


def test_image_thumbnail_generation(tmp_path: Path):
    source = make_png(tmp_path / "large.png", (1200, 600))
    output = tmp_path / "thumb.jpg"
    thumbnails = ThumbnailService(lambda: None, max_width=320)
    result = thumbnails.generate_image_thumbnail(source, output)
    assert result == output and output.is_file()
    with Image.open(output) as image:
        assert image.width <= 320
        assert image.height <= 320


def test_remove_media_deletes_project_copy_but_never_original(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "original.png")
    original = source.read_bytes()
    asset = service.import_file(project.project_id, source)
    managed = Path(asset.project_path)
    thumb = Path(asset.thumbnail_path)

    service.remove_media(project.project_id, asset.asset_id)

    assert source.exists() and source.read_bytes() == original
    assert not managed.exists()
    assert not thumb.exists()
    assert repository.get_by_id(asset.asset_id) is None


def test_safe_delete_guard_rejects_database_path_escape(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "source.png")
    asset = service.import_file(project.project_id, source)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"must survive")
    asset.project_path = str(outside)
    repository.update(asset)

    with pytest.raises(UnsafeMediaPathError):
        service.remove_media(project.project_id, asset.asset_id)
    assert outside.read_bytes() == b"must survive"
    assert source.exists()
    assert repository.get_by_id(asset.asset_id) is not None


def test_missing_media_detection_and_remove_reference(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "gone.png")
    asset = service.import_file(project.project_id, source)
    Path(asset.project_path).unlink()
    assert service.refresh_missing(project.project_id) == 1
    missing = repository.get_by_id(asset.asset_id)
    assert missing is not None and str(missing.status) == "missing"
    service.remove_media(project.project_id, asset.asset_id)
    assert repository.get_by_id(asset.asset_id) is None
    assert source.exists()


def test_search_filter_and_sort_combine(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    for name in ("logo-main.png", "logo-alt.png", "photo.png"):
        service.import_file(project.project_id, make_png(tmp_path / name))
    audio = tmp_path / "logo-voice.wav"
    audio.write_bytes(b"audio")
    service.import_file(project.project_id, audio)

    images = service.list_media(project.project_id, search="logo", media_type="image", sort="name")
    assert [item.name for item in images] == ["logo-alt.png", "logo-main.png"]
    audio_results = service.list_media(project.project_id, media_type="audio")
    assert [item.name for item in audio_results] == ["logo-voice.wav"]
    assert len(repository.list_by_project(project.project_id)) == 4


def test_import_rolls_back_when_database_insert_fails(media_system, monkeypatch):
    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "rollback.png")

    def fail_create(asset):
        raise RuntimeError("db failed")

    monkeypatch.setattr(repository, "create", fail_create)
    with pytest.raises(MediaImportError):
        service.import_file(project.project_id, source)
    image_dir = Path(project.project_path) / "media" / "images"
    assert not image_dir.exists() or list(image_dir.iterdir()) == []
    assert list((Path(project.project_path) / "thumbnails").iterdir()) == []
    assert source.exists()


def test_low_disk_space_stops_before_copy(media_system, monkeypatch):
    _, _, repository, _, service, project, tmp_path = media_system
    source = tmp_path / "large.mp4"
    source.write_bytes(b"1234567890")
    monkeypatch.setattr(
        "media.media_importer.shutil.disk_usage",
        lambda _path: shutil._ntuple_diskusage(total=100, used=99, free=1),
    )
    with pytest.raises(InsufficientDiskSpaceError):
        service.import_file(project.project_id, source)
    assert repository.count_for_project(project.project_id) == 0


def test_project_duplication_clones_media_records_and_files_independently(media_system):
    _, _, repository, project_service, service, project, tmp_path = media_system
    source = make_png(tmp_path / "copy-me.png")
    original_asset = service.import_file(project.project_id, source)

    duplicate = project_service.duplicate_project(project.project_id)
    duplicate_assets = repository.list_by_project(duplicate.project_id)

    assert len(duplicate_assets) == 1
    copied = duplicate_assets[0]
    assert copied.asset_id != original_asset.asset_id
    assert Path(copied.project_path).is_file()
    assert Path(copied.project_path).is_relative_to(Path(duplicate.project_path))
    assert Path(original_asset.project_path).is_file()
    Path(copied.project_path).write_bytes(b"changed duplicate")
    assert Path(original_asset.project_path).read_bytes() != b"changed duplicate"
    assert copied.thumbnail_path and Path(copied.thumbnail_path).name.startswith(copied.asset_id)


def test_project_deletion_cascades_media_record_and_preserves_source(media_system):
    _, _, repository, project_service, service, project, tmp_path = media_system
    source = make_png(tmp_path / "source-safe.png")
    source_bytes = source.read_bytes()
    asset = service.import_file(project.project_id, source)

    project_service.delete_project(project.project_id)

    assert repository.get_by_id(asset.asset_id) is None
    assert source.exists() and source.read_bytes() == source_bytes
    assert not Path(project.project_path).exists()


def test_media_restart_persistence(media_system):
    database, _, _, _, service, project, tmp_path = media_system
    asset = service.import_file(project.project_id, make_png(tmp_path / "persist.png"))
    restarted_repository = MediaRepository(SQLiteDatabase(database.path))
    loaded = restarted_repository.list_by_project(project.project_id)
    assert len(loaded) == 1
    assert loaded[0].asset_id == asset.asset_id
    assert loaded[0].name == "persist.png"


def test_multi_file_import_keeps_valid_files_when_one_fails(media_system):
    _, _, repository, _, service, project, tmp_path = media_system
    valid = make_png(tmp_path / "valid.png")
    unsupported = tmp_path / "bad.xyz"
    unsupported.write_text("bad", encoding="utf-8")
    another = make_png(tmp_path / "another.png")
    summary = service.import_many(project.project_id, [valid, unsupported, another])
    assert summary.imported_count == 2
    assert summary.failed_count == 1
    assert summary.failures[0].name == "bad.xyz"
    assert repository.count_for_project(project.project_id) == 2


def test_cancelled_batch_creates_no_new_record(media_system):
    from workers.cancellation import CancellationToken

    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "cancel.png")
    token = CancellationToken()
    token.cancel()
    summary = service.import_many(project.project_id, [source], cancellation=token)
    assert summary.cancelled is True
    assert summary.imported_count == 0
    assert repository.count_for_project(project.project_id) == 0


def test_remove_restores_project_copy_if_database_delete_fails(media_system, monkeypatch):
    _, _, repository, _, service, project, tmp_path = media_system
    source = make_png(tmp_path / "restore.png")
    asset = service.import_file(project.project_id, source)
    managed = Path(asset.project_path)
    thumb = Path(asset.thumbnail_path)

    def fail_delete(_asset_id):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(repository, "delete", fail_delete)
    with pytest.raises(Exception):
        service.remove_media(project.project_id, asset.asset_id)
    assert managed.exists()
    assert thumb.exists()
    assert source.exists()

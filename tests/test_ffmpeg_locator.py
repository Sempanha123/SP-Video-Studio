from pathlib import Path
from subprocess import CompletedProcess

from media.ffmpeg_locator import FFmpegLocator


def test_ffmpeg_missing_without_path():
    locator = FFmpegLocator(which=lambda _: None)
    ffmpeg, ffprobe = locator.discover()
    assert ffmpeg.available is False
    assert ffprobe.available is False


def test_ffmpeg_and_ffprobe_detected(monkeypatch, tmp_path: Path):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffprobe_path = tmp_path / "ffprobe"
    ffmpeg_path.write_text("fake", encoding="utf-8")
    ffprobe_path.write_text("fake", encoding="utf-8")

    def fake_run(args, **kwargs):
        name = Path(args[0]).name
        return CompletedProcess(args, 0, stdout=f"{name} version 7.1 test\n", stderr="")

    monkeypatch.setattr("media.ffmpeg_locator.subprocess.run", fake_run)
    locator = FFmpegLocator(which=lambda name: str(tmp_path / name))
    ffmpeg, ffprobe = locator.discover()
    assert ffmpeg.available is True
    assert ffmpeg.version == "7.1"
    assert ffprobe.available is True
    assert ffprobe.version == "7.1"


def test_custom_ffmpeg_path_is_validated(monkeypatch, tmp_path: Path):
    executable = tmp_path / "renamed-tool"
    executable.write_text("fake", encoding="utf-8")

    def fake_run(args, **kwargs):
        return CompletedProcess(args, 0, stdout="ffmpeg version 6.0\n", stderr="")

    monkeypatch.setattr("media.ffmpeg_locator.subprocess.run", fake_run)
    result = FFmpegLocator().validate_path(executable, "ffmpeg")
    assert result.available is True
    assert result.path == str(executable.resolve())


def test_invalid_ffmpeg_executable_is_rejected(monkeypatch, tmp_path: Path):
    executable = tmp_path / "not-ffmpeg"
    executable.write_text("fake", encoding="utf-8")

    def fake_run(args, **kwargs):
        return CompletedProcess(args, 0, stdout="some other program\n", stderr="")

    monkeypatch.setattr("media.ffmpeg_locator.subprocess.run", fake_run)
    result = FFmpegLocator().validate_path(executable, "ffmpeg")
    assert result.available is False

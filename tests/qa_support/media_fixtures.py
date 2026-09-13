from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FFmpegUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaFixtureSet:
    video: Path
    long_video: Path
    green_screen: Path
    music: Path
    voice_wav: Path
    image: Path
    subtitles: Path


def ffmpeg_path() -> str:
    value = shutil.which("ffmpeg")
    if not value:
        raise FFmpegUnavailable("FFmpeg is not installed or not on PATH.")
    return value


def ffprobe_path() -> str | None:
    return shutil.which("ffprobe")


def run_ffmpeg(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    command = [ffmpeg_path(), "-hide_banner", "-loglevel", "error", *args]
    done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, shell=False)
    if done.returncode != 0:
        raise RuntimeError(f"FFmpeg fixture command failed ({done.returncode}): {done.stderr.strip()[:500]}")
    return done


def _write_ppm(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 96, 64
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels.extend(((x * 3) % 256, (y * 4) % 256, ((x + y) * 2) % 256))
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + bytes(pixels))
    return path


def generate_media_fixtures(root: Path) -> MediaFixtureSet:
    """Generate tiny deterministic release-QA media without committing binaries."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    video = root / "base-video.mp4"
    long_video = root / "shorts-source.mp4"
    green = root / "green-presenter.mp4"
    music = root / "music-stereo.wav"
    voice = root / "voice-mono.wav"
    image = root / "image.ppm"
    subtitles = root / "fixture.srt"

    run_ffmpeg([
        "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=15:duration=2",
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-y", str(video),
    ])
    run_ffmpeg([
        "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=15:duration=5",
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-y", str(long_video),
    ])
    run_ffmpeg([
        "-f", "lavfi", "-i", "color=c=0x00cc44:size=320x180:rate=15:duration=2",
        "-vf", "drawbox=x=120:y=48:w=80:h=110:color=0x3355ff:t=fill,drawbox=x=138:y=18:w=44:h=44:color=0xffccaa:t=fill",
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-y", str(green),
    ])
    run_ffmpeg([
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=16000:duration=2",
        "-filter_complex", "[0:a][1:a]amerge=inputs=2[a]", "-map", "[a]", "-ac", "2", "-y", str(music),
    ])
    run_ffmpeg([
        "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=16000:duration=1.2",
        "-ac", "1", "-y", str(voice),
    ])
    _write_ppm(image)
    subtitles.write_text(
        "1\n00:00:00,000 --> 00:00:01,200\nHello · សួស្តី · สวัสดี · Xin chào\n\n",
        encoding="utf-8",
    )
    return MediaFixtureSet(video, long_video, green, music, voice, image, subtitles)


def validate_mp4(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file() or path.stat().st_size <= 0:
        raise AssertionError(f"Rendered MP4 is missing or empty: {path}")
    probe = ffprobe_path()
    if not probe:
        return {"valid": True, "size": path.stat().st_size, "probe": "unavailable"}
    command = [
        probe, "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=codec_name,width,height", "-of", "default=noprint_wrappers=1", str(path),
    ]
    done = subprocess.run(command, capture_output=True, text=True, timeout=20, shell=False)
    if done.returncode != 0 or "codec_name=" not in done.stdout:
        raise AssertionError(f"ffprobe could not validate {path}: {done.stderr.strip()[:300]}")
    return {"valid": True, "size": path.stat().st_size, "probe": done.stdout.strip()}

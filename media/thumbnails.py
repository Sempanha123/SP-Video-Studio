from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps


class ThumbnailError(RuntimeError):
    pass


class ThumbnailService:
    def __init__(
        self,
        ffmpeg_provider: Callable[[], str | Path | None],
        *,
        timeout_seconds: float = 20.0,
        max_width: int = 480,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._ffmpeg_provider = ffmpeg_provider
        self.timeout_seconds = timeout_seconds
        self.max_width = max(160, int(max_width))
        self._runner = runner

    def generate(
        self,
        media_type: str,
        source: str | Path,
        destination: str | Path,
        *,
        duration_ms: int | None = None,
    ) -> Path | None:
        if media_type == "audio":
            return None
        if media_type == "image":
            return self.generate_image_thumbnail(source, destination)
        if media_type == "video":
            return self.generate_video_thumbnail(source, destination, duration_ms=duration_ms)
        raise ThumbnailError("Unsupported thumbnail media type.")

    def generate_image_thumbnail(self, source: str | Path, destination: str | Path) -> Path:
        source_path = Path(source)
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination_path.with_name(destination_path.name + ".part")
        temporary.unlink(missing_ok=True)
        try:
            with Image.open(source_path) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((self.max_width, self.max_width), Image.Resampling.LANCZOS)
                if image.mode not in {"RGB", "L"}:
                    background = Image.new("RGB", image.size, "white")
                    if "A" in image.getbands():
                        background.paste(image, mask=image.getchannel("A"))
                    else:
                        background.paste(image)
                    image = background
                elif image.mode == "L":
                    image = image.convert("RGB")
                image.save(temporary, format="JPEG", quality=84, optimize=True)
            temporary.replace(destination_path)
            return destination_path
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            destination_path.unlink(missing_ok=True)
            raise ThumbnailError("Image thumbnail could not be generated.") from exc

    def generate_video_thumbnail(
        self,
        source: str | Path,
        destination: str | Path,
        *,
        duration_ms: int | None = None,
    ) -> Path:
        ffmpeg = self._ffmpeg_provider()
        if not ffmpeg:
            raise ThumbnailError("FFmpeg is unavailable for video thumbnails.")
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        command = self.build_video_thumbnail_command(
            ffmpeg, source, destination_path, duration_ms=duration_ms, max_width=self.max_width
        )
        try:
            completed = self._runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            destination_path.unlink(missing_ok=True)
            raise ThumbnailError("Video thumbnail could not be generated.") from exc
        if completed.returncode != 0 or not destination_path.is_file():
            destination_path.unlink(missing_ok=True)
            raise ThumbnailError(
                (completed.stderr or "Video thumbnail could not be generated.").strip()
            )
        return destination_path

    @staticmethod
    def build_video_thumbnail_command(
        ffmpeg: str | Path,
        source: str | Path,
        destination: str | Path,
        *,
        duration_ms: int | None,
        max_width: int = 480,
    ) -> list[str]:
        duration_seconds = max(0.0, (duration_ms or 0) / 1000.0)
        if duration_seconds <= 0.15:
            timestamp = 0.0
        else:
            timestamp = min(duration_seconds * 0.10, max(0.0, duration_seconds - 0.05))
        return [
            str(ffmpeg),
            "-y",
            "-ss", f"{timestamp:.3f}",
            "-i", str(source),
            "-frames:v", "1",
            "-vf", f"scale='min({int(max_width)},iw)':-2",
            "-q:v", "3",
            str(destination),
        ]

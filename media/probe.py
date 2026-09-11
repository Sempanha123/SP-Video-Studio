from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


class MediaProbeError(RuntimeError):
    pass


class FFprobeUnavailableError(MediaProbeError):
    pass


class MediaProbeTimeoutError(MediaProbeError):
    pass


class InvalidMediaError(MediaProbeError):
    pass


@dataclass(slots=True)
class MediaProbeResult:
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec: str | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    container: str | None = None
    bit_rate: int | None = None
    rotation: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def metadata(self) -> dict[str, Any]:
        return {
            "container": self.container,
            "bit_rate": self.bit_rate,
            "rotation": self.rotation,
            "ffprobe": self.raw,
        }


def parse_rational_fps(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"0/0", "N/A"}:
        return None
    try:
        if "/" in text:
            numerator, denominator = text.split("/", 1)
            denominator_value = float(denominator)
            if denominator_value == 0:
                return None
            result = float(numerator) / denominator_value
        else:
            result = float(text)
        return result if result >= 0 else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def parse_duration_ms(value: object) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        seconds = float(str(value))
        if seconds < 0:
            return None
        return int(round(seconds * 1000.0))
    except (TypeError, ValueError):
        return None


class FFprobeService:
    def __init__(
        self,
        executable_provider: Callable[[], str | Path | None],
        *,
        timeout_seconds: float = 15.0,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._executable_provider = executable_provider
        self.timeout_seconds = timeout_seconds
        self._runner = runner

    def probe(self, path: str | Path, expected_type: str | None = None) -> MediaProbeResult:
        source = Path(path)
        executable = self._executable_provider()
        if not executable:
            raise FFprobeUnavailableError(
                "FFprobe is required to inspect video and audio files. Configure it in Settings."
            )
        command = [
            str(executable),
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(source),
        ]
        try:
            completed = self._runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MediaProbeTimeoutError(f"FFprobe timed out while inspecting {source.name}.") from exc
        except OSError as exc:
            raise FFprobeUnavailableError("FFprobe could not be started.") from exc
        except subprocess.SubprocessError as exc:
            raise MediaProbeError("FFprobe could not inspect this media file.") from exc

        if completed.returncode != 0:
            detail = (completed.stderr or "").strip()
            raise InvalidMediaError(detail or "The media file is invalid or unsupported.")
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise InvalidMediaError("FFprobe returned invalid metadata.") from exc
        return self.parse_payload(payload, expected_type=expected_type)

    @staticmethod
    def parse_payload(payload: dict[str, Any], expected_type: str | None = None) -> MediaProbeResult:
        streams = payload.get("streams")
        if not isinstance(streams, list):
            streams = []
        video = next(
            (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"),
            None,
        )
        audio = next(
            (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"),
            None,
        )
        if expected_type == "video" and video is None:
            raise InvalidMediaError("The selected file does not contain a usable video stream.")
        if expected_type == "audio" and audio is None:
            raise InvalidMediaError("The selected file does not contain a usable audio stream.")
        if expected_type in {"video", "audio"} and not streams:
            raise InvalidMediaError("The selected file does not contain readable media streams.")

        format_data = payload.get("format") if isinstance(payload.get("format"), dict) else {}
        duration_value = format_data.get("duration")
        if duration_value in (None, "N/A"):
            primary = video if expected_type == "video" else audio
            if isinstance(primary, dict):
                duration_value = primary.get("duration")

        rotation = FFprobeService._rotation(video)
        sample_rate = FFprobeService._int_or_none(audio.get("sample_rate")) if audio else None
        channels = FFprobeService._int_or_none(audio.get("channels")) if audio else None
        bit_rate = FFprobeService._int_or_none(format_data.get("bit_rate"))
        return MediaProbeResult(
            duration_ms=parse_duration_ms(duration_value),
            width=FFprobeService._int_or_none(video.get("width")) if video else None,
            height=FFprobeService._int_or_none(video.get("height")) if video else None,
            fps=parse_rational_fps(
                video.get("avg_frame_rate") or video.get("r_frame_rate")
            ) if video else None,
            codec=str(video.get("codec_name")) if video and video.get("codec_name") else None,
            audio_codec=str(audio.get("codec_name")) if audio and audio.get("codec_name") else None,
            sample_rate=sample_rate,
            channels=channels,
            container=str(format_data.get("format_name")) if format_data.get("format_name") else None,
            bit_rate=bit_rate,
            rotation=rotation,
            raw=payload,
        )

    @staticmethod
    def _rotation(video: dict[str, Any] | None) -> int | None:
        if not video:
            return None
        tags = video.get("tags")
        if isinstance(tags, dict) and tags.get("rotate") is not None:
            try:
                return int(round(float(tags["rotate"])))
            except (TypeError, ValueError):
                pass
        side_data = video.get("side_data_list")
        if isinstance(side_data, list):
            for item in side_data:
                if isinstance(item, dict) and item.get("rotation") is not None:
                    try:
                        return int(round(float(item["rotation"])))
                    except (TypeError, ValueError):
                        continue
        return None

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        if value in (None, "", "N/A"):
            return None
        try:
            return int(float(str(value)))
        except (TypeError, ValueError):
            return None

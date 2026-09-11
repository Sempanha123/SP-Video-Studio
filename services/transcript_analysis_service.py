from __future__ import annotations

from pathlib import Path

from domain.transcript import source_fingerprint


def seconds_to_ms(seconds: float | int | None) -> int:
    if seconds is None:
        return 0
    return max(0, int(round(float(seconds) * 1000.0)))


def format_timestamp_ms(milliseconds: int) -> str:
    total = max(0, int(milliseconds))
    hours, remainder = divmod(total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


class TranscriptAnalysisService:
    @staticmethod
    def fingerprint(media_id: str, path: Path) -> str:
        stat = path.stat()
        return source_fingerprint(media_id, stat.st_size, stat.st_mtime_ns)

    @staticmethod
    def progress(end_ms: int, duration_ms: int) -> float | None:
        if duration_ms <= 0:
            return None
        return max(0.0, min(1.0, end_ms / duration_ms))

    @staticmethod
    def validate_timestamps(start_ms: int, end_ms: int, *, previous_end_ms: int = 0, duration_ms: int = 0) -> None:
        if start_ms < 0 or end_ms < start_ms:
            raise ValueError("Transcript timestamps are invalid.")
        if start_ms + 250 < previous_end_ms:
            raise ValueError("Transcript segments are not ordered by time.")
        if duration_ms > 0 and end_ms > duration_ms + 2_000:
            raise ValueError("Transcript timestamp exceeds the source duration.")

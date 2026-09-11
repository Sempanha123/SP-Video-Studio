"""Compatibility module for the centralized Phase 4 FFprobe service."""

from .probe import (
    FFprobeService,
    FFprobeUnavailableError,
    InvalidMediaError,
    MediaProbeError,
    MediaProbeResult,
    MediaProbeTimeoutError,
    parse_duration_ms,
    parse_rational_fps,
)

__all__ = [
    "FFprobeService",
    "FFprobeUnavailableError",
    "InvalidMediaError",
    "MediaProbeError",
    "MediaProbeResult",
    "MediaProbeTimeoutError",
    "parse_duration_ms",
    "parse_rational_fps",
]

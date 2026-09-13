from __future__ import annotations

"""Phase 34 accessibility/final UX layer over the completed Phase 33 runtime."""

from app.phase33_runtime import run as run_phase33


def run() -> int:
    return run_phase33()

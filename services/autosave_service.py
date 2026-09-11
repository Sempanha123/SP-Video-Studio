from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AutosavePolicy:
    """Small deterministic debounce state used by controllers and unit tests."""

    delay_seconds: float = 1.5
    touched_at: float | None = None

    @property
    def pending(self) -> bool:
        return self.touched_at is not None

    def touch(self, now: float) -> None:
        self.touched_at = float(now)

    def due(self, now: float) -> bool:
        return self.touched_at is not None and float(now) - self.touched_at >= self.delay_seconds

    def clear(self) -> None:
        self.touched_at = None

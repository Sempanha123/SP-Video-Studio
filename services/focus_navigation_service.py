from __future__ import annotations


class FocusNavigationService:
    """Pure helpers for predictable keyboard row/list movement."""

    @staticmethod
    def next_index(current: int, count: int, direction: int, *, wrap: bool = False) -> int:
        if count <= 0:
            return -1
        if current < 0:
            return 0 if direction >= 0 else count - 1
        target = current + (1 if direction >= 0 else -1)
        if wrap:
            return target % count
        return max(0, min(count - 1, target))

    @staticmethod
    def nearest_index(starts_ms: list[int], playhead_ms: int) -> int:
        if not starts_ms:
            return -1
        return min(range(len(starts_ms)), key=lambda i: abs(int(starts_ms[i]) - int(playhead_ms)))

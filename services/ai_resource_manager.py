from __future__ import annotations

from threading import RLock
from collections.abc import Callable


class AIResourceConflict(RuntimeError):
    pass


class AIResourceManager:
    """Lightweight coordinator for heavy local engines that may compete for VRAM."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._engines: dict[str, tuple[Callable[[], None], Callable[[], bool]]] = {}

    def register(self, engine_id: str, unload: Callable[[], None], busy: Callable[[], bool]) -> None:
        with self._lock:
            self._engines[engine_id] = (unload, busy)

    def prepare(self, engine_id: str, device: str) -> None:
        if not str(device).startswith("cuda"):
            return
        with self._lock:
            for other_id, (unload, busy) in tuple(self._engines.items()):
                if other_id == engine_id:
                    continue
                if busy():
                    raise AIResourceConflict(f"{other_id} is currently using GPU resources.")
                unload()

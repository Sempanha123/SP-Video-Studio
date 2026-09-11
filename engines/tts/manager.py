from __future__ import annotations

from threading import RLock

from engines.tts.base import TTSEngine


class TTSEngineManager:
    """Owns one engine instance per engine ID and serializes model lifecycle calls."""

    def __init__(self) -> None:
        self._engines: dict[str, TTSEngine] = {}
        self._lock = RLock()

    def register(self, engine_id: str, engine: TTSEngine) -> None:
        with self._lock:
            self._engines[engine_id] = engine

    def get(self, engine_id: str) -> TTSEngine:
        with self._lock:
            try:
                return self._engines[engine_id]
            except KeyError as exc:
                raise KeyError(f"Unknown TTS engine: {engine_id}") from exc

    def load(self, engine_id: str, device: str = "auto") -> TTSEngine:
        with self._lock:
            engine = self.get(engine_id)
            if not engine.is_loaded():
                engine.load(device)
            return engine

    def unload(self, engine_id: str) -> None:
        with self._lock:
            self.get(engine_id).unload()

    def unload_all(self) -> None:
        with self._lock:
            for engine in self._engines.values():
                engine.unload()

from __future__ import annotations

from threading import RLock

from engines.stt.base import STTEngine


class STTEngineManager:
    """Owns one main STT engine instance and serializes lifecycle access."""

    def __init__(self, engine: STTEngine) -> None:
        self.engine = engine
        self._lock = RLock()
        self._loaded_key: tuple[str, str, str, bool] | None = None

    def load(self, *, model_path: str, device: str, compute_type: str, batch_mode: bool) -> STTEngine:
        key = (model_path, device, compute_type, bool(batch_mode))
        with self._lock:
            if self.engine.is_loaded() and self._loaded_key == key:
                return self.engine
            if self.engine.is_loaded():
                self.engine.unload()
            self.engine.load(model_path=model_path, device=device, compute_type=compute_type, batch_mode=batch_mode)
            self._loaded_key = key
            return self.engine

    def unload(self) -> None:
        with self._lock:
            if self.engine.is_loaded():
                self.engine.unload()
            self._loaded_key = None

    def close(self) -> None:
        self.unload()

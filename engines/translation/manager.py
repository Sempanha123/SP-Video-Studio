from __future__ import annotations

from engines.translation.base import TranslationEngine
from engines.translation.local_marian_engine import LocalMarianEngine
from engines.translation.manual_engine import ManualTranslationEngine


class TranslationEngineManager:
    def __init__(
        self,
        local_engine: TranslationEngine | None = None,
        manual_engine: TranslationEngine | None = None,
    ) -> None:
        self._engines: dict[str, TranslationEngine] = {
            "local-marian": local_engine or LocalMarianEngine(),
            "manual": manual_engine or ManualTranslationEngine(),
        }

    def get(self, engine_id: str) -> TranslationEngine:
        try:
            return self._engines[engine_id]
        except KeyError as exc:
            raise KeyError(f"Unknown translation engine: {engine_id}") from exc

    def register(self, engine_id: str, engine: TranslationEngine) -> None:
        self._engines[engine_id] = engine

    def providers(self) -> tuple[str, ...]:
        return tuple(self._engines)

    def unload_all(self) -> None:
        for engine in self._engines.values():
            engine.unload()

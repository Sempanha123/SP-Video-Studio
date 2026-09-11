from __future__ import annotations

from abc import abstractmethod

from engines.base import Engine, EngineCapabilities
from engines.translation.types import TranslationCapabilities, TranslationRequest, TranslationResult
from workers.cancellation import CancellationToken


class TranslationEngine(Engine):
    @abstractmethod
    def load(self, *, model_path: str = "", model_id: str = "", device: str = "auto") -> None:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_loaded(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def translate(
        self,
        request: TranslationRequest,
        cancellation: CancellationToken | None = None,
    ) -> TranslationResult:
        raise NotImplementedError

    def translate_batch(
        self,
        requests: list[TranslationRequest],
        cancellation: CancellationToken | None = None,
    ) -> list[TranslationResult]:
        return [self.translate(request, cancellation) for request in requests]

    @abstractmethod
    def supports_language_pair(self, source: str, target: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_supported_language_pairs(self) -> tuple[tuple[str, str], ...]:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> TranslationCapabilities:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: TranslationRequest) -> None:
        raise NotImplementedError

    def health_check(self) -> dict[str, object]:
        return {"available": self.is_available(), "loaded": self.is_loaded()}

    def capabilities(self) -> EngineCapabilities:
        caps = self.get_capabilities()
        features = {"translation"}
        if caps.supports_batch:
            features.add("batch")
        if caps.supports_context:
            features.add("context")
        if caps.supports_offline:
            features.add("offline")
        return EngineCapabilities(name=self.__class__.__name__, features=features)

    def close(self) -> None:
        self.unload()

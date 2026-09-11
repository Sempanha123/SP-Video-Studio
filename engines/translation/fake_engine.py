from __future__ import annotations

from engines.translation.base import TranslationEngine
from engines.translation.errors import TranslationCancelled
from engines.translation.types import TranslationCapabilities, TranslationRequest, TranslationResult
from workers.cancellation import CancellationToken


class FakeTranslationEngine(TranslationEngine):
    """Deterministic test engine. Production selection never points here."""

    ENGINE_ID = "fake"

    def __init__(self) -> None:
        self._loaded = False
        self._model_id = "fake-en-km"

    def load(self, *, model_path: str = "", model_id: str = "", device: str = "auto") -> None:
        self._loaded = True
        self._model_id = model_id or self._model_id

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def translate(
        self,
        request: TranslationRequest,
        cancellation: CancellationToken | None = None,
    ) -> TranslationResult:
        self.validate_request(request)
        if cancellation is not None and cancellation.is_cancelled:
            raise TranslationCancelled()
        prefix = "ខ្មែរ:" if request.target_language == "km" else "English:"
        return TranslationResult(text=f"{prefix} {request.text}", model_id=self._model_id, provider_version="fake-1")

    def supports_language_pair(self, source: str, target: str) -> bool:
        return (source, target) in self.get_supported_language_pairs()

    def get_supported_language_pairs(self) -> tuple[tuple[str, str], ...]:
        return (("en", "km"), ("km", "en"))

    def get_capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities(supports_batch=True, supports_context=True, supports_glossary=True)

    def validate_request(self, request: TranslationRequest) -> None:
        request.validate()

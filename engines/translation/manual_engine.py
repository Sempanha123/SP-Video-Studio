from __future__ import annotations

from engines.translation.base import TranslationEngine
from engines.translation.types import TranslationCapabilities, TranslationRequest, TranslationResult
from workers.cancellation import CancellationToken


class ManualTranslationEngine(TranslationEngine):
    ENGINE_ID = "manual"

    def load(self, *, model_path: str = "", model_id: str = "", device: str = "auto") -> None:
        return None

    def unload(self) -> None:
        return None

    def is_loaded(self) -> bool:
        return True

    def translate(
        self,
        request: TranslationRequest,
        cancellation: CancellationToken | None = None,
    ) -> TranslationResult:
        self.validate_request(request)
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        return TranslationResult(text="", model_id="manual")

    def supports_language_pair(self, source: str, target: str) -> bool:
        return source in {"en", "km"} and target in {"en", "km"} and source != target

    def get_supported_language_pairs(self) -> tuple[tuple[str, str], ...]:
        return (("en", "km"), ("km", "en"))

    def get_capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities(supports_cpu=True, supports_cuda=False, supports_offline=True)

    def validate_request(self, request: TranslationRequest) -> None:
        request.validate()

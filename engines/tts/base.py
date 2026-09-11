from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from engines.base import Engine, EngineCapabilities
from engines.tts.types import TTSCapabilities, TTSRequest, TTSResult
from workers.cancellation import CancellationToken


class TTSEngine(Engine):
    @abstractmethod
    def load(self, device: str = "auto") -> None:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_loaded(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: TTSRequest, cancellation: CancellationToken | None = None) -> TTSResult:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> TTSCapabilities:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: TTSRequest) -> None:
        raise NotImplementedError

    def health_check(self) -> bool:
        return self.is_available()

    def synthesize(self, text: str, output: Path, **options: object) -> Path:
        request = TTSRequest(
            project_id=str(options.pop("project_id", "standalone")),
            text=text,
            language=str(options.pop("language", "en")),
            output_path=output,
        )
        self.generate(request)
        return output

    def capabilities(self) -> EngineCapabilities:
        caps = self.get_capabilities()
        features = {"tts"}
        if caps.supports_voice_design:
            features.add("voice_design")
        if caps.supports_reference_voice:
            features.add("reference_voice")
        return EngineCapabilities(name=self.__class__.__name__, features=features)

    def close(self) -> None:
        self.unload()

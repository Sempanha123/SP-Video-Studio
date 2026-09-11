from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from domain.language import supported_language_codes
from engines.translation.errors import TranslationInvalidRequest


@dataclass(frozen=True, slots=True)
class TranslationCapabilities:
    supports_batch: bool = False
    supports_context: bool = False
    supports_glossary: bool = False
    supports_cpu: bool = True
    supports_cuda: bool = False
    supports_offline: bool = True
    supports_language_detection: bool = False
    supports_formality: bool = False
    supports_domain_prompt: bool = False
    supports_custom_instructions: bool = False
    requires_network: bool = False
    requires_credentials: bool = False


@dataclass(slots=True)
class TranslationRequest:
    project_id: str
    source_language: str
    target_language: str
    text: str
    engine_id: str = "local-marian"
    model_id: str = ""
    device: str = "auto"
    context: str = ""
    segment_id: str = ""
    transcript_id: str = ""
    script_section_id: str = ""
    keep_terms: tuple[str, ...] = ()
    settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid4()))

    def validate(self) -> None:
        supported = set(supported_language_codes())
        if self.source_language not in supported or self.target_language not in supported:
            raise TranslationInvalidRequest("Unsupported source or target language.")
        if self.source_language == self.target_language:
            raise TranslationInvalidRequest("Source and target languages must differ.")
        if not self.text.strip():
            raise TranslationInvalidRequest("Translation text cannot be empty.")
        if self.device not in {"auto", "cpu", "cuda"}:
            raise TranslationInvalidRequest("Device must be Auto, CPU, or CUDA.")
        if not self.engine_id:
            raise TranslationInvalidRequest("Translation engine is required.")


@dataclass(frozen=True, slots=True)
class TranslationResult:
    text: str
    model_id: str = ""
    provider_version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class NewsClaimCandidate:
    text: str
    claim_type: str
    evidence_text: str
    start_offset: int = -1
    end_offset: int = -1
    metadata: dict[str, object] = field(default_factory=dict)


class NewsClaimExtractionProvider(ABC):
    provider_id = "base"
    requires_network = False

    @abstractmethod
    def extract_claims(self, source_text: str) -> list[NewsClaimCandidate]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class NewsScriptDraft:
    sections: tuple[tuple[str, str, tuple[str, ...]], ...]


class NewsScriptProvider(ABC):
    provider_id = "base"
    requires_network = False

    @abstractmethod
    def generate_news_script(self, *, approved_claims: list[dict[str, object]], brief: dict[str, object] | None,
                             style: str, duration_ms: int, language: str) -> NewsScriptDraft:
        raise NotImplementedError

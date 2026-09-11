from __future__ import annotations
from engines.news.base import NewsClaimCandidate, NewsClaimExtractionProvider
from engines.news.deterministic import DeterministicNewsExtractor

class NewsExtractionService:
    def __init__(self, provider:NewsClaimExtractionProvider|None=None)->None:
        self.provider=provider or DeterministicNewsExtractor()
    def candidate_claims(self,text:str)->list[NewsClaimCandidate]:
        return self.provider.extract_claims(text)

from __future__ import annotations
import re
from .base import NewsClaimCandidate, NewsClaimExtractionProvider, NewsScriptDraft, NewsScriptProvider

_SENTENCE_RE = re.compile(r"[^.!?។!?\n]+(?:[.!?។!?]|$)", re.UNICODE)
_QUOTE_RE = re.compile(r'["“”](.{3,240}?)["“”]')
_DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?)\b", re.I)
_NUMBER_RE = re.compile(r"(?<!\w)(?:[$€£]?\d[\d,.]*(?:\s?%|\s?(?:million|billion|thousand|km|kg|USD|KHR))?)(?!\w)", re.I)


class DeterministicNewsExtractor(NewsClaimExtractionProvider):
    provider_id = "deterministic-news-extractor"

    def extract_claims(self, source_text: str) -> list[NewsClaimCandidate]:
        out: list[NewsClaimCandidate] = []
        seen: set[str] = set()
        for match in _SENTENCE_RE.finditer(source_text or ""):
            sentence = match.group(0).strip()
            if len(sentence) < 5:
                continue
            claim_type = "fact"
            quote = _QUOTE_RE.search(sentence)
            if quote:
                claim_type = "quote"
            elif _DATE_RE.search(sentence):
                claim_type = "date"
            elif _NUMBER_RE.search(sentence):
                claim_type = "number"
            else:
                continue
            key = " ".join(sentence.casefold().split())
            if key in seen:
                continue
            seen.add(key)
            out.append(NewsClaimCandidate(sentence, claim_type, sentence, match.start(), match.end()))
        return out


class DeterministicNewsScriptProvider(NewsScriptProvider):
    provider_id = "deterministic-news-script"

    def generate_news_script(self, *, approved_claims: list[dict[str, object]], brief: dict[str, object] | None,
                             style: str, duration_ms: int, language: str) -> NewsScriptDraft:
        claims = [c for c in approved_claims if str(c.get("text", "")).strip()]
        if not claims:
            return NewsScriptDraft(tuple())
        buckets = [claims[:1], claims[1:max(2, len(claims)-1)], claims[max(2, len(claims)-1):]]
        if style == "short_update":
            titles = ("Hook / Lead", "Main Story", "Outro")
        elif style == "explainer":
            titles = ("What Happened", "Background", "Why It Matters")
        elif style == "documentary_news":
            titles = ("Lead", "Background", "What Happens Next")
        else:
            titles = ("Hook / Lead", "Main Story", "Background")
        sections=[]
        for title, group in zip(titles, buckets):
            if not group:
                continue
            text="\n\n".join(str(c["text"]).strip() for c in group)
            ids=tuple(str(c["id"]) for c in group)
            sections.append((title,text,ids))
        return NewsScriptDraft(tuple(sections))

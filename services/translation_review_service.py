from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


_PLACEHOLDER_RE = re.compile(
    r"\{\{[^{}]+\}\}|\{[^{}]+\}|%\d+|https?://[^\s]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
    re.UNICODE,
)
_NUMBER_RE = re.compile(r"(?<!\w)(?:[$€£¥₩₹៛]?\d[\d,]*(?:\.\d+)?(?:\s?(?:%|GHz|MHz|GB|MB|KB|USD|KHR))?)(?!\w)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ProtectedText:
    text: str
    replacements: tuple[tuple[str, str], ...]


class TranslationReviewService:
    def protect(self, text: str, keep_terms: Iterable[str] = ()) -> ProtectedText:
        replacements: list[tuple[str, str]] = []
        protected = text
        values = [match.group(0) for match in _PLACEHOLDER_RE.finditer(text)]
        for term in keep_terms:
            clean = str(term).strip()
            if clean and clean in text and clean not in values:
                values.append(clean)
        # Longest first prevents a shorter keep-term from corrupting a longer one.
        for value in sorted(values, key=len, reverse=True):
            marker = f"__SPVS_KEEP_{len(replacements):03d}__"
            if value in protected:
                protected = protected.replace(value, marker)
                replacements.append((marker, value))
        return ProtectedText(protected, tuple(replacements))

    @staticmethod
    def restore(text: str, protected: ProtectedText) -> tuple[str, tuple[str, ...]]:
        result = text
        missing: list[str] = []
        for marker, value in protected.replacements:
            if marker not in result:
                missing.append(value)
                continue
            result = result.replace(marker, value)
        return result, tuple(missing)

    def quality_warnings(
        self,
        source: str,
        target: str,
        *,
        missing_protected: Iterable[str] = (),
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        source_clean = source.strip()
        target_clean = target.strip()
        if not target_clean:
            warnings.append("Empty translation output")
            return tuple(warnings)
        if len(source_clean) >= 32 and source_clean == target_clean:
            warnings.append("Translation matches source text")
        missing_values = [item for item in missing_protected if item]
        if missing_values:
            warnings.append("One or more protected terms/placeholders changed")
        source_numbers = self._normalized_numbers(source_clean)
        target_numbers = self._normalized_numbers(target_clean)
        if source_numbers - target_numbers:
            warnings.append("One or more numbers may be missing")
        source_len = max(1, len(source_clean))
        ratio = len(target_clean) / source_len
        if source_len >= 24 and (ratio < 0.15 or ratio > 5.5):
            warnings.append("Translation length is unusually different from the source")
        if any(token in target_clean for token in ("<pad>", "</s>", "<unk>")):
            warnings.append("Translation contains model control tokens")
        return tuple(warnings)

    @staticmethod
    def _normalized_numbers(text: str) -> set[str]:
        return {re.sub(r"\s+", "", match.group(0)).lower() for match in _NUMBER_RE.finditer(text)}

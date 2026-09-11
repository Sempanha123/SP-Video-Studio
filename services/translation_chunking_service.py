from __future__ import annotations

import re


class TranslationChunkingService:
    """Lossless paragraph/sentence chunking for local translation model limits."""

    def __init__(self, default_max_chars: int = 900) -> None:
        self.default_max_chars = max(200, int(default_max_chars))

    def chunk(self, text: str, language: str, max_chars: int | None = None) -> list[str]:
        limit = max(100, int(max_chars or self.default_max_chars))
        if not text:
            return []
        if len(text) <= limit:
            return [text]
        paragraphs = re.split(r"(\n{2,})", text)
        chunks: list[str] = []
        buffer = ""
        for part in paragraphs:
            if not part:
                continue
            if len(buffer) + len(part) <= limit:
                buffer += part
                continue
            if buffer:
                chunks.append(buffer)
                buffer = ""
            if len(part) <= limit:
                buffer = part
                continue
            for sentence in self._split_sentences(part, language):
                if len(sentence) <= limit:
                    if buffer and len(buffer) + len(sentence) > limit:
                        chunks.append(buffer)
                        buffer = ""
                    buffer += sentence
                    continue
                # Last-resort whitespace boundary splitting. Never slices bytes and never drops text.
                units = re.split(r"(\s+)", sentence)
                for unit in units:
                    if buffer and len(buffer) + len(unit) > limit:
                        chunks.append(buffer)
                        buffer = ""
                    if len(unit) > limit:
                        # Long token/no-space Khmer text: character slicing is Unicode-codepoint safe in Python.
                        while len(unit) > limit:
                            chunks.append(unit[:limit])
                            unit = unit[limit:]
                    buffer += unit
        if buffer:
            chunks.append(buffer)
        return chunks

    @staticmethod
    def _split_sentences(text: str, language: str) -> list[str]:
        punctuation = r"(?<=[.!?។៕])" if language == "km" else r"(?<=[.!?])"
        parts = re.split(f"({punctuation}\\s*)", text)
        if len(parts) <= 1:
            return [text]
        result: list[str] = []
        current = ""
        for part in parts:
            current += part
            if re.search(r"[.!?។៕]\s*$", current):
                result.append(current)
                current = ""
        if current:
            result.append(current)
        return result or [text]

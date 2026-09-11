from __future__ import annotations

import re

from domain.narration import TTSChunk
from domain.script_section import ScriptSection


class TTSChunkingService:
    """Paragraph/sentence-aware chunking for narration without heavyweight NLP dependencies."""

    def __init__(self, max_characters: int = 700) -> None:
        self.max_characters = max(120, int(max_characters))

    def chunk_text(self, text: str, language: str, section_id: str | None = None) -> list[TTSChunk]:
        clean = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not clean:
            return []
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", clean) if part.strip()]
        pieces: list[str] = []
        for paragraph in paragraphs:
            pieces.extend(self._split_paragraph(paragraph, language))
        chunks: list[TTSChunk] = []
        buffer = ""
        for piece in pieces:
            candidate = piece if not buffer else f"{buffer} {piece}"
            if len(candidate) <= self.max_characters:
                buffer = candidate
                continue
            if buffer:
                chunks.append(TTSChunk(buffer, len(chunks), section_id=section_id))
            if len(piece) <= self.max_characters:
                buffer = piece
            else:
                for sub in self._hard_wrap(piece):
                    if len(sub) == self.max_characters:
                        chunks.append(TTSChunk(sub, len(chunks), section_id=section_id))
                    else:
                        buffer = sub
        if buffer:
            chunks.append(TTSChunk(buffer, len(chunks), section_id=section_id))
        return chunks

    def chunk_sections(self, sections: list[ScriptSection], language: str) -> list[TTSChunk]:
        chunks: list[TTSChunk] = []
        for section in sorted((s for s in sections if s.enabled and s.content.strip()), key=lambda item: item.order):
            local = self.chunk_text(section.content, language, section.section_id)
            for item in local:
                item.order = len(chunks)
                item.metadata["sectionTitle"] = section.title
                chunks.append(item)
        return chunks

    def _split_paragraph(self, paragraph: str, language: str) -> list[str]:
        # Khmer uses ។ as a common sentence terminator; Latin punctuation is retained too.
        pattern = r"(?<=[។!?])\s*" if language == "km" else r"(?<=[.!?])\s+"
        parts = [part.strip() for part in re.split(pattern, paragraph) if part.strip()]
        return parts or [paragraph]

    def _hard_wrap(self, text: str) -> list[str]:
        result: list[str] = []
        remaining = text
        while len(remaining) > self.max_characters:
            cut = remaining.rfind(" ", 0, self.max_characters + 1)
            if cut < self.max_characters // 2:
                cut = self.max_characters
            result.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()
        if remaining:
            result.append(remaining)
        return result

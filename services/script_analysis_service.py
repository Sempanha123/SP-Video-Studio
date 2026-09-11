from __future__ import annotations

import math
import re
from dataclasses import dataclass

from domain.script import ScriptPace
from domain.script_section import ScriptSection

ENGLISH_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?")
PACE_WPM = {ScriptPace.SLOW.value: 125, ScriptPace.NORMAL.value: 150, ScriptPace.FAST.value: 180}
KHMER_CHARS_PER_MINUTE = {ScriptPace.SLOW.value: 360, ScriptPace.NORMAL.value: 450, ScriptPace.FAST.value: 540}


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    word_count: int
    character_count: int
    estimated_speech_units: int
    estimated_duration_ms: int
    metric_label: str
    metric_value: int


class ScriptAnalysisService:
    def analyze_text(self, text: str, language: str, pace: str = "normal") -> AnalysisResult:
        text = text or ""
        characters = sum(1 for ch in text if not ch.isspace())
        words = len(ENGLISH_WORD_RE.findall(text))
        if language == "km":
            rate = KHMER_CHARS_PER_MINUTE.get(pace, KHMER_CHARS_PER_MINUTE["normal"])
            duration_ms = round((characters / rate) * 60_000) if characters else 0
            return AnalysisResult(words, characters, characters, duration_ms, "characters", characters)
        rate = PACE_WPM.get(pace, PACE_WPM["normal"])
        duration_ms = round((words / rate) * 60_000) if words else 0
        return AnalysisResult(words, characters, words, duration_ms, "words", words)

    def analyze_sections(self, sections: list[ScriptSection], language: str, pace: str = "normal") -> AnalysisResult:
        text = "\n\n".join(section.content for section in sections if section.enabled and section.content)
        return self.analyze_text(text, language, pace)

    @staticmethod
    def format_duration(duration_ms: int) -> str:
        seconds = max(0, math.ceil(duration_ms / 1000))
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"~{hours}:{minutes:02d}:{secs:02d}"
        if minutes:
            return f"~{minutes}:{secs:02d}"
        return f"~{secs} sec"

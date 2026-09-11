from __future__ import annotations

import importlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from domain.language import LanguageInfo, language_info, search_languages, supported_language_codes

# Verified against the official openbmb/VoxCPM2 model card (30 languages).
VOXCPM2_LANGUAGE_CODES = frozenset({
    "ar","my","zh","da","nl","en","fi","fr","de","el","he","hi","id","it","ja","km","ko","lo",
    "ms","no","pl","pt","ru","es","sw","sv","tl","th","tr","vi",
})


class LanguageSupportState(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    MODEL_REQUIRED = "model_required"
    UNSUPPORTED_BY_SELECTED_ENGINE = "unsupported_by_selected_engine"


@dataclass(frozen=True, slots=True)
class LanguageCapability:
    language: str
    stt: str
    tts: str
    translation: str
    details: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        info = language_info(self.language)
        return {
            **info.to_dict(),
            "sttSupport": self.stt,
            "ttsSupport": self.tts,
            "translationSupport": self.translation,
            "details": dict(self.details),
        }


class LanguageService:
    def __init__(self, *, stt_manager=None, tts_manager=None, translation_manager=None, model_service=None) -> None:
        self.stt_manager = stt_manager
        self.tts_manager = tts_manager
        self.translation_manager = translation_manager
        self.model_service = model_service

    def list_languages(self, query: str = "") -> list[dict[str, object]]:
        return [self.capability(item.code).to_dict() for item in search_languages(query)]

    def get(self, code: str) -> LanguageInfo:
        return language_info(code)

    def stt_languages(self) -> set[str]:
        """Read faster-whisper's own mapping when available; don't keep a shadow Whisper list."""
        try:
            tokenizer = importlib.import_module("faster_whisper.tokenizer")
            values = getattr(tokenizer, "_LANGUAGE_CODES", ())
            return {str(code) for code in values}
        except Exception:
            # Dependency/model not present: report model-required rather than pretending support.
            return set()

    def tts_languages(self, engine_id: str = "voxcpm2") -> set[str]:
        if engine_id == "voxcpm2":
            return set(VOXCPM2_LANGUAGE_CODES)
        if self.tts_manager is None:
            return set()
        try:
            caps = self.tts_manager.get(engine_id).get_capabilities()
            values = getattr(caps, "supported_languages", ())
            return {str(x) for x in values if str(x) != "multilingual"}
        except Exception:
            return set()

    def translation_pairs(self, engine_id: str | None = None) -> set[tuple[str, str]]:
        manager = self.translation_manager
        if manager is None:
            return set()
        providers: Iterable[str] = [engine_id] if engine_id else manager.providers()
        result: set[tuple[str, str]] = set()
        for provider in providers:
            if not provider:
                continue
            try:
                engine = manager.get(provider)
                for source, target in engine.get_supported_language_pairs():
                    result.add((str(source), str(target)))
            except Exception:
                continue
        return result

    def capability(self, code: str, *, translation_target: str | None = None, tts_engine: str = "voxcpm2") -> LanguageCapability:
        language_info(code)
        stt_codes = self.stt_languages()
        stt = LanguageSupportState.SUPPORTED.value if code in stt_codes else LanguageSupportState.MODEL_REQUIRED.value
        tts_codes = self.tts_languages(tts_engine)
        tts = LanguageSupportState.SUPPORTED.value if code in tts_codes else LanguageSupportState.UNSUPPORTED_BY_SELECTED_ENGINE.value
        pairs = self.translation_pairs()
        if translation_target:
            translation = LanguageSupportState.SUPPORTED.value if (code, translation_target) in pairs else LanguageSupportState.MODEL_REQUIRED.value
        else:
            translation = LanguageSupportState.SUPPORTED.value if any(src == code for src, _ in pairs) else LanguageSupportState.MODEL_REQUIRED.value
        states = {stt, tts, translation}
        if LanguageSupportState.SUPPORTED.value in states and len(states) > 1:
            overall = LanguageSupportState.PARTIALLY_SUPPORTED.value
        elif states == {LanguageSupportState.SUPPORTED.value}:
            overall = LanguageSupportState.SUPPORTED.value
        else:
            overall = LanguageSupportState.MODEL_REQUIRED.value
        return LanguageCapability(code, stt, tts, translation, {"overall": overall, "ttsEngine": tts_engine})

    def supports_tts(self, code: str, engine_id: str = "voxcpm2") -> bool:
        return code in self.tts_languages(engine_id)

    def supports_translation_pair(self, source: str, target: str, engine_id: str | None = None) -> bool:
        if source == target:
            return False
        return (source, target) in self.translation_pairs(engine_id)

    @staticmethod
    def app_languages() -> tuple[str, ...]:
        return supported_language_codes()

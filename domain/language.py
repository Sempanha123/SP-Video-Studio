from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LanguageInfo:
    code: str
    name: str
    native_name: str


LANGUAGES: dict[str, LanguageInfo] = {
    "en": LanguageInfo("en", "English", "English"),
    "km": LanguageInfo("km", "Khmer", "ខ្មែរ"),
}


def language_info(code: str) -> LanguageInfo:
    try:
        return LANGUAGES[code]
    except KeyError as exc:
        raise ValueError(f"Unsupported language code: {code}") from exc


def language_name(code: str) -> str:
    return language_info(code).name


def supported_language_codes() -> tuple[str, ...]:
    return tuple(LANGUAGES)

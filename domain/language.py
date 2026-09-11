from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class LanguageInfo:
    code: str
    display_name: str
    native_name: str
    script: str = "Latin"
    text_direction: str = "ltr"
    fallback_fonts: tuple[str, ...] = ()
    stt_code: str = ""
    translation_codes: tuple[str, ...] = ()
    tts_metadata: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Backward-compatible alias used by Phase 11/12 UI code."""
        return self.display_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "displayName": self.display_name,
            "name": self.display_name,
            "nativeName": self.native_name,
            "script": self.script,
            "textDirection": self.text_direction,
            "fallbackFonts": list(self.fallback_fonts),
            "sttCode": self.stt_code,
            "translationCodes": list(self.translation_codes),
            "ttsMetadata": dict(self.tts_metadata),
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


_FALLBACK_ROWS = (
    ("en", "English", "English", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("km", "Khmer", "ខ្មែរ", "Khmer", ("Noto Sans Khmer", "Khmer OS System", "Noto Sans")),
    ("th", "Thai", "ไทย", "Thai", ("Noto Sans Thai", "Leelawadee UI", "Tahoma")),
    ("vi", "Vietnamese", "Tiếng Việt", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("zh", "Chinese", "中文", "Han", ("Noto Sans CJK SC", "Microsoft YaHei", "Noto Sans")),
    ("ja", "Japanese", "日本語", "Japanese", ("Noto Sans CJK JP", "Yu Gothic UI", "Noto Sans")),
    ("ko", "Korean", "한국어", "Hangul", ("Noto Sans CJK KR", "Malgun Gothic", "Noto Sans")),
    ("id", "Indonesian", "Bahasa Indonesia", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("ms", "Malay", "Bahasa Melayu", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("es", "Spanish", "Español", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("fr", "French", "Français", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("de", "German", "Deutsch", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("pt", "Portuguese", "Português", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("it", "Italian", "Italiano", "Latin", ("Noto Sans", "Segoe UI", "Arial")),
    ("hi", "Hindi", "हिन्दी", "Devanagari", ("Noto Sans Devanagari", "Nirmala UI", "Noto Sans")),
)


def _resource_candidates() -> Iterable[Path]:
    here = Path(__file__).resolve()
    yield here.parents[1] / "resources" / "languages.json"
    yield Path.cwd() / "resources" / "languages.json"


def _fallback_registry() -> dict[str, LanguageInfo]:
    return {
        code: LanguageInfo(
            code=code,
            display_name=name,
            native_name=native,
            script=script,
            fallback_fonts=fonts,
            stt_code=code,
            translation_codes=(code,),
            tts_metadata={"voxcpm2": code},
            metadata={"whisper": True},
        )
        for code, name, native, script, fonts in _FALLBACK_ROWS
    }


def _load_registry() -> dict[str, LanguageInfo]:
    path = next((candidate for candidate in _resource_candidates() if candidate.is_file()), None)
    if path is None:
        return _fallback_registry()
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _fallback_registry()
    result: dict[str, LanguageInfo] = {}
    for raw in rows if isinstance(rows, list) else []:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("code", "")).strip().lower()
        if not code:
            continue
        result[code] = LanguageInfo(
            code=code,
            display_name=str(raw.get("display_name") or raw.get("displayName") or code),
            native_name=str(raw.get("native_name") or raw.get("nativeName") or raw.get("display_name") or code),
            script=str(raw.get("script") or "Latin"),
            text_direction=str(raw.get("text_direction") or raw.get("textDirection") or "ltr"),
            fallback_fonts=tuple(str(x) for x in raw.get("fallback_fonts", raw.get("fallbackFonts", [])) if str(x).strip()),
            stt_code=str(raw.get("stt_code") or raw.get("sttCode") or code),
            translation_codes=tuple(str(x) for x in raw.get("translation_codes", raw.get("translationCodes", [code]))),
            tts_metadata={str(k): str(v) for k, v in dict(raw.get("tts_metadata", raw.get("ttsMetadata", {}))).items()},
            enabled=bool(raw.get("enabled", True)),
            metadata=dict(raw.get("metadata") or {}),
        )
    return result or _fallback_registry()


LANGUAGES: dict[str, LanguageInfo] = _load_registry()


def language_info(code: str) -> LanguageInfo:
    normalized = (code or "").strip().lower()
    try:
        return LANGUAGES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported language code: {code}") from exc


def language_name(code: str) -> str:
    return language_info(code).display_name


def supported_language_codes(*, enabled_only: bool = True) -> tuple[str, ...]:
    return tuple(
        code for code, info in LANGUAGES.items()
        if info.enabled or not enabled_only
    )


def search_languages(query: str = "", *, enabled_only: bool = True) -> tuple[LanguageInfo, ...]:
    needle = (query or "").strip().casefold()
    values = [item for item in LANGUAGES.values() if item.enabled or not enabled_only]
    if needle:
        values = [
            item for item in values
            if needle in item.code.casefold()
            or needle in item.display_name.casefold()
            or needle in item.native_name.casefold()
        ]
    values.sort(key=lambda item: (item.display_name.casefold(), item.code))
    return tuple(values)


def preferred_font_families(code: str) -> tuple[str, ...]:
    return language_info(code).fallback_fonts

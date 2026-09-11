from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
import re

_PLACEHOLDER_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,79}$")
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([A-Za-z][A-Za-z0-9_-]{0,79})\s*\}\}")


class TemplatePlaceholderType(StrEnum):
    MEDIA = "media"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    VOICE = "voice"
    SPEAKER = "speaker"
    TEXT = "text"
    LOGO = "logo"
    LANGUAGE = "language"
    SUBTITLE = "subtitle"
    NEWS_SOURCE = "news_source"
    CLAIM = "claim"
    STORY_IDEA = "story_idea"


class TemplateLanguageMode(StrEnum):
    PROJECT = "project"
    FIXED = "fixed"
    USER_SELECT = "user_select"


@dataclass(slots=True)
class TemplatePlaceholder:
    placeholder_id: str
    label: str
    placeholder_type: str | TemplatePlaceholderType
    required: bool = False
    instructions: str = ""
    language_mode: str | TemplateLanguageMode = TemplateLanguageMode.PROJECT
    fixed_language: str = ""
    role: str = ""
    voice_category: str = ""
    accepted_media_types: tuple[str, ...] = ()
    default_value: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str: return self.placeholder_id
    @property
    def type_code(self) -> str: return self.placeholder_type.value if isinstance(self.placeholder_type,StrEnum) else str(self.placeholder_type)
    @property
    def language_mode_code(self) -> str: return self.language_mode.value if isinstance(self.language_mode,StrEnum) else str(self.language_mode)

    def validate(self) -> None:
        if not _PLACEHOLDER_ID_RE.fullmatch(self.placeholder_id): raise ValueError("Template placeholder ID is invalid.")
        if not self.label.strip(): raise ValueError("Template placeholder label is required.")
        if self.type_code not in {x.value for x in TemplatePlaceholderType}: raise ValueError("Unsupported template placeholder type.")
        if self.language_mode_code not in {x.value for x in TemplateLanguageMode}: raise ValueError("Unsupported template language mode.")
        if self.language_mode_code==TemplateLanguageMode.FIXED.value and not self.fixed_language: raise ValueError("Fixed-language placeholder requires a language code.")

    def to_dict(self) -> dict[str, Any]:
        self.validate(); return {"id":self.id,"label":self.label,"type":self.type_code,"required":self.required,"instructions":self.instructions,"languageMode":self.language_mode_code,"fixedLanguage":self.fixed_language,"role":self.role,"voiceCategory":self.voice_category,"acceptedMediaTypes":list(self.accepted_media_types),"defaultValue":self.default_value,"metadata":dict(self.metadata)}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "TemplatePlaceholder":
        item=cls(str(raw.get("id") or ""),str(raw.get("label") or ""),str(raw.get("type") or "text"),bool(raw.get("required",False)),str(raw.get("instructions") or ""),str(raw.get("languageMode") or "project"),str(raw.get("fixedLanguage") or ""),str(raw.get("role") or ""),str(raw.get("voiceCategory") or ""),tuple(str(x) for x in (raw.get("acceptedMediaTypes") or ())),str(raw.get("defaultValue") or ""),dict(raw.get("metadata") or {}))
        item.validate(); return item


def placeholder_ids_in(value: Any) -> set[str]:
    if isinstance(value,str): return set(PLACEHOLDER_PATTERN.findall(value))
    if isinstance(value,dict):
        result:set[str]=set()
        for k,v in value.items(): result.update(placeholder_ids_in(k)); result.update(placeholder_ids_in(v))
        return result
    if isinstance(value,(list,tuple)):
        result:set[str]=set()
        for item in value: result.update(placeholder_ids_in(item))
        return result
    return set()


def resolve_placeholders(value: Any, resolutions: Mapping[str, Any], *, preserve_unresolved: bool=False) -> Any:
    if isinstance(value,str):
        full=PLACEHOLDER_PATTERN.fullmatch(value.strip())
        if full:
            key=full.group(1)
            if key in resolutions: return resolutions[key]
            return value if preserve_unresolved else ""
        def repl(match: re.Match[str]) -> str:
            key=match.group(1)
            if key not in resolutions: return match.group(0) if preserve_unresolved else ""
            return str(resolutions[key])
        return PLACEHOLDER_PATTERN.sub(repl,value)
    if isinstance(value,dict): return {k:resolve_placeholders(v,resolutions,preserve_unresolved=preserve_unresolved) for k,v in value.items()}
    if isinstance(value,list): return [resolve_placeholders(v,resolutions,preserve_unresolved=preserve_unresolved) for v in value]
    if isinstance(value,tuple): return tuple(resolve_placeholders(v,resolutions,preserve_unresolved=preserve_unresolved) for v in value)
    return value

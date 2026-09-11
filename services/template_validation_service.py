from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
import re

from domain.project import ProjectWorkflow, SUPPORTED_ASPECT_RATIOS
from domain.template import Template
from domain.template_asset import EXECUTABLE_TEMPLATE_EXTENSIONS, is_safe_relative_template_path
from domain.template_errors import TemplateValidationError, TemplateVersionTooNew
from domain.template_manifest import TEMPLATE_SCHEMA_VERSION
from domain.template_placeholder import placeholder_ids_in
from services.language_service import LanguageService

_WINDOWS_ABS=re.compile(r"^[A-Za-z]:[\\/]")

@dataclass(frozen=True,slots=True)
class TemplateIssue:
    severity: str
    code: str
    message: str

    def to_dict(self)->dict[str,str]: return {"severity":self.severity,"code":self.code,"message":self.message}


class TemplateValidationService:
    FEATURE_SET=frozenset({"layered_video","chroma_key","multi_speaker","tts","stt","translation","subtitles","news","story","shorts","dubbing","timeline","export"})

    def __init__(self,languages:LanguageService,feature_probe=None) -> None:
        self.languages=languages; self.feature_probe=feature_probe

    def validate(self,item:Template,*,strict:bool=True)->list[TemplateIssue]:
        issues:list[TemplateIssue]=[]
        try:item.validate()
        except Exception as exc: issues.append(TemplateIssue("error","schema",str(exc)))
        if item.schema_version>TEMPLATE_SCHEMA_VERSION: issues.append(TemplateIssue("error","newer_schema","This template was created with a newer MMO Video Studio version."))
        workflows={x.value for x in ProjectWorkflow}
        if item.workflow not in workflows: issues.append(TemplateIssue("error","workflow",f"Unsupported workflow: {item.workflow}"))
        known_languages=set(self.languages.app_languages())
        for code in item.supported_languages:
            if code!="*" and code not in known_languages: issues.append(TemplateIssue("error","language",f"Unknown language code: {code}"))
        for aspect in item.supported_aspect_ratios:
            if aspect not in SUPPORTED_ASPECT_RATIOS: issues.append(TemplateIssue("error","aspect",f"Unsupported aspect ratio: {aspect}"))
        if item.preview_image:
            preview=str(item.preview_image).replace("\\","/")
            if preview.startswith("/") or _WINDOWS_ABS.match(preview) or ".." in PurePosixPath(preview).parts:
                issues.append(TemplateIssue("error","preview_path","Template preview paths must be relative to the template package."))
        self._scan_unsafe(item.metadata,issues)
        placeholders={x.id for x in item.placeholders}
        for component in item.components:
            for ref in placeholder_ids_in(component.data):
                if ref not in placeholders and ref!="project_language": issues.append(TemplateIssue("error","placeholder",f"Unknown placeholder: {ref}"))
            self._scan_unsafe(component.data,issues)
        for asset in item.assets:
            try:asset.validate()
            except Exception as exc: issues.append(TemplateIssue("error","asset",str(exc)))
        missing_features=[]
        if self.feature_probe:
            for feature in item.required_features:
                try:
                    if not bool(self.feature_probe(feature)): missing_features.append(feature)
                except Exception: missing_features.append(feature)
        else:
            missing_features=[f for f in item.required_features if f not in self.FEATURE_SET]
        for feature in missing_features: issues.append(TemplateIssue("warning","feature",f"Feature unavailable: {feature}"))
        if strict and any(x.severity=="error" for x in issues): raise TemplateValidationError(issues[0].message)
        return issues

    def compatibility(self,item:Template,*,language:str,aspect_ratio:str)->dict[str,Any]:
        issues=self.validate(item,strict=False); state="compatible"
        if any(x.code=="newer_schema" for x in issues): state="unsupported_version"
        elif any(x.severity=="error" for x in issues): state="missing_features"
        elif any(x.code=="feature" for x in issues): state="missing_features"
        elif item.supported_languages and "*" not in item.supported_languages and language not in item.supported_languages: issues.append(TemplateIssue("warning","language_choice",f"Template does not list {language} as a supported language.")); state="compatible_with_warnings"
        elif item.supported_aspect_ratios and aspect_ratio not in item.supported_aspect_ratios: issues.append(TemplateIssue("warning","aspect_choice",f"This template does not include a layout for {aspect_ratio}.")); state="compatible_with_warnings"
        elif any(x.severity=="warning" for x in issues): state="compatible_with_warnings"
        # AI capabilities remain separate from registry membership. Missing models warn; language is never silently changed.
        requires=set(item.required_features)
        missing_model=False
        if "tts" in requires and not self.languages.supports_tts(language):
            issues.append(TemplateIssue("warning","voice_setup",f"Voice Setup Required for {language}.")); missing_model=True
        if "stt" in requires and language not in self.languages.stt_languages():
            issues.append(TemplateIssue("warning","stt_setup",f"Speech recognition model setup is required for {language}.")); missing_model=True
        if "translation" in requires:
            pairs=self.languages.translation_pairs()
            if not any(language in pair for pair in pairs):
                issues.append(TemplateIssue("warning","translation_setup",f"Translation model setup is required for {language}.")); missing_model=True
        if missing_model: state="missing_models"
        return {"state":state,"issues":[x.to_dict() for x in issues]}

    @staticmethod
    def validate_archive_name(name:str)->None:
        normalized=name.replace("\\","/")
        if not is_safe_relative_template_path(normalized): raise TemplateValidationError("Template package contains an unsafe path.")
        suffix=PurePosixPath(normalized).suffix.lower()
        if suffix in EXECUTABLE_TEMPLATE_EXTENSIONS: raise TemplateValidationError("Template package contains executable content.")

    def _scan_unsafe(self,value:Any,issues:list[TemplateIssue])->None:
        if isinstance(value,str):
            text=value.strip()
            if text.startswith("/") or _WINDOWS_ABS.match(text): issues.append(TemplateIssue("error","absolute_path","Templates cannot store absolute local paths."))
        elif isinstance(value,dict):
            blocked={"referenceAudioPath","promptAudioPath","generatedAudioPath","renderPath","privateNewsSource","claimText"}
            for key,val in value.items():
                if str(key) in blocked and val: issues.append(TemplateIssue("error","private_runtime_data",f"Templates cannot store {key}."))
                self._scan_unsafe(val,issues)
        elif isinstance(value,(list,tuple)):
            for item in value:self._scan_unsafe(item,issues)

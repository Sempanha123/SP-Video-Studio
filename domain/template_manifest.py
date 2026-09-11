from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from domain.template_asset import TemplateAsset

TEMPLATE_SCHEMA_VERSION=1


@dataclass(slots=True)
class TemplateManifest:
    template_id: str
    name: str
    version: str
    template_type: str
    workflow: str
    schema_version: int = TEMPLATE_SCHEMA_VERSION
    created_with_app_version: str = "phase24"
    required_features: tuple[str,...] = ()
    supported_languages: tuple[str,...] = ()
    supported_aspect_ratios: tuple[str,...] = ()
    assets: list[TemplateAsset] = field(default_factory=list)
    checksums: dict[str,str] = field(default_factory=dict)
    metadata: dict[str,Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.template_id or not self.name.strip(): raise ValueError("Template manifest identity is required.")
        if self.schema_version<1: raise ValueError("Template schema version is invalid.")
        if not self.version.strip(): raise ValueError("Template version is required.")
        for item in self.assets: item.validate()

    def to_dict(self) -> dict[str,Any]:
        self.validate(); return {"schema_version":self.schema_version,"template_id":self.template_id,"name":self.name,"version":self.version,"template_type":self.template_type,"workflow":self.workflow,"created_with_app_version":self.created_with_app_version,"required_features":list(self.required_features),"supported_languages":list(self.supported_languages),"supported_aspect_ratios":list(self.supported_aspect_ratios),"assets":[a.to_dict() for a in self.assets],"checksums":dict(self.checksums),"metadata":dict(self.metadata)}

    @classmethod
    def from_dict(cls, raw: Mapping[str,Any]) -> "TemplateManifest":
        item=cls(template_id=str(raw.get("template_id") or raw.get("templateId") or ""),name=str(raw.get("name") or ""),version=str(raw.get("version") or "1.0"),template_type=str(raw.get("template_type") or raw.get("templateType") or "project"),workflow=str(raw.get("workflow") or "video"),schema_version=int(raw.get("schema_version") or raw.get("schemaVersion") or 1),created_with_app_version=str(raw.get("created_with_app_version") or raw.get("createdWithAppVersion") or "unknown"),required_features=tuple(str(x) for x in raw.get("required_features",raw.get("requiredFeatures",()))),supported_languages=tuple(str(x) for x in raw.get("supported_languages",raw.get("supportedLanguages",()))),supported_aspect_ratios=tuple(str(x) for x in raw.get("supported_aspect_ratios",raw.get("supportedAspectRatios",()))),assets=[TemplateAsset.from_dict(x) for x in raw.get("assets",())],checksums={str(k):str(v) for k,v in dict(raw.get("checksums") or {}).items()},metadata=dict(raw.get("metadata") or {})); item.validate(); return item

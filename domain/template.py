from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso
from domain.template_asset import TemplateAsset
from domain.template_component import TemplateComponent
from domain.template_manifest import TEMPLATE_SCHEMA_VERSION, TemplateManifest
from domain.template_placeholder import TemplatePlaceholder


class TemplateType(StrEnum):
    PROJECT="project"
    SCENE="scene"
    NEWS="news"
    STORY="story"
    SHORT="short"
    INTERVIEW="interview"
    REPORTER="reporter"
    SUBTITLE="subtitle"
    VISUAL_LAYOUT="visual_layout"
    SPEAKER_LAYOUT="speaker_layout"


@dataclass(slots=True)
class Template:
    name: str
    template_type: str | TemplateType
    category: str
    description: str
    workflow: str
    version: str = "1.0"
    schema_version: int = TEMPLATE_SCHEMA_VERSION
    builtin: bool = False
    author_label: str = "MMO Video Studio"
    preview_image: str = ""
    tags: tuple[str,...] = ()
    supported_aspect_ratios: tuple[str,...] = ("16:9",)
    supported_languages: tuple[str,...] = ()
    required_features: tuple[str,...] = ()
    manifest_path: str = ""
    components: list[TemplateComponent] = field(default_factory=list)
    placeholders: list[TemplatePlaceholder] = field(default_factory=list)
    assets: list[TemplateAsset] = field(default_factory=list)
    metadata: dict[str,Any] = field(default_factory=dict)
    template_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def id(self)->str: return self.template_id
    @property
    def type_code(self)->str: return self.template_type.value if isinstance(self.template_type,StrEnum) else str(self.template_type)

    def validate(self)->None:
        if not self.id or not self.name.strip(): raise ValueError("Template name and ID are required.")
        if self.type_code not in {x.value for x in TemplateType}: raise ValueError("Unsupported template type.")
        if not self.workflow.strip(): raise ValueError("Template workflow is required.")
        if self.schema_version<1: raise ValueError("Template schema version is invalid.")
        if not self.version.strip(): raise ValueError("Template version is required.")
        component_ids=[x.local_id for x in self.components]; placeholder_ids=[x.id for x in self.placeholders]
        if len(component_ids)!=len(set(component_ids)): raise ValueError("Template component IDs must be unique.")
        if len(placeholder_ids)!=len(set(placeholder_ids)): raise ValueError("Template placeholder IDs must be unique.")
        for item in self.components: item.validate()
        for item in self.placeholders: item.validate()
        for item in self.assets: item.validate()

    def manifest(self)->TemplateManifest:
        return TemplateManifest(self.id,self.name,self.version,self.type_code,self.workflow,self.schema_version,"phase24",self.required_features,self.supported_languages,self.supported_aspect_ratios,list(self.assets),metadata={"category":self.category,"builtin":self.builtin})

    def to_dict(self)->dict[str,Any]:
        self.validate(); return {"id":self.id,"name":self.name,"templateType":self.type_code,"category":self.category,"description":self.description,"workflow":self.workflow,"version":self.version,"schemaVersion":self.schema_version,"builtin":self.builtin,"authorLabel":self.author_label,"previewImage":self.preview_image,"tags":list(self.tags),"supportedAspectRatios":list(self.supported_aspect_ratios),"supportedLanguages":list(self.supported_languages),"requiredFeatures":list(self.required_features),"components":[x.to_dict() for x in self.components],"placeholders":[x.to_dict() for x in self.placeholders],"assets":[x.to_dict() for x in self.assets],"metadata":dict(self.metadata),"createdAt":self.created_at,"updatedAt":self.updated_at}

    @classmethod
    def from_dict(cls, raw: Mapping[str,Any], *, builtin: bool|None=None) -> "Template":
        item=cls(name=str(raw.get("name") or ""),template_type=str(raw.get("templateType") or raw.get("template_type") or "project"),category=str(raw.get("category") or "General Video"),description=str(raw.get("description") or ""),workflow=str(raw.get("workflow") or "video"),version=str(raw.get("version") or "1.0"),schema_version=int(raw.get("schemaVersion") or raw.get("schema_version") or 1),builtin=bool(raw.get("builtin",False) if builtin is None else builtin),author_label=str(raw.get("authorLabel") or raw.get("author_label") or "MMO Video Studio"),preview_image=str(raw.get("previewImage") or raw.get("preview_image") or ""),tags=tuple(str(x) for x in raw.get("tags",())),supported_aspect_ratios=tuple(str(x) for x in raw.get("supportedAspectRatios",raw.get("supported_aspect_ratios",("16:9",)))),supported_languages=tuple(str(x) for x in raw.get("supportedLanguages",raw.get("supported_languages",()))),required_features=tuple(str(x) for x in raw.get("requiredFeatures",raw.get("required_features",()))),manifest_path=str(raw.get("manifestPath") or raw.get("manifest_path") or ""),components=[TemplateComponent.from_dict(x) for x in raw.get("components",())],placeholders=[TemplatePlaceholder.from_dict(x) for x in raw.get("placeholders",())],assets=[TemplateAsset.from_dict(x) for x in raw.get("assets",())],metadata=dict(raw.get("metadata") or {}),template_id=str(raw.get("id") or raw.get("template_id") or uuid4()),created_at=str(raw.get("createdAt") or raw.get("created_at") or utc_now_iso()),updated_at=str(raw.get("updatedAt") or raw.get("updated_at") or utc_now_iso()))
        item.validate(); return item

    def search_text(self)->str:
        return " ".join((self.name,self.category,self.description,*self.tags,self.workflow,self.type_code)).casefold()

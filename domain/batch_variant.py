from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any
from uuid import uuid4

@dataclass(slots=True)
class BatchVariantConfig:
    batch_id:str; languages:list[str]=field(default_factory=list); voices:list[str]=field(default_factory=list); platforms:list[str]=field(default_factory=list); aspect_ratios:list[str]=field(default_factory=list); template_options:list[str]=field(default_factory=list); source_language:str=""; seed:int=0; metadata:dict[str,Any]=field(default_factory=dict); variant_id:str=field(default_factory=lambda:str(uuid4()))
    @property
    def id(self):return self.variant_id
    def normalized(self):
        return {"languages":list(dict.fromkeys(self.languages)) or [""],"voices":list(dict.fromkeys(self.voices)) or [""],"platforms":list(dict.fromkeys(self.platforms)) or [""],"aspectRatios":list(dict.fromkeys(self.aspect_ratios)) or [""],"templateOptions":list(dict.fromkeys(self.template_options)) or [""],"sourceLanguage":self.source_language,"seed":int(self.seed),"metadata":dict(self.metadata)}
    def to_dict(self):return {"id":self.id,"batchId":self.batch_id,**self.normalized()}

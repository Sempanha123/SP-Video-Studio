from __future__ import annotations
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from uuid import uuid4

class BatchMappingKind(StrEnum):
    COLUMN="column"; CONSTANT="constant"; SYSTEM="system"; GENERATED_FILENAME="generated_filename"; DEFAULT="default"; EMPTY="empty"; ASSET_FIXED="asset_fixed"; ASSET_COLUMN="asset_column"; ASSET_COLLECTION="asset_collection"; VOICE_FIXED="voice_fixed"; VOICE_COLUMN="voice_column"; VOICE_LANGUAGE="voice_language"; VOICE_ROLE="voice_role"
class BatchTransform(StrEnum): TRIM="trim"; UPPERCASE="uppercase"; LOWERCASE="lowercase"; PREFIX="prefix"; SUFFIX="suffix"

@dataclass(slots=True)
class BatchMapping:
    batch_id:str; target:str; kind:str|BatchMappingKind; source:str=""; value:Any=""; required:bool=False; default_value:Any=""; transforms:list[dict[str,Any]]=field(default_factory=list); metadata:dict[str,Any]=field(default_factory=dict); mapping_id:str=field(default_factory=lambda:str(uuid4()))
    @property
    def id(self):return self.mapping_id
    @property
    def kind_code(self):return self.kind.value if isinstance(self.kind,StrEnum) else str(self.kind)
    def validate(self):
        if not self.target.strip():raise ValueError("Mapping target is required.")
        if self.kind_code not in {x.value for x in BatchMappingKind}:raise ValueError("Unsupported Batch mapping kind.")
        for transform in self.transforms:
            if str(transform.get("type")) not in {x.value for x in BatchTransform}:raise ValueError("Unsupported Batch transform.")
    def to_dict(self):return {"id":self.id,"batchId":self.batch_id,"target":self.target,"kind":self.kind_code,"source":self.source,"value":self.value,"required":self.required,"defaultValue":self.default_value,"transforms":[dict(x) for x in self.transforms],"metadata":dict(self.metadata)}

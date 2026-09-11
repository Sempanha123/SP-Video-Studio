from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso

class AudioEffectType(StrEnum):
    GAIN='gain'; HIGH_PASS='high_pass'; LOW_PASS='low_pass'; EQ='eq'; COMPRESSOR='compressor'; LIMITER='limiter'

@dataclass(slots=True)
class AudioEffectSpec:
    owner_type: str
    owner_id: str
    effect_type: str|AudioEffectType
    order: int=0
    enabled: bool=True
    settings: dict[str,Any]=field(default_factory=dict)
    effect_id: str=field(default_factory=lambda:str(uuid4()))
    created_at: str=field(default_factory=utc_now_iso)
    updated_at: str=field(default_factory=utc_now_iso)
    @property
    def id(self)->str:return self.effect_id
    @property
    def type_code(self)->str:return self.effect_type.value if isinstance(self.effect_type,StrEnum) else str(self.effect_type)
    def validate(self)->None:
        if self.owner_type not in {'clip','track','bus','master'}: raise ValueError('Unsupported audio effect owner.')
        if not self.owner_id: raise ValueError('Audio effect owner is required.')
        if self.type_code not in {x.value for x in AudioEffectType}: raise ValueError('Unsupported audio effect.')
        if self.order<0: raise ValueError('Effect order cannot be negative.')
    def to_dict(self)->dict[str,Any]:
        return {'id':self.id,'ownerType':self.owner_type,'ownerId':self.owner_id,'type':self.type_code,'order':self.order,'enabled':self.enabled,'settings':dict(self.settings)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->'AudioEffectSpec':
        try:s=json.loads(str(row['settings_json'] or '{}'))
        except Exception:s={}
        return cls(str(row['owner_type']),str(row['owner_id']),str(row['effect_type']),int(row['effect_order']),bool(row['enabled']),s if isinstance(s,dict) else {},str(row['id']),str(row['created_at']),str(row['updated_at']))

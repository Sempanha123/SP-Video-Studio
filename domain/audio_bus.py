from __future__ import annotations
import json
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any,Mapping
from uuid import uuid4
from domain.project import utc_now_iso

class AudioBusRole(StrEnum):
    VOICE='voice'; MUSIC='music'; SFX='sfx'; SOURCE='source'; MASTER='master'; GENERAL='general'

@dataclass(slots=True)
class AudioBus:
    project_id:str; name:str; role:str|AudioBusRole=AudioBusRole.GENERAL; order:int=0; gain_db:float=0.0; muted:bool=False; metadata:dict[str,Any]=field(default_factory=dict); bus_id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=utc_now_iso); updated_at:str=field(default_factory=utc_now_iso)
    @property
    def id(self):return self.bus_id
    @property
    def role_code(self):return self.role.value if isinstance(self.role,StrEnum) else str(self.role)
    def validate(self):
        if not self.project_id or not self.name.strip():raise ValueError('Audio bus requires project and name.')
        if self.role_code not in {x.value for x in AudioBusRole}:raise ValueError('Unsupported audio bus role.')
        if not -60.0<=float(self.gain_db)<=12.0:raise ValueError('Bus gain must be between -60 and +12 dB.')
    def to_dict(self):return {'id':self.id,'projectId':self.project_id,'name':self.name,'role':self.role_code,'order':self.order,'gainDb':self.gain_db,'muted':self.muted,'metadata':dict(self.metadata)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->'AudioBus':
        try:m=json.loads(str(row['metadata_json'] or '{}'))
        except Exception:m={}
        return cls(str(row['project_id']),str(row['name']),str(row['role']),int(row['bus_order']),float(row['gain_db']),bool(row['muted']),m if isinstance(m,dict) else {},str(row['id']),str(row['created_at']),str(row['updated_at']))

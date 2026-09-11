from __future__ import annotations
import json
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any,Mapping
from uuid import uuid4
from domain.project import utc_now_iso

class AudioTrackRole(StrEnum):
    VOICE='voice'; DIALOGUE='dialogue'; NARRATION='narration'; SOURCE_AUDIO='source_audio'; MUSIC='music'; SFX='sfx'; AMBIENCE='ambience'; BROLL_AUDIO='broll_audio'; DUB='dub'; GENERAL='general'

@dataclass(slots=True)
class AudioTrack:
    project_id:str; name:str; role:str|AudioTrackRole=AudioTrackRole.GENERAL; order:int=0; gain_db:float=0.0; pan:float=0.0; muted:bool=False; solo:bool=False; enabled:bool=True; bus_id:str=''; metadata:dict[str,Any]=field(default_factory=dict); track_id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=utc_now_iso); updated_at:str=field(default_factory=utc_now_iso)
    @property
    def id(self):return self.track_id
    @property
    def role_code(self):return self.role.value if isinstance(self.role,StrEnum) else str(self.role)
    def validate(self):
        if not self.project_id or not self.name.strip():raise ValueError('Audio track requires project and name.')
        if self.role_code not in {x.value for x in AudioTrackRole}:raise ValueError('Unsupported audio track role.')
        if not -60.0<=float(self.gain_db)<=12.0:raise ValueError('Track gain must be between -60 and +12 dB.')
        if not -1.0<=float(self.pan)<=1.0:raise ValueError('Track pan must be between -1 and +1.')
        if self.order<0:raise ValueError('Track order cannot be negative.')
    def to_dict(self):return {'id':self.id,'projectId':self.project_id,'name':self.name,'role':self.role_code,'order':self.order,'gainDb':self.gain_db,'pan':self.pan,'muted':self.muted,'solo':self.solo,'enabled':self.enabled,'busId':self.bus_id,'metadata':dict(self.metadata)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->'AudioTrack':
        try:m=json.loads(str(row['metadata_json'] or '{}'))
        except Exception:m={}
        return cls(str(row['project_id']),str(row['name']),str(row['role']),int(row['track_order']),float(row['gain_db']),float(row['pan']),bool(row['muted']),bool(row['solo']),bool(row['enabled']),str(row['bus_id'] or ''),m if isinstance(m,dict) else {},str(row['id']),str(row['created_at']),str(row['updated_at']))

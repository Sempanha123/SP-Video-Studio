from __future__ import annotations
import json
from dataclasses import dataclass,field
from typing import Any,Mapping
from domain.project import utc_now_iso

@dataclass(slots=True)
class AudioMixSettings:
    project_id:str; master_gain_db:float=0.0; limiter_enabled:bool=True; limiter_limit:float=0.95; normalization_enabled:bool=False; normalization_target_lufs:float=-16.0; preset:str='custom'; metadata:dict[str,Any]=field(default_factory=dict); updated_at:str=field(default_factory=utc_now_iso)
    def validate(self):
        if not self.project_id:raise ValueError('Audio mix requires project.')
        if not -60.0<=float(self.master_gain_db)<=12.0:raise ValueError('Master gain is out of range.')
        if not 0.1<=float(self.limiter_limit)<=1.0:raise ValueError('Limiter limit is invalid.')
        if not -40.0<=float(self.normalization_target_lufs)<=-5.0:raise ValueError('Loudness target is invalid.')
    def to_dict(self):return {'projectId':self.project_id,'masterGainDb':self.master_gain_db,'limiterEnabled':self.limiter_enabled,'limiterLimit':self.limiter_limit,'normalizationEnabled':self.normalization_enabled,'normalizationTargetLufs':self.normalization_target_lufs,'preset':self.preset,'metadata':dict(self.metadata),'updatedAt':self.updated_at}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->'AudioMixSettings':
        try:m=json.loads(str(row['metadata_json'] or '{}'))
        except Exception:m={}
        return cls(str(row['project_id']),float(row['master_gain_db']),bool(row['limiter_enabled']),float(row['limiter_limit']),bool(row['normalization_enabled']),float(row['normalization_target_lufs']),str(row['preset']),m if isinstance(m,dict) else {},str(row['updated_at']))

from __future__ import annotations
import json
from dataclasses import dataclass,field
from typing import Any,Mapping
from uuid import uuid4
from domain.project import utc_now_iso

@dataclass(slots=True)
class DuckingRule:
    project_id:str; trigger_id:str; target_id:str; trigger_kind:str='bus'; target_kind:str='bus'; duck_amount_db:float=-12.0; attack_ms:int=120; release_ms:int=220; threshold:float|None=None; enabled:bool=True; metadata:dict[str,Any]=field(default_factory=dict); rule_id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=utc_now_iso); updated_at:str=field(default_factory=utc_now_iso)
    @property
    def id(self):return self.rule_id
    def validate(self):
        if not self.project_id or not self.trigger_id or not self.target_id:raise ValueError('Ducking routing is required.')
        if self.trigger_kind not in {'track','bus'} or self.target_kind not in {'track','bus'}:raise ValueError('Unsupported ducking endpoint.')
        if not -36.0<=float(self.duck_amount_db)<=0.0:raise ValueError('Duck amount must be between -36 and 0 dB.')
        if not 0<=self.attack_ms<=5000 or not 0<=self.release_ms<=10000:raise ValueError('Ducking timing is invalid.')
    def to_dict(self):return {'id':self.id,'projectId':self.project_id,'triggerKind':self.trigger_kind,'triggerId':self.trigger_id,'targetKind':self.target_kind,'targetId':self.target_id,'duckAmountDb':self.duck_amount_db,'attackMs':self.attack_ms,'releaseMs':self.release_ms,'threshold':self.threshold,'enabled':self.enabled,'metadata':dict(self.metadata)}
    @classmethod
    def from_record(cls,row:Mapping[str,Any])->'DuckingRule':
        try:m=json.loads(str(row['metadata_json'] or '{}'))
        except Exception:m={}
        return cls(str(row['project_id']),str(row['trigger_id']),str(row['target_id']),str(row['trigger_kind']),str(row['target_kind']),float(row['duck_amount_db']),int(row['attack_ms']),int(row['release_ms']),float(row['threshold']) if row['threshold'] is not None else None,bool(row['enabled']),m if isinstance(m,dict) else {},str(row['id']),str(row['created_at']),str(row['updated_at']))

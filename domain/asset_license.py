from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping

RIGHTS_STATUSES={"owned","licensed","royalty_free","public_domain","unknown","custom"}

@dataclass(slots=True)
class AssetLicense:
    asset_id:str
    rights_status:str="unknown"
    source_url:str=""
    license_name:str=""
    notes:str=""
    attribution_required:bool=False
    attribution_text:str=""
    metadata:dict[str,Any]=field(default_factory=dict)
    def validate(self)->None:
        if self.rights_status not in RIGHTS_STATUSES: raise ValueError("Unsupported asset rights status.")
        if self.attribution_required and not self.attribution_text.strip(): raise ValueError("Attribution text is required when attribution is enabled.")
    def to_dict(self)->dict[str,Any]:
        return {"assetId":self.asset_id,"rightsStatus":self.rights_status,"sourceUrl":self.source_url,"licenseName":self.license_name,"notes":self.notes,"attributionRequired":self.attribution_required,"attributionText":self.attribution_text,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,r:Mapping[str,Any]):
        import json
        try:m=json.loads(r["metadata_json"] or "{}")
        except Exception:m={}
        return cls(str(r["asset_id"]),str(r["rights_status"]),str(r["source_url"] or ""),str(r["license_name"] or ""),str(r["notes"] or ""),bool(r["attribution_required"]),str(r["attribution_text"] or ""),m if isinstance(m,dict) else {})

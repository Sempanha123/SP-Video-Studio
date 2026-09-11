from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass

from storage.repositories.news_repository import NewsRepository

@dataclass(frozen=True, slots=True)
class NewsIssue:
    severity:str; code:str; message:str
    def to_dict(self)->dict[str,str]:return {"severity":self.severity,"code":self.code,"message":self.message}

_CONNECTIVE=("here is what we know","now let's look","now let’s look","why this matters","what happens next","in summary","to recap")
_FACTUAL_HINT=re.compile(r"\d|\b(?:said|announced|reported|confirmed|according|on\s+[A-Z]|today|yesterday|million|percent|%)\b",re.I)

def source_fingerprint(repository:NewsRepository,project_id:str)->str:
    rows=[]
    for s in repository.list_sources(project_id):
        snap=repository.latest_snapshot(project_id,s.id); rows.append((s.id,snap.id if snap else "",snap.content_hash if snap else ""))
    approved=[(c.id,c.text,c.status_code) for c in repository.list_claims(project_id) if c.status_code=="approved"]
    payload={"sources":rows,"approved":approved}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

class NewsValidationService:
    def __init__(self,repository:NewsRepository)->None:self.repository=repository
    @staticmethod
    def is_connective(text:str)->bool:
        n=" ".join((text or "").strip().casefold().split())
        return not n or any(n.startswith(x) for x in _CONNECTIVE)
    @classmethod
    def looks_factual(cls,text:str)->bool:
        if cls.is_connective(text):return False
        return bool(_FACTUAL_HINT.search(text)) or len((text or "").split())>=5
    def grounding_issues(self,project_id:str,script_id:str)->list[NewsIssue]:
        mappings=self.repository.mappings(project_id,script_id); issues=[]
        for m in mappings:
            if m.mapping_type=="factual" and (m.status!="grounded" or not m.claim_ids):issues.append(NewsIssue("error","unsupported_script_sentence","A factual script sentence needs approved claim support."))
        return issues
    def readiness(self,project_id:str,script_id:str|None=None)->dict[str,object]:
        meta=self.repository.get_project(project_id); sources=self.repository.list_sources(project_id); claims=self.repository.list_claims(project_id); briefs=self.repository.list_briefs(project_id)
        approved=sum(c.status_code=="approved" for c in claims); unsupported=sum(c.status_code=="unsupported" for c in claims); conflicting=sum(c.status_code=="conflicting" for c in claims); review=sum(c.status_code in {"candidate","needs_review"} for c in claims)
        grounding=self.grounding_issues(project_id,script_id) if script_id else []
        level="not_ready"
        if meta and meta.topic.strip() and sources and approved:
            level="needs_review" if unsupported or conflicting or review or grounding else "ready_for_production"
        return {"level":level,"sources":len(sources),"approvedClaims":approved,"needsReviewClaims":review,"unsupportedClaims":unsupported,"conflictingClaims":conflicting,"briefs":len(briefs),"groundingIssues":len(grounding)}

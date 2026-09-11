from __future__ import annotations
import re
from difflib import SequenceMatcher

from domain.news_claim import NewsClaim, NewsClaimStatus, NewsEvidence
from domain.project import utc_now_iso
from services.news_errors import NewsClaimConflict, NewsClaimUnsupported, NewsInvalidSource
from services.news_extraction_service import NewsExtractionService
from storage.repositories.news_repository import NewsRepository

_NUM_RE=re.compile(r"(?<!\w)(?:\d[\d,.]*)(?!\w)")
_DATE_TOKEN_RE=re.compile(r"\b(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?)\b",re.I)
_WORD_RE=re.compile(r"\w+",re.UNICODE)


def _norm(text:str)->str:return " ".join((text or "").casefold().split())
def _base_words(text:str)->set[str]:
    return {w for w in _WORD_RE.findall(_NUM_RE.sub(" ",_DATE_TOKEN_RE.sub(" ",text.casefold()))) if len(w)>2}

class NewsClaimService:
    def __init__(self,repository:NewsRepository,extraction:NewsExtractionService|None=None)->None:
        self.repository=repository; self.extraction=extraction or NewsExtractionService()
    def create_manual(self,project_id:str,text:str,*,claim_type:str="fact",importance:str="supporting",uncertainty:str="reported",source_id:str|None=None,snapshot_id:str|None=None,evidence_text:str="",start_offset:int=-1,end_offset:int=-1,quote:dict[str,str]|None=None)->NewsClaim:
        claim=NewsClaim(project_id,text.strip(),claim_type=claim_type,importance=importance,uncertainty=uncertainty)
        if quote:
            claim.quote_text=quote.get("text",""); claim.speaker=quote.get("speaker",""); claim.quote_kind=quote.get("kind",""); claim.original_quote=quote.get("original",claim.quote_text)
        self.repository.create_claim(claim)
        if source_id and snapshot_id and evidence_text.strip():
            self.add_evidence(project_id,claim.id,source_id,snapshot_id,evidence_text,start_offset=start_offset,end_offset=end_offset)
        return claim
    def extract_candidates(self,project_id:str,source_id:str)->list[NewsClaim]:
        source=self.repository.source(project_id,source_id)
        snapshot=self.repository.latest_snapshot(project_id,source_id)
        if source is None or snapshot is None: raise NewsInvalidSource("Source content is not ready.")
        created=[]
        existing={_norm(c.text) for c in self.repository.list_claims(project_id)}
        for cand in self.extraction.candidate_claims(snapshot.content_text):
            if _norm(cand.text) in existing: continue
            quote={}
            if cand.claim_type=="quote": quote={"text":cand.evidence_text,"kind":"exact","original":cand.evidence_text}
            claim=self.create_manual(project_id,cand.text,claim_type=cand.claim_type,source_id=source_id,snapshot_id=snapshot.id,evidence_text=cand.evidence_text,start_offset=cand.start_offset,end_offset=cand.end_offset,quote=quote)
            created.append(claim); existing.add(_norm(claim.text))
        self.detect_conflicts(project_id)
        return created
    def add_evidence(self,project_id:str,claim_id:str,source_id:str,snapshot_id:str,evidence_text:str,*,start_offset:int=-1,end_offset:int=-1,evidence_type:str="support")->NewsEvidence:
        claim=self._claim(project_id,claim_id); source=self.repository.source(project_id,source_id); snap=self.repository.snapshot(snapshot_id)
        if source is None or snap is None or snap.source_id!=source_id: raise NewsInvalidSource("Evidence source or snapshot could not be found.")
        if evidence_text and evidence_text not in snap.content_text and not (start_offset>=0 and end_offset>start_offset):
            raise NewsInvalidSource("Evidence must come from the selected source snapshot.")
        e=NewsEvidence(claim.id,source_id,snapshot_id,evidence_text.strip(),start_offset,end_offset,evidence_type)
        return self.repository.create_evidence(e)
    def approve(self,project_id:str,claim_id:str,*,override_note:str="")->NewsClaim:
        claim=self._claim(project_id,claim_id); evidence=self.repository.evidence_for_claim(claim.id)
        active=[e for e in evidence if (s:=self.repository.source(project_id,e.source_id)) is not None and s.status_code!="removed"]
        if not active and not override_note.strip():
            claim.status=NewsClaimStatus.UNSUPPORTED; self.repository.update_claim(claim); raise NewsClaimUnsupported()
        if claim.status_code=="conflicting" and not override_note.strip(): raise NewsClaimConflict()
        claim.status=NewsClaimStatus.APPROVED
        if override_note.strip(): claim.metadata["approval_override_note"]=override_note.strip()
        return self.repository.update_claim(claim)
    def reject(self,project_id:str,claim_id:str)->NewsClaim:
        claim=self._claim(project_id,claim_id); claim.status=NewsClaimStatus.REJECTED; return self.repository.update_claim(claim)
    def set_locked(self,project_id:str,claim_id:str,locked:bool)->NewsClaim:
        claim=self._claim(project_id,claim_id); claim.locked=bool(locked); return self.repository.update_claim(claim)
    def edit(self,project_id:str,claim_id:str,text:str)->NewsClaim:
        claim=self._claim(project_id,claim_id)
        if claim.locked: raise NewsInvalidSource("Unlock this claim before editing it.")
        clean=text.strip()
        if not clean: raise NewsInvalidSource("Claim text cannot be empty.")
        if _norm(clean)!=_norm(claim.text):
            claim.text=clean; claim.user_modified=True
            if claim.status_code=="approved": claim.status=NewsClaimStatus.NEEDS_REVIEW
        return self.repository.update_claim(claim)
    def merge(self,project_id:str,target_id:str,source_id:str)->NewsClaim:
        target=self._claim(project_id,target_id); source=self._claim(project_id,source_id)
        if target.locked or source.locked: raise NewsInvalidSource("Unlock claims before merging them.")
        return self.repository.merge_claims(project_id,target_id,source_id)
    def resolve_conflict(self,project_id:str,claim_a_id:str,claim_b_id:str,choice:str)->tuple[NewsClaim,NewsClaim]:
        a=self._claim(project_id,claim_a_id); b=self._claim(project_id,claim_b_id)
        if choice=="keep_a":
            a=self.approve(project_id,a.id,override_note="Conflict reviewed: kept this claim."); b=self.reject(project_id,b.id)
        elif choice=="keep_b":
            b=self.approve(project_id,b.id,override_note="Conflict reviewed: kept this claim."); a=self.reject(project_id,a.id)
        elif choice=="keep_both_uncertain":
            a.uncertainty="uncertain"; b.uncertainty="uncertain"
            self.repository.update_claim(a); self.repository.update_claim(b)
            a=self.approve(project_id,a.id,override_note="Conflicting source statements retained as uncertainty.")
            b=self.approve(project_id,b.id,override_note="Conflicting source statements retained as uncertainty.")
        elif choice=="reject_both":
            a=self.reject(project_id,a.id); b=self.reject(project_id,b.id)
        else: raise NewsInvalidSource("Choose how to resolve the conflicting claims.")
        return a,b
    def possible_duplicates(self,project_id:str,threshold:float=.82)->list[tuple[str,str,float]]:
        claims=self.repository.list_claims(project_id); result=[]
        for i,a in enumerate(claims):
            if a.status_code=="rejected": continue
            for b in claims[i+1:]:
                if b.status_code=="rejected": continue
                score=SequenceMatcher(None,_norm(a.text),_norm(b.text)).ratio()
                if score>=threshold: result.append((a.id,b.id,score))
        return result
    def detect_conflicts(self,project_id:str)->list[tuple[str,str,str]]:
        claims=[c for c in self.repository.list_claims(project_id) if c.status_code not in {"rejected","unsupported"}]
        conflicts=[]
        for i,a in enumerate(claims):
            for b in claims[i+1:]:
                aw,bw=_base_words(a.text),_base_words(b.text)
                union=aw|bw; similarity=(len(aw&bw)/len(union)) if union else 0.0
                if similarity<0.45: continue
                nums_a=set(_NUM_RE.findall(a.text)); nums_b=set(_NUM_RE.findall(b.text))
                dates_a={x.casefold() for x in _DATE_TOKEN_RE.findall(a.text)}; dates_b={x.casefold() for x in _DATE_TOKEN_RE.findall(b.text)}
                kind=""
                if nums_a and nums_b and nums_a!=nums_b: kind="number"
                elif dates_a and dates_b and dates_a!=dates_b: kind="date"
                if not kind: continue
                a.status=NewsClaimStatus.CONFLICTING; b.status=NewsClaimStatus.CONFLICTING
                a.metadata.setdefault("conflicts",[]); b.metadata.setdefault("conflicts",[])
                if b.id not in a.metadata["conflicts"]: a.metadata["conflicts"].append(b.id)
                if a.id not in b.metadata["conflicts"]: b.metadata["conflicts"].append(a.id)
                self.repository.update_claim(a); self.repository.update_claim(b); conflicts.append((a.id,b.id,kind))
        return conflicts
    def search(self,project_id:str,query:str)->list[NewsClaim]:
        q=(query or "").strip().casefold(); claims=self.repository.list_claims(project_id)
        if not q:return claims
        result=[]
        for c in claims:
            hay=[c.text,c.notes]
            for e in self.repository.evidence_for_claim(c.id):
                hay.append(e.evidence_text); src=self.repository.source(project_id,e.source_id); hay.append(src.title if src else "")
            if q in " ".join(hay).casefold():result.append(c)
        return result
    def _claim(self,project_id:str,claim_id:str)->NewsClaim:
        item=self.repository.claim(project_id,claim_id)
        if item is None: raise NewsInvalidSource("Claim could not be found.")
        return item

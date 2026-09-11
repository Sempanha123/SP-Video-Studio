from __future__ import annotations
from collections import defaultdict

from domain.news_brief import NewsBrief, NewsBriefItem
from services.news_errors import NewsBriefInvalid
from services.news_validation_service import source_fingerprint
from storage.repositories.news_repository import NewsRepository

SECTION_ORDER=("lead","what_happened","key_details","background","why_it_matters","what_happens_next")

class NewsBriefService:
    def __init__(self,repository:NewsRepository)->None:self.repository=repository
    def create_from_approved(self,project_id:str,*,title:str="News Brief")->NewsBrief:
        claims=[c for c in self.repository.list_claims(project_id) if c.status_code=="approved"]
        if not claims: raise NewsBriefInvalid("Approve at least one supported claim first.")
        brief=NewsBrief(project_id,title=title,source_fingerprint=source_fingerprint(self.repository,project_id))
        items=[]; counters=defaultdict(int)
        for index,claim in enumerate(sorted(claims,key=lambda x:({"primary":0,"supporting":1,"background":2}.get(x.importance,1),x.created_at))):
            if index==0: section="lead"
            elif claim.importance=="background" or claim.claim_type=="background": section="background"
            elif claim.claim_type in {"date","event","identity","location"}: section="what_happened"
            elif claim.importance=="primary": section="key_details"
            else: section="key_details"
            items.append(NewsBriefItem(brief.id,section,claim.id,order=counters[section])); counters[section]+=1
        brief.summary="\n".join(c.text for c in claims[:3]); self.repository.create_brief(brief,items); return brief
    def get(self,project_id:str,brief_id:str)->tuple[NewsBrief,list[NewsBriefItem]]:
        brief=self.repository.brief(project_id,brief_id)
        if brief is None: raise NewsBriefInvalid("News Brief could not be found.")
        current=source_fingerprint(self.repository,project_id)
        if brief.source_fingerprint!=current and brief.status!="draft": brief.status="outdated"; self.repository.update_brief(brief)
        return brief,self.repository.brief_items(brief.id)
    def move_item(self,project_id:str,brief_id:str,item_id:str,section_key:str,order:int=0)->NewsBriefItem:
        brief,_=self.get(project_id,brief_id)
        if section_key not in SECTION_ORDER: raise NewsBriefInvalid("Unsupported brief section.")
        item=self.repository.update_brief_item_section(brief.id,item_id,section_key,order)
        brief.status="draft"; self.repository.update_brief(brief); return item
    def set_status(self,project_id:str,brief_id:str,status:str)->NewsBrief:
        brief,_=self.get(project_id,brief_id)
        if status not in {"draft","review","approved"}: raise NewsBriefInvalid("Unsupported brief status.")
        brief.status=status; return self.repository.update_brief(brief)

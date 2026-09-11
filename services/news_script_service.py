from __future__ import annotations
import hashlib
import re
from collections import defaultdict

from domain.director_plan import DirectorRequest
from domain.news_script_mapping import NewsScriptMapping
from domain.project import utc_now_iso
from domain.script_section import ScriptSection, ScriptSectionType
from engines.news.deterministic import DeterministicNewsScriptProvider
from services.news_brief_service import NewsBriefService
from services.news_errors import NewsBriefInvalid, NewsScriptGroundingError
from services.news_validation_service import NewsValidationService, source_fingerprint
from services.script_service import ScriptService
from storage.repositories.news_repository import NewsRepository

_SENTENCE_SPLIT=re.compile(r"(?<=[.!?។!?])\s+|\n{2,}",re.UNICODE)

def _norm(text:str)->str:return " ".join((text or "").casefold().split())

class NewsScriptService:
    def __init__(self,repository:NewsRepository,script_service:ScriptService,brief_service:NewsBriefService,
                 validation:NewsValidationService,provider:DeterministicNewsScriptProvider|None=None,
                 translation_service=None,scene_service=None,director_service=None)->None:
        self.repository=repository; self.script_service=script_service; self.brief_service=brief_service; self.validation=validation
        self.provider=provider or DeterministicNewsScriptProvider(); self.translation_service=translation_service; self.scene_service=scene_service; self.director_service=director_service
    def build_script(self,project_id:str,*,brief_id:str|None=None,style:str="straight_news",replace_existing:bool=True):
        approved=[c for c in self.repository.list_claims(project_id) if c.status_code=="approved"]
        if not approved: raise NewsBriefInvalid("Approve supported claims before building a News script.")
        brief=None
        if brief_id:
            b,items=self.brief_service.get(project_id,brief_id); brief={"brief":b.to_dict(),"items":[x.to_dict() for x in items]}
            allowed={x.claim_id for x in items if x.claim_id}; approved=[c for c in approved if c.id in allowed]
        script,existing=self.script_service.load_or_create(project_id)
        if not replace_existing and any(s.content.strip() for s in existing): raise NewsScriptGroundingError("The current script already contains text. Choose Replace explicitly.")
        draft=self.provider.generate_news_script(approved_claims=[c.to_dict() for c in approved],brief=brief,style=style,duration_ms=60_000,language=script.language)
        if not draft.sections: raise NewsBriefInvalid("No approved claims are available for the script.")
        sections=[]; mappings=[]; claim_by_id={c.id:c for c in approved}
        for order,(title,text,claim_ids) in enumerate(draft.sections):
            section_type=ScriptSectionType.HOOK if order==0 else ScriptSectionType.BODY
            sec=ScriptSection(script.id,order,section_type,title,content=text,metadata={"news":True,"news_style":style,"news_claim_ids":list(claim_ids),"scene_source":True})
            sections.append(sec)
            for idx,cid in enumerate(claim_ids):
                claim=claim_by_id.get(cid)
                if claim is None: continue
                mappings.append(NewsScriptMapping(project_id,script.id,sec.id,claim.text,[cid],sentence_key=f"{sec.id}:{idx}",mapping_type="factual",status="grounded"))
        # Keep a short generic closing when the workflow has facts to close; it is connective, not factual.
        outro=ScriptSection(script.id,len(sections),ScriptSectionType.OUTRO,"Outro",content="Here is what we know so far.",metadata={"news":True,"scene_source":True})
        sections.append(outro)
        mappings.append(NewsScriptMapping(project_id,script.id,outro.id,outro.content,[],sentence_key=f"{outro.id}:0",mapping_type="connective",status="grounded"))
        self.script_service.repository.replace_sections(project_id,script.id,sections)
        script.metadata.update({"news_grounded":True,"news_style":style,"news_brief_id":brief_id or "","news_source_fingerprint":source_fingerprint(self.repository,project_id)})
        script.status="review"; self.script_service.save_script(script)
        self.repository.replace_script_mappings(project_id,script.id,mappings)
        return script,sections,mappings
    def validate_grounding(self,project_id:str,script_id:str|None=None)->dict[str,object]:
        script= self.script_service.repository.get_primary_by_project(project_id) if script_id is None else self.script_service.repository.get_by_id(script_id)
        if script is None or script.project_id!=project_id: raise NewsScriptGroundingError("News script could not be found.")
        sections=self.script_service.repository.list_sections(script.id); existing=self.repository.mappings(project_id,script.id)
        by_section=defaultdict(list)
        for m in existing: by_section[m.script_section_id].append(m)
        rebuilt=[]; unsupported=[]; needs_review=[]; grounded=[]
        for sec in sections:
            mapped=by_section.get(sec.id,[]); current=sec.content or ""
            covered=[]
            for m in mapped:
                if m.mapping_type=="connective":
                    m.status="grounded" if _norm(m.text_snapshot) in _norm(current) else "needs_review"
                else:
                    m.status="grounded" if _norm(m.text_snapshot) in _norm(current) and all((c:=self.repository.claim(project_id,cid)) is not None and c.status_code=="approved" for cid in m.claim_ids) else "needs_review"
                (grounded if m.status=="grounded" else needs_review).append(m)
                rebuilt.append(m); covered.append(_norm(m.text_snapshot))
            for idx,sentence in enumerate(x.strip() for x in _SENTENCE_SPLIT.split(current) if x.strip()):
                n=_norm(sentence)
                if any(n==x or n in x or x in n for x in covered if x): continue
                if self.validation.is_connective(sentence):
                    m=NewsScriptMapping(project_id,script.id,sec.id,sentence,[],sentence_key=f"{sec.id}:new:{idx}",mapping_type="connective",status="grounded")
                    grounded.append(m)
                elif self.validation.looks_factual(sentence):
                    m=NewsScriptMapping(project_id,script.id,sec.id,sentence,[],sentence_key=f"{sec.id}:unsupported:{idx}",mapping_type="factual",status="unsupported")
                    unsupported.append(m)
                else:
                    m=NewsScriptMapping(project_id,script.id,sec.id,sentence,[],sentence_key=f"{sec.id}:note:{idx}",mapping_type="connective",status="grounded")
                    grounded.append(m)
                rebuilt.append(m)
        self.repository.replace_script_mappings(project_id,script.id,rebuilt)
        script.metadata["news_grounding_status"]="unsupported" if unsupported else ("needs_review" if needs_review else "grounded")
        self.script_service.save_script(script)
        return {"status":script.metadata["news_grounding_status"],"grounded":len(grounded),"needsReview":len(needs_review),"unsupported":len(unsupported),"mappings":[m.to_dict() for m in rebuilt]}
    def create_translation(self,project_id:str,target_language:str,*,engine_id:str="manual"):
        if self.translation_service is None: raise NewsScriptGroundingError("Translation service is unavailable.")
        script,_=self.script_service.load_or_create(project_id); report=self.validate_grounding(project_id,script.id)
        if report["unsupported"]: raise NewsScriptGroundingError()
        translation=self.translation_service.create_from_script(project_id,script.id,target_language,engine_id=engine_id)
        translation.metadata["news_claim_provenance"]=[m.to_dict() for m in self.repository.mappings(project_id,script.id) if m.claim_ids]
        self.translation_service.repository.update_translation(translation); return translation
    def create_scenes(self,project_id:str,*,append:bool=False):
        if self.scene_service is None: raise NewsScriptGroundingError("Scene service is unavailable.")
        script,_=self.script_service.load_or_create(project_id); report=self.validate_grounding(project_id,script.id)
        if report["unsupported"]: raise NewsScriptGroundingError()
        scenes=self.scene_service.create_from_script(project_id,append=append)
        for scene in scenes:
            if scene.script_section_id:
                sec=self.script_service.repository.get_section(scene.script_section_id)
                title=(sec.title if sec else scene.name).casefold()
                role="lead" if "hook" in title or "lead" in title else ("background" if "background" in title else ("outro" if "outro" in title else "context"))
                scene.metadata["news_role"]=role; scene.metadata["news_source_fingerprint"]=source_fingerprint(self.repository,project_id); self.scene_service.repository.update(scene)
        return scenes
    def create_director_plan(self,project_id:str):
        if self.director_service is None: raise NewsScriptGroundingError("AI Director is unavailable.")
        script,_=self.script_service.load_or_create(project_id); report=self.validate_grounding(project_id,script.id)
        if report["unsupported"]: raise NewsScriptGroundingError()
        meta=self.repository.get_project(project_id); project=self.script_service.project_repository.get_by_id(project_id)
        req=DirectorRequest(project_id=project_id,workflow="news",content_source_type="script",content_source_id=script.id,language=script.language,platform=(meta.platform if meta else "generic"),target_duration_ms=(meta.target_duration_ms if meta else 60_000),style="news",pace="balanced",tone="neutral",metadata={"newsGrounded":True,"sourceFingerprint":source_fingerprint(self.repository,project_id)})
        return self.director_service.create_plan(req)

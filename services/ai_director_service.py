from __future__ import annotations

import hashlib
import json
import logging
from copy import deepcopy
from typing import Any
from uuid import uuid4

from domain.director_plan import DirectorPlan, DirectorPlanStatus, DirectorRequest
from domain.director_recommendation import DirectorRecommendation
from domain.director_scene_plan import DirectorScenePlan
from domain.project import utc_now_iso
from engines.llm.deterministic_director import DeterministicDirectorProvider
from engines.llm.errors import DirectorInvalidRequest, DirectorPlanValidationError, DirectorSourceMissing
from services.director_validation_service import DirectorValidationService
from services.script_analysis_service import ScriptAnalysisService
from storage.repositories.director_plan_repository import DirectorPlanRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")).hexdigest()


class AIDirectorService:
    def __init__(self, repository: DirectorPlanRepository, project_repository: ProjectRepository,
                 script_repository: ScriptRepository, transcript_repository: TranscriptRepository,
                 translation_repository: TranslationRepository, scene_repository: SceneRepository,
                 media_repository: MediaRepository, script_analysis: ScriptAnalysisService,
                 provider: DeterministicDirectorProvider, validation: DirectorValidationService,
                 logger: logging.Logger | None=None) -> None:
        self.repository=repository; self.project_repository=project_repository; self.script_repository=script_repository
        self.transcript_repository=transcript_repository; self.translation_repository=translation_repository
        self.scene_repository=scene_repository; self.media_repository=media_repository; self.script_analysis=script_analysis
        self.provider=provider; self.validation=validation; self.logger=logger or logging.getLogger("sp_video_studio.director")

    def create_plan(self, request: DirectorRequest) -> tuple[DirectorPlan,list[DirectorScenePlan]]:
        try: request.validate()
        except ValueError as exc: raise DirectorInvalidRequest(str(exc)) from exc
        project=self._project(request.project_id)
        context=self._context(request,project)
        plan,scenes=self.provider.create_plan(request,context)
        issues=self.validation.validate(plan,scenes)
        if any(i.severity=="error" for i in issues): raise DirectorPlanValidationError(issues[0].message)
        plan.metadata["readiness"]=self.validation.readiness(plan,scenes)
        plan.metadata["validationIssues"]=[i.to_dict() for i in issues]
        self.repository.create(plan,scenes); self.logger.info("Director plan created: %s",plan.id); return plan,scenes

    def list_plans(self, project_id:str)->list[DirectorPlan]:
        self._project(project_id); plans=self.repository.list_for_project(project_id)
        for plan in plans:self._mark_outdated(plan,persist=True)
        return plans

    def get(self, project_id:str, plan_id:str)->tuple[DirectorPlan,list[DirectorScenePlan]]:
        plan=self.repository.get_owned(project_id,plan_id)
        if plan is None: raise DirectorSourceMissing("Director plan could not be found.")
        self._mark_outdated(plan,persist=True)
        return plan,self.repository.scenes(plan_id)

    def source_options(self, project_id:str)->dict[str,list[dict[str,object]]]:
        project=self._project(project_id); result={"script":[],"transcript":[],"translation":[],"scenes":[]}
        script=self.script_repository.get_primary_by_project(project_id)
        if script: result["script"].append({"id":script.id,"name":script.title,"language":script.language,"updatedAt":script.updated_at})
        for item in self.transcript_repository.list_for_project(project_id):
            result["transcript"].append({"id":item.id,"name":f"Transcript • {item.detected_language or item.language_mode}","language":item.detected_language or item.language_mode,"updatedAt":item.updated_at,"status":item.status_code})
        for item in self.translation_repository.list_for_project(project_id):
            result["translation"].append({"id":item.id,"name":f"{item.source_language.upper()} → {item.target_language.upper()} Translation","language":item.target_language,"updatedAt":item.updated_at,"status":item.status_code})
        scenes=self.scene_repository.list_for_project(project_id)
        if scenes: result["scenes"].append({"id":"project-scenes","name":f"Existing Scenes ({len(scenes)})","language":project.language,"updatedAt":project.updated_at})
        return result

    def edit_recommendation(self, project_id:str, plan_id:str, category:str, value:object)->DirectorPlan:
        plan,scenes=self.get(project_id,plan_id); item=plan.recommendation(category)
        if item is None: raise DirectorInvalidRequest("Recommendation could not be found.")
        item.value=value; item.user_modified=True; plan.updated_at=utc_now_iso()
        if category=="format": plan.aspect_ratio=str(value)
        if category=="scenes":
            try: count=int(value)
            except (TypeError,ValueError) as exc: raise DirectorInvalidRequest("Scene count must be a number.") from exc
            if not 1 <= count <= 60: raise DirectorInvalidRequest("Scene count must be between 1 and 60.")
            item.value=count; plan.metadata["requestedSceneCount"]=count
            scenes=self._resize_scene_plans(plan,scenes,count)
            self.repository.replace_scenes(project_id,plan_id,scenes)
        self._revalidate(plan,scenes); return self.repository.update(plan)

    def lock_recommendation(self, project_id:str, plan_id:str, category:str, locked:bool)->DirectorPlan:
        plan,scenes=self.get(project_id,plan_id); item=plan.recommendation(category)
        if item is None: raise DirectorInvalidRequest("Recommendation could not be found.")
        item.locked=bool(locked); return self.repository.update(plan)

    def update_scene_plan(self, project_id:str, plan_id:str, scene_id:str, *, title:str|None=None,duration_ms:int|None=None,locked:bool|None=None)->DirectorScenePlan:
        plan,scenes=self.get(project_id,plan_id); item=next((s for s in scenes if s.id==scene_id),None)
        if item is None: raise DirectorInvalidRequest("Planned scene could not be found.")
        if title is not None:
            if not title.strip(): raise DirectorInvalidRequest("Scene title is required.")
            item.title=title.strip(); item.user_modified=True
        if duration_ms is not None:
            if int(duration_ms)<=0: raise DirectorInvalidRequest("Scene duration must be greater than zero.")
            item.target_duration_ms=int(duration_ms); item.user_modified=True
        if locked is not None:item.locked=bool(locked)
        self.repository.update_scene(project_id,item); self._revalidate(plan,self.repository.scenes(plan_id)); self.repository.update(plan); return item

    def regenerate(self, project_id:str, plan_id:str, section:str="all_unlocked")->tuple[DirectorPlan,list[DirectorScenePlan],dict[str,object]]:
        old,old_scenes=self.get(project_id,plan_id)
        req=self._request_from_plan(old); context=self._context(req,self._project(project_id)); fresh,fresh_scenes=self.provider.create_plan(req,context)
        fresh.plan_id=old.id; fresh.created_at=old.created_at; fresh.version=old.version+1
        categories=None if section=="all_unlocked" else {section}
        fresh_by={r.category:r for r in fresh.recommendations}
        merged=[]; changes={}
        for current in old.recommendations:
            candidate=fresh_by.get(current.category,current)
            should_replace=not current.locked and (categories is None or current.category in categories)
            if current.user_modified and categories is None: should_replace=False
            chosen=candidate if should_replace else current
            if should_replace and chosen.value!=current.value: changes[current.category]={"previous":current.value,"new":chosen.value}
            merged.append(chosen)
        fresh.recommendations=merged; fresh.aspect_ratio=str(fresh.recommendation("format").value if fresh.recommendation("format") else old.aspect_ratio)
        fresh.metadata={**fresh.metadata,"previousVersion":old.version,"comparison":changes}
        if section in {"scenes","all_unlocked"}:
            by_order={s.order:s for s in old_scenes}
            for item in fresh_scenes:
                prior=by_order.get(item.order)
                if prior and (prior.locked or prior.user_modified):
                    item=deepcopy(prior); item.plan_id=old.id
                else:item.plan_id=old.id
                by_order[item.order]=item
            final_scenes=[by_order[i] for i in sorted(by_order) if i < len(fresh_scenes)]
        else: final_scenes=old_scenes
        self._revalidate(fresh,final_scenes); self.repository.update(fresh); self.repository.replace_scenes(project_id,old.id,final_scenes)
        self.logger.info("Director plan regenerated: %s",old.id); return fresh,final_scenes,changes

    def refresh_from_source(self, project_id:str, plan_id:str)->tuple[DirectorPlan,list[DirectorScenePlan]]:
        plan,_=self.get(project_id,plan_id); plan.status=DirectorPlanStatus.REVIEW
        result=self.regenerate(project_id,plan_id,"all_unlocked"); return result[0],result[1]

    def approve(self, project_id:str, plan_id:str, allow_warnings:bool=True)->DirectorPlan:
        plan,scenes=self.get(project_id,plan_id); issues=self.validation.validate(plan,scenes)
        if any(i.severity=="error" for i in issues): raise DirectorPlanValidationError("This production plan contains structural errors.")
        if issues and not allow_warnings: raise DirectorPlanValidationError("This production plan still needs review.")
        plan.status=DirectorPlanStatus.APPROVED; return self.repository.update(plan)

    def mark_applied(self, project_id:str, plan_id:str)->DirectorPlan:
        plan,scenes=self.get(project_id,plan_id); plan.status=DirectorPlanStatus.APPLIED; self.repository.set_active(project_id,plan_id); return self.repository.update(plan)

    def duplicate_plan(self, project_id:str, plan_id:str)->DirectorPlan:
        source,scenes=self.get(project_id,plan_id); clone=deepcopy(source); clone.plan_id=str(uuid4()); clone.request_id=str(uuid4()); clone.version=1; clone.status=DirectorPlanStatus.DRAFT; clone.created_at=clone.updated_at=utc_now_iso(); clone.metadata={**clone.metadata,"duplicatedFrom":source.id}
        recs=[]
        for r in source.recommendations:
            item=deepcopy(r); item.recommendation_id=str(uuid4()); recs.append(item)
        clone.recommendations=recs; new_scenes=[]
        for s in scenes:
            item=deepcopy(s); item.scene_plan_id=str(uuid4()); item.plan_id=clone.id; new_scenes.append(item)
        self.repository.create(clone,new_scenes); return clone

    def delete_plan(self, project_id:str, plan_id:str)->None:self.repository.delete(project_id,plan_id)

    def voice_matches(self, plan:DirectorPlan, voice_service)->list[dict[str,object]]:
        rec=plan.recommendation("voice"); category=str(rec.value if rec else "")
        voices=[v for v in voice_service.list_all() if v.language==plan.language and (not category or v.category.casefold()==category.casefold() or category.casefold() in [t.casefold() for t in v.style_tags])]
        return [v.to_dict() for v in voices[:8]]

    def duplicate_project_plans(self, source_project_id:str,target_project_id:str,*,script_map:dict[str,str]|None=None,script_section_map:dict[str,str]|None=None,transcript_map:dict[str,str]|None=None,translation_map:dict[str,str]|None=None,scene_map:dict[str,str]|None=None)->dict[str,str]:
        maps=[script_map or {},script_section_map or {},transcript_map or {},translation_map or {},scene_map or {}]; script_map,script_section_map,transcript_map,translation_map,scene_map=maps
        result={}; active_source=self.repository.active_id(source_project_id)
        for source in self.repository.list_for_project(source_project_id):
            clone=deepcopy(source); clone.plan_id=str(uuid4()); clone.project_id=target_project_id; clone.request_id=str(uuid4()); clone.created_at=clone.updated_at=utc_now_iso()
            if clone.source_type=="script": clone.source_id=script_map.get(clone.source_id,"")
            elif clone.source_type=="transcript": clone.source_id=transcript_map.get(clone.source_id,"")
            elif clone.source_type=="translation": clone.source_id=translation_map.get(clone.source_id,"")
            elif clone.source_type=="scenes": clone.source_id="project-scenes"
            new_recs=[]
            for r in clone.recommendations:
                item=deepcopy(r); item.recommendation_id=str(uuid4()); new_recs.append(item)
            clone.recommendations=new_recs; scene_items=[]
            for item in self.repository.scenes(source.id):
                copied=deepcopy(item); copied.scene_plan_id=str(uuid4()); copied.plan_id=clone.id; copied.script_section_id=script_section_map.get(copied.script_section_id,"") if copied.script_section_id else ""; scene_items.append(copied)
            self.repository.create(clone,scene_items); result[source.id]=clone.id
        if active_source and active_source in result:self.repository.set_active(target_project_id,result[active_source])
        return result

    def _resize_scene_plans(self, plan:DirectorPlan, current:list[DirectorScenePlan], count:int)->list[DirectorScenePlan]:
        req=self._request_from_plan(plan)
        dist=self.provider.rules.scene_distribution(req,preferred_count=count)
        titles=self.provider.rules.scene_titles(plan.workflow,count)
        old_by_order={item.order:item for item in current}
        result=[]
        for i,duration in enumerate(dist.durations_ms):
            prior=old_by_order.get(i)
            if prior is not None:
                item=deepcopy(prior); item.plan_id=plan.id; item.order=i
                if not item.locked and not item.user_modified:
                    item.title=titles[i][0]; item.purpose=titles[i][1]; item.target_duration_ms=duration
            else:
                voice=str(plan.recommendation("voice").value if plan.recommendation("voice") else "")
                subtitle=str(plan.recommendation("subtitles").value if plan.recommendation("subtitles") else "clean")
                visual=str(plan.recommendation("visuals").value if plan.recommendation("visuals") else "mixed_media")
                transition=str(plan.recommendation("transitions").value if plan.recommendation("transitions") else "cut")
                item=DirectorScenePlan(plan.id,i,titles[i][0],titles[i][1],duration,visual_type=visual,visual_description="Use relevant project media or a supporting visual that matches this scene's purpose.",overlay_recommendation="Key phrase" if plan.workflow in {"news","shorts"} else "",voice_style=voice,subtitle_style=subtitle,transition=transition,metadata={"ruleEngineVersion":plan.rule_engine_version})
            result.append(item)
        unlocked=[x for x in result if not x.locked and not x.user_modified]
        delta=plan.target_duration_ms-sum(x.target_duration_ms for x in result)
        if delta and unlocked:
            unlocked[-1].target_duration_ms=max(500,unlocked[-1].target_duration_ms+delta)
        return result

    def _request_from_plan(self, plan:DirectorPlan)->DirectorRequest:
        m=plan.metadata
        return DirectorRequest(project_id=plan.project_id,workflow=plan.workflow,content_source_type=plan.source_type,content_source_id=plan.source_id,content_text=str(m.get("idea") or ""),language=plan.language,platform=plan.platform,target_duration_ms=plan.target_duration_ms,audience=str(m.get("audience") or "general"),style=str(m.get("style") or "modern"),pace=str(m.get("pace") or "balanced"),tone=str(m.get("tone") or "neutral"),aspect_ratio_mode="auto")

    def _context(self,request:DirectorRequest,project)->dict[str,Any]:
        context={"project_aspect_ratio":project.aspect_ratio,"media_counts":self._media_counts(project.id)}
        st=request.content_source_type
        if st=="idea":
            context["source_fingerprint"]=_sha({"idea":request.content_text,"language":request.language}); context["source_summary"]={"characters":len(request.content_text)}
        elif st=="script":
            script=self.script_repository.get_by_id(request.content_source_id)
            if script is None or script.project_id!=project.id: raise DirectorSourceMissing("The selected script is no longer available.")
            sections=[s for s in self.script_repository.list_sections(script.id) if s.enabled]
            context["script_sections"]=[{"id":s.id,"title":s.title,"text":s.content,"order":s.order} for s in sections]
            analysis=self.script_analysis.analyze_sections(sections,script.language,str(script.pace)); context["script_estimated_duration_ms"]=analysis.estimated_duration_ms
            context["source_fingerprint"]=_sha([(s.id,s.order,s.title,s.content,s.enabled) for s in sections]); context["source_summary"]={"sections":len(sections),"estimatedDurationMs":analysis.estimated_duration_ms}
        elif st=="transcript":
            item=self.transcript_repository.get(request.content_source_id)
            if item is None or item.project_id!=project.id: raise DirectorSourceMissing("The selected transcript is no longer available.")
            segments=self.transcript_repository.segments(item.id); context["source_fingerprint"]=_sha([(s.id,s.start_ms,s.end_ms,s.text) for s in segments]); context["source_summary"]={"segments":len(segments),"durationMs":item.duration_ms,"language":item.detected_language or item.language_mode,"speechDensity":round(sum(max(0,s.end_ms-s.start_ms) for s in segments)/max(1,item.duration_ms),3)}
        elif st=="translation":
            item=self.translation_repository.get(request.content_source_id)
            if item is None or item.project_id!=project.id: raise DirectorSourceMissing("The selected translation is no longer available.")
            segments=self.translation_repository.segments(item.id); context["source_fingerprint"]=_sha([(s.id,s.order,s.translated_text,s.reviewed,s.locked) for s in segments]); context["source_summary"]={"segments":len(segments),"sourceLanguage":item.source_language,"targetLanguage":item.target_language,"reviewed":sum(1 for s in segments if s.reviewed)}
        elif st=="scenes":
            scenes=self.scene_repository.list_for_project(project.id); context["source_fingerprint"]=_sha([(s.id,s.order,s.duration_ms,s.name,s.enabled,s.updated_at) for s in scenes]); context["scene_count"]=len(scenes); context["scene_duration_ms"]=sum(s.duration_ms for s in scenes if s.enabled); context["source_summary"]={"sceneCount":len(scenes),"durationMs":context["scene_duration_ms"]}
        return context

    def _current_source_fingerprint(self,plan:DirectorPlan)->str:
        try:return str(self._context(self._request_from_plan(plan),self._project(plan.project_id)).get("source_fingerprint") or "")
        except DirectorSourceMissing:return "missing"

    def _mark_outdated(self,plan:DirectorPlan,*,persist:bool)->bool:
        current=self._current_source_fingerprint(plan)
        outdated=bool(plan.source_fingerprint and current!=plan.source_fingerprint)
        if outdated and plan.status_code!=DirectorPlanStatus.OUTDATED.value:
            plan.status=DirectorPlanStatus.OUTDATED
            if persist:self.repository.update(plan)
        return outdated

    def _revalidate(self,plan:DirectorPlan,scenes:list[DirectorScenePlan])->None:
        issues=self.validation.validate(plan,scenes); plan.metadata["validationIssues"]=[i.to_dict() for i in issues]; plan.metadata["readiness"]=self.validation.readiness(plan,scenes)
        if any(i.severity=="error" for i in issues):raise DirectorPlanValidationError(issues[0].message)

    def _media_counts(self,project_id:str)->dict[str,int]:
        result={"video":0,"image":0,"audio":0}
        for item in self.media_repository.list_by_project(project_id): result[item.type]=result.get(item.type,0)+1
        return result

    def _project(self,project_id:str):
        project=self.project_repository.get_by_id(project_id)
        if project is None:raise DirectorSourceMissing("Project could not be found.")
        return project

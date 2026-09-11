from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from domain.director_plan import DirectorRequest
from services.ai_director_service import AIDirectorService
from services.director_apply_service import DirectorApplyService
from services.voice_service import VoiceService


class AIDirectorController(QObject):
    contextChanged=Signal(); plansChanged=Signal(); planChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str)

    def __init__(self, service:AIDirectorService, apply_service:DirectorApplyService, voice_service:VoiceService, logger=None, parent=None):
        super().__init__(parent); self.service=service; self.apply_service=apply_service; self.voice_service=voice_service
        self.logger=logger or logging.getLogger("sp_video_studio.director_controller")
        self._project_id=""; self._plan_id=""; self._plans:list[dict[str,object]]=[]; self._plan:dict[str,object]={}; self._scenes:list[dict[str,object]]=[]; self._impact:dict[str,object]={}; self._comparison:dict[str,object]={}

    @Property(str,notify=contextChanged)
    def currentProjectId(self): return self._project_id
    @Property('QVariantList',notify=plansChanged)
    def plans(self): return self._plans
    @Property('QVariantMap',notify=planChanged)
    def plan(self): return self._plan
    @Property('QVariantList',notify=planChanged)
    def scenePlans(self): return self._scenes
    @Property('QVariantMap',notify=planChanged)
    def applyImpact(self): return self._impact
    @Property('QVariantMap',notify=planChanged)
    def comparison(self): return self._comparison
    @Property('QVariantMap',notify=contextChanged)
    def sourceOptions(self):
        if not self._project_id:return {"script":[],"transcript":[],"translation":[],"scenes":[]}
        try:return self.service.source_options(self._project_id)
        except Exception:return {"script":[],"transcript":[],"translation":[],"scenes":[]}
    @Property('QVariantList',notify=planChanged)
    def voiceMatches(self):
        if not self._plan_id:return []
        try:
            plan,_=self.service.get(self._project_id,self._plan_id); return self.service.voice_matches(plan,self.voice_service)
        except Exception:return []

    @Slot(str)
    def setCurrentProject(self, project_id:str):
        value=(project_id or '').strip()
        if value==self._project_id:return
        self._project_id=value; self._plan_id=""; self.contextChanged.emit(); self.refresh()

    @Slot()
    def refresh(self):
        if not self._project_id:
            self._plans=[]; self._plan={}; self._scenes=[]; self._impact={}; self.plansChanged.emit(); self.planChanged.emit(); return
        try:
            plans=self.service.list_plans(self._project_id)
            active=self.service.repository.active_id(self._project_id)
            self._plans=[{**p.to_dict(),"active":p.id==active,"sceneCount":len(self.service.repository.scenes(p.id))} for p in plans]
            if not self._plan_id and plans:self._plan_id=active or plans[0].id
            if self._plan_id and not any(p.id==self._plan_id for p in plans):self._plan_id=plans[0].id if plans else ""
            self._load_current(); self.plansChanged.emit()
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def selectPlan(self, plan_id:str): self._plan_id=plan_id; self._load_current()

    @Slot(str,str,str,str,str,str,int,str,str,str,str,result=bool)
    def createPlan(self,workflow:str,source_type:str,source_id:str,idea:str,platform:str,language:str,duration_ms:int,audience:str,style:str,pace:str,tone:str):
        try:
            req=DirectorRequest(project_id=self._project_id,workflow=workflow,content_source_type=source_type,content_source_id=source_id,content_text=idea,language=language,platform=platform,target_duration_ms=int(duration_ms),audience=audience,style=style,pace=pace,tone=tone)
            plan,_=self.service.create_plan(req); self._plan_id=plan.id; self._comparison={}; self.refresh(); self.operationSucceeded.emit("Production plan created"); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(str,'QVariant',result=bool)
    def editRecommendation(self,category:str,value):
        try:self.service.edit_recommendation(self._project_id,self._plan_id,category,value); self._load_current(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,bool,result=bool)
    def lockRecommendation(self,category:str,locked:bool):
        try:self.service.lock_recommendation(self._project_id,self._plan_id,category,locked); self._load_current(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,result=bool)
    def regenerate(self,section:str="all_unlocked"):
        try:
            _,_,changes=self.service.regenerate(self._project_id,self._plan_id,section); self._comparison=changes; self.refresh(); self.operationSucceeded.emit("Recommendations refreshed"); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,str,int,bool,result=bool)
    def updateScenePlan(self,scene_id:str,title:str,duration_ms:int,locked:bool):
        try:self.service.update_scene_plan(self._project_id,self._plan_id,scene_id,title=title,duration_ms=duration_ms,locked=locked); self._load_current(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def approve(self):
        try:self.service.approve(self._project_id,self._plan_id,True); self.refresh(); self.operationSucceeded.emit("Plan approved"); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,str,result=bool)
    def apply(self,mode:str,voice_id:str=""):
        try:
            self.apply_service.apply(self._project_id,self._plan_id,mode=mode,voice_id=voice_id); self.refresh(); self.operationSucceeded.emit("Plan applied"); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def duplicatePlan(self):
        try:item=self.service.duplicate_plan(self._project_id,self._plan_id); self._plan_id=item.id; self.refresh(); self.operationSucceeded.emit("Plan duplicated"); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def deletePlan(self):
        try:self.service.delete_plan(self._project_id,self._plan_id); self._plan_id=""; self.refresh(); self.operationSucceeded.emit("Plan deleted"); return True
        except Exception as exc:self._fail(exc); return False

    def _load_current(self):
        if not self._plan_id:
            self._plan={}; self._scenes=[]; self._impact={}; self.planChanged.emit(); return
        try:
            plan,scenes=self.service.get(self._project_id,self._plan_id); self._plan=plan.to_dict(); self._scenes=[s.to_dict() for s in scenes]; self._impact=self.apply_service.impact(self._project_id,self._plan_id); self.planChanged.emit()
        except Exception as exc:self._fail(exc)
    def _fail(self,exc):self.logger.exception("Director action failed"); self.operationFailed.emit(str(exc) or "AI Director action could not be completed.")

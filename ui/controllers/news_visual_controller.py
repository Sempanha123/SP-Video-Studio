from __future__ import annotations
import logging
from PySide6.QtCore import QObject,Property,Signal,Slot
from services.news_visual_service import NewsVisualService

class NewsVisualController(QObject):
    contextChanged=Signal(); scenesChanged=Signal(); visualChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str); navigationRequested=Signal(str)
    def __init__(self,service:NewsVisualService,logger=None,parent=None):
        super().__init__(parent);self.service=service;self.logger=logger or logging.getLogger('sp_video_studio.news_visual_controller');self._project_id='';self._scene_id='';self._theme={};self._scenes=[];self._visual={};self._readiness={}
    @Property(str,notify=contextChanged)
    def currentProjectId(self):return self._project_id
    @Property(str,notify=visualChanged)
    def currentSceneId(self):return self._scene_id
    @Property('QVariantMap',notify=contextChanged)
    def theme(self):return self._theme
    @Property('QVariantList',constant=True)
    def builtinThemes(self):return self.service.builtin_themes()
    @Property('QVariantList',constant=True)
    def layouts(self):return self.service.builtin_layouts()
    @Property('QVariantList',constant=True)
    def graphicPresets(self):return self.service.builtin_graphics()
    @Property('QVariantList',notify=scenesChanged)
    def scenes(self):return self._scenes
    @Property('QVariantMap',notify=visualChanged)
    def currentVisual(self):return self._visual
    @Property('QVariantList',notify=visualChanged)
    def elements(self):return list(self._visual.get('elements',[]) or [])
    @Property('QVariantMap',notify=contextChanged)
    def readiness(self):return self._readiness
    @Property(bool,notify=contextChanged)
    def canUndo(self):return self.service.can_undo()
    @Property(bool,notify=contextChanged)
    def canRedo(self):return self.service.can_redo()
    @Property('QVariantList',notify=contextChanged)
    def approvedClaims(self):
        if not self._project_id:return []
        return [c.to_dict() for c in self.service.news_repository.list_claims(self._project_id) if c.status_code=='approved']
    @Property('QVariantList',notify=contextChanged)
    def sources(self):
        if not self._project_id:return []
        return [s.to_dict() for s in self.service.news_repository.list_sources(self._project_id)]
    @Slot(str)
    def setCurrentProject(self,project_id):
        value=(project_id or '').strip()
        if value==self._project_id:return
        self._project_id=value;self._scene_id='';self.refresh()
    @Slot()
    def refresh(self):
        try:
            if not self._project_id:self._theme={};self._scenes=[];self._visual={};self._readiness={}
            else:
                self._theme=self.service.active_theme(self._project_id).to_dict();items=self.service.scenes.list_scenes(self._project_id);self._scenes=[{**s.to_dict(),'overlayCount':len(self.service.scenes.overlays(self._project_id,s.id))} for s in items]
                if self._scene_id not in {s.id for s in items}:self._scene_id=items[0].id if items else ''
                self._visual=self.service.scene_visuals(self._project_id,self._scene_id) if self._scene_id else {};self._readiness=self.service.readiness(self._project_id)
            self.contextChanged.emit();self.scenesChanged.emit();self.visualChanged.emit()
        except Exception as exc:self._fail(exc)
    @Slot(str)
    def selectScene(self,scene_id):self._scene_id=scene_id;self.refresh()
    @Slot(str,result=bool)
    def applyTheme(self,preset_id):return self._act(lambda:self.service.apply_theme(self._project_id,preset_id),'Theme applied',project_scope=True)
    @Slot(str,str,str,str,result=bool)
    def customizeTheme(self,primary,accent,heading_font,body_font):return self._act(lambda:self.service.customize_theme(self._project_id,{'primaryColor':primary,'accentColor':accent,'fontHeading':heading_font,'fontBody':body_font}),'Theme updated',project_scope=True)
    @Slot(str,str,result=bool)
    def applyLayout(self,preset_id,mode='replace'):return self._act(lambda:self.service.apply_layout(self._project_id,self._scene_id,preset_id,mode=mode),'Layout applied')
    @Slot(result=bool)
    def detachLayout(self):return self._act(lambda:self.service.detach_layout(self._project_id,self._scene_id),'Layout detached')
    @Slot(str,str,str,bool,result=bool)
    def createHeadline(self,headline,kicker='',source_id='',breaking=False):return self._act(lambda:self.service.create_headline(self._project_id,self._scene_id,headline,kicker=kicker,source_id=source_id,breaking=breaking),'Headline graphic added')
    @Slot(str,result=bool)
    def createFact(self,claim_id):return self._act(lambda:self.service.create_fact_from_claim(self._project_id,self._scene_id,claim_id),'Fact graphic added')
    @Slot(str,result=bool)
    def createQuote(self,claim_id):return self._act(lambda:self.service.create_quote_from_claim(self._project_id,self._scene_id,claim_id),'Quote graphic added')
    @Slot(str,str,str,str,str,result=bool)
    def createNumber(self,value,unit,label,claim_id='',source_id=''):return self._act(lambda:self.service.create_number(self._project_id,self._scene_id,value,unit,label,claim_id=claim_id,source_id=source_id),'Number graphic added')
    @Slot(str,result=bool)
    def createSource(self,source_id):return self._act(lambda:self.service.create_source_attribution(self._project_id,self._scene_id,source_id),'Source attribution added')
    @Slot(str,str,str,result=bool)
    def createLowerThird(self,primary,secondary='',source_id=''):return self._act(lambda:self.service.create_lower_third(self._project_id,self._scene_id,primary,secondary,source_id=source_id),'Lower third added')
    @Slot(str,result=bool)
    def createTopic(self,text):return self._act(lambda:self.service.create_topic(self._project_id,self._scene_id,text),'Topic label added')
    @Slot(str,str,result=bool)
    def createIntro(self,title,topic=''):return self._act(lambda:self.service.create_intro(self._project_id,self._scene_id,title,topic),'Intro graphic added')
    @Slot(str,result=bool)
    def createOutro(self,text='Sources listed in video description'):return self._act(lambda:self.service.create_outro(self._project_id,self._scene_id,text),'Outro graphic added')
    @Slot(str,result=bool)
    def updateFromClaim(self,element_id):return self._act(lambda:self.service.update_from_claim(self._project_id,element_id),'Graphic updated from claim')
    @Slot(result=bool)
    def undo(self):
        try:
            if not self.service.undo():return False
            self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def redo(self):
        try:
            if not self.service.redo():return False
            self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str)
    def navigate(self,mode):self.navigationRequested.emit(mode)
    def _act(self,fn,message,project_scope=False):
        try:self.service.execute_undoable(message,self._project_id,self._scene_id,fn,project_scope=project_scope);self.refresh();self.operationSucceeded.emit(message);return True
        except Exception as exc:self._fail(exc);return False
    def _fail(self,exc):self.logger.exception('News visual action failed');self.operationFailed.emit(str(exc) or 'News visual action could not be completed.')

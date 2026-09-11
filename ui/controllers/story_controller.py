from __future__ import annotations
import logging
from PySide6.QtCore import QObject, Property, Signal, Slot
from services.story_service import StoryService
from services.story_outline_service import StoryOutlineService
from services.story_script_service import StoryScriptService
from services.story_apply_service import StoryApplyService
from services.story_validation_service import StoryValidationService
from services.story_errors import StoryError

class StoryController(QObject):
    contextChanged=Signal();outlineChanged=Signal();charactersChanged=Signal();readinessChanged=Signal();operationSucceeded=Signal(str);operationFailed=Signal(str);navigationRequested=Signal(str)
    def __init__(self,service:StoryService,outlines:StoryOutlineService,scripts:StoryScriptService,apply:StoryApplyService,validation:StoryValidationService,logger=None,parent=None):
        super().__init__(parent);self.service=service;self.outlines_service=outlines;self.scripts_service=scripts;self.apply_service=apply;self.validation=validation;self.logger=logger or logging.getLogger('sp_video_studio.story_controller');self._project_id='';self._story={};self._outline={};self._beats=[];self._characters=[];self._readiness={}
    @Property(str,notify=contextChanged)
    def currentProjectId(self):return self._project_id
    @Property('QVariantMap',notify=contextChanged)
    def story(self):return self._story
    @Property('QVariantMap',notify=outlineChanged)
    def outline(self):return self._outline
    @Property('QVariantList',notify=outlineChanged)
    def beats(self):return self._beats
    @Property('QVariantList',notify=charactersChanged)
    def characters(self):return self._characters
    @Property('QVariantMap',notify=readinessChanged)
    def readiness(self):return self._readiness
    @Property('QVariantList',constant=True)
    def storyTypes(self):return [{"id":x,"name":x.replace('_',' ').title()} for x in ['short_story','documentary_story','educational_story','motivational_story','mystery','drama','adventure','biography_style','explainer_story','custom']]
    @Property('QVariantList',constant=True)
    def structureTemplates(self):return [{"id":x,"name":x.replace('_',' ').title()} for x in ['5_beat_story','explainer','documentary','motivational','mystery_short','educational']]
    @Slot(str)
    def setCurrentProject(self,project_id):self._project_id=(project_id or '').strip();self.refresh()
    @Slot()
    def refresh(self):
        if not self._project_id:self._story={};self._outline={};self._beats=[];self._characters=[];self._readiness={};self._emit_all();return
        try:
            meta=self.service.load_or_create(self._project_id);outline,beats=self.outlines_service.latest(self._project_id)
            self._story={**meta.to_dict(),**self.service.overview(self._project_id)};self._outline=outline.to_dict() if outline else {};self._beats=[b.to_dict() for b in beats];self._characters=[c.to_dict() for c in self.service.repository.characters(self._project_id)];self._readiness=self.validation.validate(self._project_id);self._emit_all()
        except Exception as exc:self._fail(exc)
    def _emit_all(self):self.contextChanged.emit();self.outlineChanged.emit();self.charactersChanged.emit();self.readinessChanged.emit()
    @Slot(str,str,str,str,str,int,str,str,result=bool)
    def updateSetup(self,title,idea,story_type,language,tone,duration_ms,audience='general',pace='balanced'):
        try:self.service.update_setup(self._project_id,title=title,idea=idea,story_type=story_type,language=language,tone=tone,target_duration_ms=int(duration_ms),audience=audience,pace=pace);self.refresh();self.operationSucceeded.emit('Story setup saved');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(bool,str,result=bool)
    def createOutline(self,replace=False,template_id=''):
        try:self.outlines_service.create_from_plan(self._project_id,replace=replace,template_id=template_id or None);self.refresh();self.operationSucceeded.emit('Story outline created');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def approveOutline(self):
        try:self.outlines_service.approve(self._project_id,str(self._outline.get('id','')));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,int,result=bool)
    def addBeat(self,title='New Beat',beat_type='custom',duration_ms=5000):
        try:self.outlines_service.add_beat(self._project_id,str(self._outline.get('id','')),title,beat_type,duration_ms);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,str,int,str,str,bool,result=bool)
    def updateBeat(self,beat_id,title,description,duration_ms,beat_type='custom',visual_direction='',locked=False):
        try:self.outlines_service.update_beat(self._project_id,beat_id,title=title,description=description,target_duration_ms=duration_ms,beat_type=beat_type,visual_direction=visual_direction,locked=locked);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,str,int,str,str,str,str,str,bool,result=bool)
    def editBeat(self,beat_id,title,description,duration_ms,beat_type,emotion,visual_direction,character_id,notes,locked):
        try:self.outlines_service.update_beat(self._project_id,beat_id,title=title,description=description,target_duration_ms=duration_ms,beat_type=beat_type,emotion=emotion,visual_direction=visual_direction,character_id=character_id,notes=notes,locked=locked);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,int,result=bool)
    def moveBeat(self,beat_id,delta):
        try:
            beat=self.service.repository.beat(self._project_id,beat_id);self.outlines_service.move_beat(self._project_id,beat_id,(beat.order if beat else 0)+int(delta));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def duplicateBeat(self,beat_id):
        try:self.outlines_service.duplicate_beat(self._project_id,beat_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def deleteBeat(self,beat_id):
        try:self.outlines_service.delete_beat(self._project_id,beat_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def fitDuration(self):
        try:self.outlines_service.fit_to_target(self._project_id,str(self._outline.get('id','')));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def applyTemplate(self,template_id,mode='replace'):
        try:self.outlines_service.apply_template(self._project_id,str(self._outline.get('id','')),template_id,mode);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def refreshStructure(self):
        try:self.outlines_service.refresh_structure(self._project_id,str(self._outline.get('id','')));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(bool,result=bool)
    def createScript(self,replace=False):
        try:self.scripts_service.create_from_outline(self._project_id,str(self._outline.get('id','')),replace=replace);self.refresh();self.navigationRequested.emit('script');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def syncScript(self):
        try:self.scripts_service.sync(self._project_id,str(self._outline.get('id','')));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def createScenes(self):
        try:self.apply_service.create_scenes_from_outline(self._project_id,str(self._outline.get('id','')));self.refresh();self.navigationRequested.emit('scenes');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def setNarratorVoice(self,voice_id):
        try:self.service.set_narrator_voice(self._project_id,voice_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,str,result=bool)
    def addCharacter(self,name,role='other',voice_id=''):
        try:self.service.add_character(self._project_id,name,role,voice_id=voice_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def deleteCharacter(self,character_id):
        try:self.service.delete_character(self._project_id,character_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def createDirectorPlan(self):
        try:self.apply_service.director_plan(self._project_id);self.navigationRequested.emit('director');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def undo(self):
        ok=self.outlines_service.undo();self.refresh();return ok
    @Slot(result=bool)
    def redo(self):
        ok=self.outlines_service.redo();self.refresh();return ok
    @Slot(str)
    def openModule(self,mode):self.navigationRequested.emit(mode)
    def _fail(self,exc):self.logger.exception('Story action failed');self.operationFailed.emit(getattr(exc,'user_message',None) or str(exc) or 'Story action could not be completed.')

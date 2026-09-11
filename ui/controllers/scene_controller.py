from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from services.media_service import MediaService
from services.narration_service import NarrationService
from services.scene_service import SceneService
from services.subtitle_service import SubtitleService
from ui.models.scene_list_model import SceneListModel


def _duration_text(ms: int) -> str:
    total=max(0,int(ms)); seconds=total/1000
    if seconds < 60: return f"{seconds:.1f} sec"
    minutes=int(seconds//60); return f"{minutes}:{int(seconds%60):02d}"


def _file_url(path: str) -> str:
    try: return Path(path).resolve().as_uri() if path else ""
    except Exception: return ""


class SceneController(QObject):
    contextChanged=Signal(); scenesChanged=Signal(); sceneChanged=Signal(); optionsChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str)
    playbackRequested=Signal(str,int,bool); audioPlaybackRequested=Signal(str,str,int)

    def __init__(self, service:SceneService, media_service:MediaService, narration_service:NarrationService, subtitle_service:SubtitleService, logger=None, parent=None):
        super().__init__(parent); self.service=service; self.media_service=media_service; self.narration_service=narration_service; self.subtitle_service=subtitle_service; self.logger=logger or logging.getLogger('sp_video_studio.scene_controller')
        self.sceneModel=SceneListModel(self); self._project_id=""; self._scene_id=""; self._scene:dict[str,object]={}; self._overlays:list[dict[str,object]]=[]; self._issues:list[dict[str,object]]=[]; self._summary={"sceneCount":0,"totalDurationMs":0,"readyCount":0,"warningCount":0,"missingCount":0}

    @Property(QObject,constant=True)
    def scenes(self): return self.sceneModel
    @Property(str,notify=contextChanged)
    def currentProjectId(self): return self._project_id
    @Property('QVariantMap',notify=sceneChanged)
    def scene(self): return self._scene
    @Property('QVariantList',notify=sceneChanged)
    def overlays(self): return self._overlays
    @Property('QVariantList',notify=sceneChanged)
    def issues(self): return self._issues
    @Property('QVariantMap',notify=scenesChanged)
    def summary(self): return self._summary
    @Property('QVariantList',notify=optionsChanged)
    def mediaOptions(self):
        if not self._project_id:return []
        try:
            result=[]
            for item in self.media_service.list_media(self._project_id,sort='name'):
                if item.type not in {'image','video'}: continue
                result.append({"id":item.id,"name":item.name,"type":item.type,"durationMs":int(item.duration_ms or 0),"thumbnailUrl":_file_url(item.thumbnail_path or item.project_path)})
            return result
        except Exception:return []
    @Property('QVariantList',notify=optionsChanged)
    def narrationOptions(self):
        if not self._project_id:return []
        try:return [{"id":x.id,"name":f"{('Section' if x.section_id else 'Full')} narration • {_duration_text(x.duration_ms)}","durationMs":x.duration_ms,"filePath":x.file_path,"sectionId":x.section_id or ""} for x in self.narration_service.list_generated(self._project_id) if str(x.status)=='completed']
        except Exception:return []
    @Property('QVariantList',notify=optionsChanged)
    def subtitleOptions(self):
        if not self._project_id:return []
        try:return [{"id":x.id,"name":x.name,"language":x.language} for x in self.subtitle_service.list_tracks(self._project_id)]
        except Exception:return []
    @Property('QVariantList',notify=optionsChanged)
    def transcriptOptions(self):
        if not self._project_id:return []
        try:
            result=[]
            for item in self.service.transcript_repository.list_for_project(self._project_id):
                media=self.service.media_repository.get_by_id(item.media_id)
                result.append({"id":item.id,"name":(media.name if media else "Transcript"),"language":item.detected_language or item.language_mode or "auto","durationMs":item.duration_ms,"active":item.active})
            return result
        except Exception:return []

    @Slot(str)
    def setCurrentProject(self, project_id:str):
        value=(project_id or '').strip()
        if value==self._project_id:return
        self._project_id=value; self._scene_id=""; self._scene={}; self._overlays=[]; self._issues=[]; self.contextChanged.emit(); self.refresh()

    @Slot()
    def refresh(self):
        if not self._project_id:
            self.sceneModel.replace([]); self._summary={"sceneCount":0,"totalDurationMs":0,"readyCount":0,"warningCount":0,"missingCount":0}; self.scenesChanged.emit(); return
        try:
            scenes=self.service.list_scenes(self._project_id); items=[]
            for scene in scenes:
                media=self.service.media_repository.get_by_id(scene.primary_media_id) if scene.primary_media_id else None
                items.append({"id":scene.id,"number":scene.order+1,"name":scene.name,"durationMs":scene.duration_ms,"durationText":_duration_text(scene.duration_ms),"status":scene.status_code,"statusName":scene.status_code.replace('_',' ').title(),"enabled":scene.enabled,"hasMedia":bool(scene.primary_media_id),"thumbnailUrl":_file_url((media.thumbnail_path or media.project_path) if media else ''),"hasNarration":bool(scene.narration_audio_id),"hasSubtitle":bool(scene.subtitle_track_id),"sourceLabel":str(scene.metadata.get('sourceTitle',''))})
            if self._scene_id and not any(x.id==self._scene_id for x in scenes): self._scene_id=""
            if not self._scene_id and scenes:self._scene_id=scenes[0].id
            self.sceneModel.replace(items,self._scene_id); self._summary=self.service.project_summary(self._project_id); self.scenesChanged.emit(); self.optionsChanged.emit(); self._load_current()
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def selectScene(self,scene_id:str): self._scene_id=scene_id; self.sceneModel.set_selected(scene_id); self._load_current()
    @Slot(result=bool)
    def addScene(self):
        try: scene=self.service.add_scene(self._project_id); self._scene_id=scene.id; self.refresh(); self.operationSucceeded.emit('Scene added'); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def createFromScript(self):
        try: created=self.service.create_from_script(self._project_id); self._scene_id=created[0].id if created else self._scene_id; self.refresh(); self.operationSucceeded.emit(f'{len(created)} scenes created from script'); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,int,result=bool)
    def createFromTranscript(self,transcript_id:str,group_seconds:int=15):
        try:
            created=self.service.create_from_transcript(self._project_id,transcript_id,group_ms=max(1,int(group_seconds))*1000,append=True)
            self._scene_id=created[0].id if created else self._scene_id; self.refresh(); self.operationSucceeded.emit(f'{len(created)} scenes created from transcript'); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def syncScript(self):
        try:r=self.service.sync_with_script(self._project_id); self.refresh(); self.operationSucceeded.emit(f"Scene sync: {r['added']} added, {r['changed']} changed"); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def duplicateScene(self):
        try: item=self.service.duplicate_scene(self._project_id,self._scene_id); self._scene_id=item.id; self.refresh(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def deleteScene(self):
        try:self.service.delete_scene(self._project_id,self._scene_id); self._scene_id=""; self.refresh(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(int,result=bool)
    def moveScene(self,delta:int):
        try:
            current=self.service.repository.get(self._scene_id)
            if current is None:return False
            self.service.move_scene(self._project_id,self._scene_id,current.order+int(delta)); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(bool,result=bool)
    def setEnabled(self,value:bool): return self._act(lambda:self.service.set_enabled(self._project_id,self._scene_id,value))
    @Slot(str,int,result=bool)
    def updateGeneral(self,name:str,duration_ms:int): return self._act(lambda:self.service.update_general(self._project_id,self._scene_id,name=name,duration_ms=duration_ms))
    @Slot(str,result=bool)
    def setBackground(self,color:str): return self._act(lambda:self.service.update_general(self._project_id,self._scene_id,background_color=color))
    @Slot(bool,result=bool)
    def setBackgroundEnabled(self,value:bool): return self._act(lambda:self.service.set_background_enabled(self._project_id,self._scene_id,value))
    @Slot(str,result=bool)
    def assignMedia(self,media_id:str): return self._act(lambda:self.service.assign_media(self._project_id,self._scene_id,media_id))
    @Slot(result=bool)
    def clearMedia(self): return self._act(lambda:self.service.clear_media(self._project_id,self._scene_id))
    @Slot(str,result=bool)
    def setFitMode(self,value:str): return self._act(lambda:self.service.set_fit_mode(self._project_id,self._scene_id,value))
    @Slot(int,int,result=bool)
    def setVideoRange(self,start_ms:int,end_ms:int): return self._act(lambda:self.service.set_video_range(self._project_id,self._scene_id,start_ms,end_ms))
    @Slot(str,result=bool)
    def assignNarration(self,audio_id:str): return self._act(lambda:self.service.assign_narration(self._project_id,self._scene_id,audio_id))
    @Slot(result=bool)
    def matchNarrationDuration(self): return self._act(lambda:self.service.match_duration_to_narration(self._project_id,self._scene_id))
    @Slot(str,result=bool)
    def assignSubtitle(self,track_id:str): return self._act(lambda:self.service.assign_subtitle(self._project_id,self._scene_id,track_id))
    @Slot(bool,int,bool,int,result=bool)
    def setAudio(self,source_enabled:bool,source_volume:int,narration_enabled:bool,narration_volume:int): return self._act(lambda:self.service.set_audio(self._project_id,self._scene_id,source_enabled=source_enabled,source_volume=source_volume/100,narration_enabled=narration_enabled,narration_volume=narration_volume/100))
    @Slot(str,int,result=bool)
    def setTransition(self,kind:str,duration_ms:int): return self._act(lambda:self.service.set_transition(self._project_id,self._scene_id,kind,duration_ms))
    @Slot(str,result=bool)
    def addHeadline(self,text:str): return self._overlay_act(lambda:self.service.add_text_overlay(self._project_id,self._scene_id,text or 'Headline','headline'))
    @Slot(str,str,result=bool)
    def addLowerThird(self,primary:str,secondary:str): return self._overlay_act(lambda:self.service.add_lower_third(self._project_id,self._scene_id,primary or 'Name',secondary or 'Role'))
    @Slot(str,result=bool)
    def addLogo(self,media_id:str): return self._overlay_act(lambda:self.service.add_logo(self._project_id,self._scene_id,media_id))
    @Slot(str,str,str,result=bool)
    def updateOverlayText(self,overlay_id:str,text:str,secondary:str): return self._overlay_act(lambda:self.service.update_overlay(self._project_id,self._scene_id,overlay_id,{"text":text,"secondaryText":secondary}))
    @Slot(str,float,float,float,float,float,result=bool)
    def updateOverlayLayout(self,overlay_id:str,x:float,y:float,width:float,height:float,opacity:float): return self._overlay_act(lambda:self.service.update_overlay(self._project_id,self._scene_id,overlay_id,{"x":x,"y":y,"width":width,"height":height,"opacity":opacity}))
    @Slot(str,result=bool)
    def deleteOverlay(self,overlay_id:str):
        try:self.service.delete_overlay(self._project_id,self._scene_id,overlay_id); self._load_current(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,int,result=bool)
    def moveOverlay(self,overlay_id:str,delta:int):
        try:self.service.move_overlay(self._project_id,self._scene_id,overlay_id,delta); self._load_current(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def syncCurrentFromScript(self): return self._act(lambda:self.service.sync_scene_from_script(self._project_id,self._scene_id))
    @Slot(result='QVariantMap')
    def renderSpec(self):
        try:return self.service.build_scene_render_spec(self._project_id,self._scene_id) if self._scene_id else {}
        except Exception as exc:self._fail(exc); return {}
    @Slot(result='QVariantMap')
    def sequenceSpec(self):
        try:return self.service.build_project_scene_sequence(self._project_id)
        except Exception as exc:self._fail(exc); return {}
    @Slot(bool)
    def playScene(self,autoplay:bool=True):
        if not self._scene:return
        media_id=str(self._scene.get('primaryMediaId',''))
        if media_id:self.playbackRequested.emit(media_id,int(self._scene.get('sourceStartMs',0) or 0),bool(autoplay))
    @Slot()
    def playNarration(self):
        if not self._scene:return
        audio_id=str(self._scene.get('narrationAudioId',''))
        if not audio_id:return
        try:
            item=self.narration_service.get_generated(self._project_id,audio_id); self.audioPlaybackRequested.emit(item.file_path,'Scene narration',item.duration_ms)
        except Exception as exc:self._fail(exc)

    def _act(self,fn):
        try:fn(); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False
    def _overlay_act(self,fn):
        try:fn(); self._load_current(); self.scenesChanged.emit(); return True
        except Exception as exc:self._fail(exc); return False
    def _load_current(self):
        if not self._project_id or not self._scene_id:
            self._scene={}; self._overlays=[]; self._issues=[]; self.sceneChanged.emit(); return
        try:
            scene,layers,overlays=self.service.get(self._project_id,self._scene_id); data=scene.to_dict(); media=self.service.media_repository.get_by_id(scene.primary_media_id) if scene.primary_media_id else None; audio=self.service.audio_repository.get(scene.narration_audio_id) if scene.narration_audio_id else None; track=self.service.subtitle_repository.get_track(scene.subtitle_track_id) if scene.subtitle_track_id else None
            data.update({"mediaName":media.name if media else "","mediaType":media.type if media else "","mediaUrl":_file_url(media.project_path if media else ''),"thumbnailUrl":_file_url((media.thumbnail_path or media.project_path) if media else ''),"mediaDurationMs":int(media.duration_ms or 0) if media else 0,"narrationName":f"Narration • {_duration_text(audio.duration_ms)}" if audio else "","narrationDurationMs":int(audio.duration_ms or 0) if audio else 0,"subtitleName":track.name if track else "","durationText":_duration_text(scene.duration_ms),"backgroundEnabled":bool(scene.metadata.get("backgroundEnabled",False))})
            overlay_items=[]
            for item in overlays:
                value=item.to_dict()
                if item.asset_id:
                    asset=self.service.media_repository.get_by_id(item.asset_id)
                    value["assetUrl"]=_file_url(asset.project_path if asset else "")
                    value["assetName"]=asset.name if asset else ""
                else:
                    value["assetUrl"]=""; value["assetName"]=""
                overlay_items.append(value)
            self._scene=data; self._overlays=overlay_items; self._issues=[x.to_dict() for x in self.service.validate_scene(self._project_id,self._scene_id)]; self.sceneChanged.emit()
        except Exception as exc:self._fail(exc)
    def _fail(self,exc): self.logger.exception('Scene action failed'); self.operationFailed.emit(str(exc) or 'Scene action could not be completed.')

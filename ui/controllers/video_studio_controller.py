from __future__ import annotations
import logging
from PySide6.QtCore import QObject, Property, Signal, Slot
from domain.chroma_key import ChromaKeySettings


class VideoStudioController(QObject):
    changed=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str)
    def __init__(self, universal, layers, speakers, blocks, repository, media_repository, scene_service, language_service, parent=None, logger=None):
        super().__init__(parent); self.universal=universal; self.layers_service=layers; self.speakers_service=speakers; self.blocks_service=blocks; self.repository=repository; self.media=media_repository; self.scenes_service=scene_service; self.languages=language_service; self.logger=logger or logging.getLogger("sp_video_studio.phase22")
        self._project_id=""; self._scene_id=""; self._layer_id=""
    @Property(str,notify=changed)
    def currentProjectId(self): return self._project_id
    @Property(str,notify=changed)
    def selectedSceneId(self): return self._scene_id
    @Property(str,notify=changed)
    def selectedLayerId(self): return self._layer_id
    @Property('QVariantList',notify=changed)
    def mediaItems(self):
        if not self._project_id:return []
        try:return [{"id":x.id,"name":x.name,"type":x.type,"durationMs":int(x.duration_ms or 0),"thumbnail":x.thumbnail_path or ""} for x in self.media.list_by_project(self._project_id)]
        except Exception:return []
    @Property('QVariantList',notify=changed)
    def scenes(self):
        if not self._project_id:return []
        try:return [x.to_dict() for x in self.scenes_service.list_scenes(self._project_id)]
        except Exception:return []
    @Property('QVariantList',notify=changed)
    def layers(self):
        if not self._project_id or not self._scene_id:return []
        try:return [x.to_dict() for x in self.layers_service.list_layers(self._project_id,self._scene_id)]
        except Exception:return []
    @Property('QVariantMap',notify=changed)
    def selectedLayer(self):
        return next((x for x in self.layers if x.get("id")==self._layer_id),{})
    @Property('QVariantList',notify=changed)
    def voices(self):
        try:return [{"id":v.voice_id,"name":v.name,"language":v.language,"engineId":v.engine_id} for v in self.speakers_service.voices.list_all()]
        except Exception:return []
    @Property('QVariantList',notify=changed)
    def scriptSections(self):
        if not self._project_id:return []
        try:
            with self.repository.database.connect() as c:
                rows=c.execute("""SELECT s.id,s.title,s.content,sc.language FROM script_sections s JOIN scripts sc ON sc.id=s.script_id WHERE sc.project_id=? ORDER BY s.section_order""",(self._project_id,)).fetchall()
            return [{"id":str(r["id"]),"title":str(r["title"]),"content":str(r["content"] or ""),"language":str(r["language"] or "en")} for r in rows]
        except Exception:return []
    @Property('QVariantList',notify=changed)
    def speakers(self):
        if not self._project_id:return []
        try:return [x.to_dict() for x in self.speakers_service.list(self._project_id)]
        except Exception:return []
    @Property('QVariantList',notify=changed)
    def speechBlocks(self):
        if not self._project_id:return []
        try:return [x.to_dict() for x in self.blocks_service.for_project(self._project_id)]
        except Exception:return []
    @Property('QVariantList',constant=True)
    def visualRoles(self): return [{"id":x,"name":x.replace("_"," ").title()} for x in ["broll","overlay_video","presenter","reporter","interview_guest","host","character","image_overlay","custom"]]
    @Property('QVariantList',constant=True)
    def speakerRoles(self): return [{"id":x,"name":x.replace("_"," ").title()} for x in ["narrator","reporter","host","interviewer","interview_guest","character","expert","speaker","custom"]]
    @Slot()
    def refresh(self): self.changed.emit()
    @Slot(str)
    def setCurrentProject(self,project_id):
        self._project_id=(project_id or "").strip(); state=self.repository.state(self._project_id) if self._project_id else {}; self._scene_id=str(state.get("activeSceneId","") or ""); self._layer_id=str(state.get("activeLayerId","") or "")
        if self._project_id and not self._scene_id:
            items=self.scenes_service.list_scenes(self._project_id); self._scene_id=items[0].id if items else ""
        self.changed.emit()
    @Slot(str)
    def selectScene(self,scene_id): self._scene_id=scene_id; self._layer_id=""; self._save_state(); self.changed.emit()
    @Slot(str)
    def selectLayer(self,layer_id): self._layer_id=layer_id; self._save_state(); self.changed.emit()
    @Slot(str,str,int,result=bool)
    def addMediaAtPlayhead(self,media_id,track,playhead_ms): return self._act(lambda:self.universal.add_media_at_playhead(self._project_id,media_id,playhead_ms,track),"Media added")
    @Slot(str,str,str,result=bool)
    def addLayer(self,media_id,role,pip_preset=""):
        if not self._scene_id:return self._fail("Select a scene first.")
        def action():
            item=self.layers_service.add_media_layer(self._project_id,self._scene_id,media_id,role=role,pip_preset=(pip_preset or None)); self._layer_id=item.id; self._save_state(); return item
        return self._act(action,"Visual layer added")
    @Slot(str,float,float,float,float,float,float,result=bool)
    def setLayerTransform(self,layer_id,x,y,w,h,opacity,rotation): return self._act(lambda:self.layers_service.update_layer(self._project_id,self._scene_id,layer_id,{"x":x,"y":y,"width":w,"height":h,"opacity":opacity,"rotation":rotation}),"Layer transform updated")
    @Slot(str,float,float,float,float,result=bool)
    def setLayerCrop(self,layer_id,left,top,right,bottom): return self._act(lambda:self.layers_service.update_layer(self._project_id,self._scene_id,layer_id,{"cropLeft":left,"cropTop":top,"cropRight":right,"cropBottom":bottom}),"Crop updated")
    @Slot(str,str,result=bool)
    def applyPip(self,layer_id,preset): return self._act(lambda:self.layers_service.apply_pip(self._project_id,self._scene_id,layer_id,preset),"Picture-in-picture applied")
    @Slot(str,str,result=bool)
    def applyChromaPreset(self,layer_id,preset): return self._act(lambda:self.layers_service.apply_chroma_preset(self._project_id,self._scene_id,layer_id,preset),"Chroma key updated")
    @Slot(str,bool,str,float,float,result=bool)
    def setChroma(self,layer_id,enabled,color,similarity,softness): return self._act(lambda:self.layers_service.set_chroma_key(self._project_id,self._scene_id,layer_id,ChromaKeySettings(enabled=enabled,key_color=color,similarity=similarity,blend=softness,edge_softness=softness)),"Chroma key updated")
    @Slot(str,int,result=bool)
    def moveLayerZ(self,layer_id,delta): return self._act(lambda:self.layers_service.move_z(self._project_id,self._scene_id,layer_id,delta),"Layer order updated")
    @Slot(str,result=bool)
    def duplicateLayer(self,layer_id): return self._act(lambda:self.layers_service.duplicate_layer(self._project_id,self._scene_id,layer_id),"Layer duplicated")
    @Slot(str,result=bool)
    def deleteLayer(self,layer_id):
        ok=self._act(lambda:self.layers_service.delete_layer(self._project_id,self._scene_id,layer_id),"Layer removed")
        if ok:self._layer_id="";self._save_state();self.changed.emit()
        return ok
    @Slot(str,str,str,str,result=bool)
    def addSpeaker(self,name,role,language,voice_id=""): return self._act(lambda:self.speakers_service.create(self._project_id,name,role,language=language,voice_id=voice_id),"Speaker added")
    @Slot(str,str,result=bool)
    def assignSpeakerVoice(self,speaker_id,voice_id): return self._act(lambda:self.speakers_service.update(self._project_id,speaker_id,voice_id=voice_id),"Speaker voice updated")
    @Slot(str,str,result=bool)
    def deleteSpeaker(self,speaker_id,replacement_id=""): return self._act(lambda:self.speakers_service.delete(self._project_id,speaker_id,replacement_speaker_id=replacement_id),"Speaker removed")
    @Slot(str,str,str,str,result=bool)
    def addDialogue(self,section_id,text,speaker_id,language): return self._act(lambda:self.blocks_service.add(self._project_id,section_id,text,speaker_id=speaker_id,language=language),"Dialogue added")
    def _save_state(self):
        if self._project_id:self.repository.save_state(self._project_id,activeSceneId=self._scene_id,activeLayerId=self._layer_id)
    def _act(self,fn,message):
        try:fn();self.changed.emit();self.operationSucceeded.emit(message);return True
        except Exception as exc:self.logger.exception("Phase22 action failed");return self._fail(getattr(exc,"user_message",None) or str(exc))
    def _fail(self,message):self.operationFailed.emit(message or "Video Studio action could not be completed.");return False

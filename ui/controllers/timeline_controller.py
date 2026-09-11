from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from services.timeline_edit_service import TimelineInvalidOperation
from services.timeline_service import TimelineService


def _time_text(ms:int)->str:
    value=max(0,int(ms)); h=value//3600000; m=(value//60000)%60; s=(value//1000)%60; milli=value%1000
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}" if h else f"{m:02d}:{s:02d}.{milli:03d}"


class TimelineController(QObject):
    timelineChanged=Signal(); selectionChanged=Signal(); playheadChanged=Signal(); historyChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str)
    playbackRequested=Signal(str,int,bool); togglePlaybackRequested=Signal()

    def __init__(self,service:TimelineService,logger=None,parent=None):
        super().__init__(parent); self.service=service; self.logger=logger or logging.getLogger("sp_video_studio.timeline_controller")
        self._project_id=""; self._state={}; self._tracks=[]; self._markers=[]; self._issues=[]; self._selected={}; self._preview_scene_id=""; self._flat={}

    @Property(str,notify=timelineChanged)
    def currentProjectId(self): return self._project_id
    @Property('QVariantList',notify=timelineChanged)
    def tracks(self): return self._tracks
    @Property('QVariantList',notify=timelineChanged)
    def markers(self): return self._markers
    @Property('QVariantList',notify=timelineChanged)
    def issues(self): return self._issues
    @Property('QVariantMap',notify=selectionChanged)
    def selectedClip(self): return dict(self._selected)
    @Property(int,notify=timelineChanged)
    def durationMs(self): return int(self._state.get("durationMs",0) or 0)
    @Property(str,notify=timelineChanged)
    def durationText(self): return _time_text(self.durationMs)
    @Property(int,notify=playheadChanged)
    def playheadMs(self): return int(self._state.get("playheadMs",0) or 0)
    @Property(str,notify=playheadChanged)
    def playheadText(self): return _time_text(self.playheadMs)
    @Property(float,notify=timelineChanged)
    def pixelsPerSecond(self): return float(self._state.get("pixelsPerSecond",80.0) or 80.0)
    @Property(bool,notify=timelineChanged)
    def snapEnabled(self): return bool(self._state.get("snapEnabled",True))
    @Property(bool,notify=historyChanged)
    def canUndo(self): return self.service.edits.stack.can_undo
    @Property(bool,notify=historyChanged)
    def canRedo(self): return self.service.edits.stack.can_redo
    @Property(str,notify=historyChanged)
    def undoLabel(self): return self.service.edits.stack.undo_label
    @Property(str,notify=historyChanged)
    def redoLabel(self): return self.service.edits.stack.redo_label

    @Slot(str)
    def setCurrentProject(self,project_id:str):
        value=(project_id or "").strip()
        if value==self._project_id:return
        self._project_id=value; self._preview_scene_id=""; self._selected={}; self.service.edits.clear_history(); self.refresh(); self.historyChanged.emit()

    @Slot()
    def refresh(self):
        if not self._project_id:
            self._state={}; self._tracks=[]; self._markers=[]; self._issues=[]; self._flat={}; self.timelineChanged.emit(); return
        try:
            data=self.service.load(self._project_id); state=data["state"]
            clips_by=data["clips"]; self._flat={}
            rows=[]
            for track in data["tracks"]:
                clips=[]
                for clip in clips_by.get(track.type_code,[]):
                    item=clip.to_dict(); clips.append(item); self._flat[clip.id]=item
                row=track.to_dict(); row["clips"]=clips; row["clipCount"]=len(clips); rows.append(row)
            self._tracks=rows; self._markers=[m.to_dict() for m in data["markers"]]; self._issues=[{"severity":x.severity,"code":x.code,"message":x.message,"clipId":x.clip_id} for x in data["issues"]]; self._state=state.to_dict()
            sid=str(self._state.get("selectedClipId","") or ""); self._selected=dict(self._flat.get(sid,{})); self.timelineChanged.emit(); self.selectionChanged.emit(); self.playheadChanged.emit()
        except Exception as exc: self._fail(exc)

    @Slot(str)
    def selectClip(self,clip_id:str):
        self._selected=dict(self._flat.get(clip_id,{})); self.service.save_editor_state(self._project_id,selected_clip_id=clip_id if self._selected else ""); self.selectionChanged.emit()

    @Slot(int,bool)
    def seekProject(self,position_ms:int,autoplay:bool=False):
        if not self._project_id:return
        pos=max(0,min(int(position_ms),self.durationMs)); self._state["playheadMs"]=pos; self.service.save_editor_state(self._project_id,playhead_ms=pos); self.playheadChanged.emit()
        mapped=self.service.project_to_scene_time(self._project_id,pos)
        if not mapped:return
        scene_id,local=mapped; scene=self.service.edits.scenes.get(self._project_id,scene_id)[0]; self._preview_scene_id=scene_id
        if scene.primary_media_id: self.playbackRequested.emit(scene.primary_media_id,scene.source_start_ms+local,autoplay)

    @Slot(int)
    def setPreviewLocalPosition(self,source_position_ms:int):
        if not self._preview_scene_id or not self._project_id:return
        try:
            scene=self.service.edits.scenes.get(self._project_id,self._preview_scene_id)[0]
            local=max(0,int(source_position_ms)-int(scene.source_start_ms or 0))
            value=self.service.scene_to_project_time(self._project_id,self._preview_scene_id,local); self._state["playheadMs"]=value; self.playheadChanged.emit()
        except Exception: return

    @Slot()
    def togglePlayback(self): self.togglePlaybackRequested.emit()
    @Slot(int)
    def seekRelative(self,delta_ms:int): self.seekProject(self.playheadMs+int(delta_ms),False)
    @Slot(int)
    def stepFrame(self,direction:int):
        if not self._project_id:return
        step=self.service.frame_step_ms(self._project_id); target=self.playheadMs+(step if int(direction)>=0 else -step); self.seekProject(self.service.quantize_to_frame(self._project_id,target),False)
    @Slot()
    def previousScene(self):
        ranges=self.service.mapping.scene_ranges(self._project_id); starts=[int(x["startMs"]) for x in ranges if int(x["startMs"])<self.playheadMs-1]; self.seekProject(starts[-1] if starts else 0,False)
    @Slot()
    def nextScene(self):
        ranges=self.service.mapping.scene_ranges(self._project_id); nxt=next((int(x["startMs"]) for x in ranges if int(x["startMs"])>self.playheadMs+1),self.durationMs); self.seekProject(nxt,False)

    @Slot(float)
    def setZoom(self,value:float): self._set_zoom(value)
    @Slot()
    def zoomIn(self): self._set_zoom(self.pixelsPerSecond*1.25)
    @Slot()
    def zoomOut(self): self._set_zoom(self.pixelsPerSecond/1.25)
    @Slot(float)
    def fitTimeline(self,viewport_width:float):
        seconds=max(.1,self.durationMs/1000); self._set_zoom(max(10,min(800,(max(200,float(viewport_width))-40)/seconds)))
    def _set_zoom(self,value:float):
        if not self._project_id:return
        state=self.service.save_editor_state(self._project_id,zoom_level=max(10,min(800,float(value)))); self._state.update(state.to_dict()); self.timelineChanged.emit()
    @Slot(bool)
    def setSnapEnabled(self,value:bool):
        state=self.service.save_editor_state(self._project_id,snap_enabled=value); self._state.update(state.to_dict()); self.timelineChanged.emit()
    @Slot(int,result=int)
    def snapTime(self,value_ms:int): return self.service.snap_time(self._project_id,value_ms,self.pixelsPerSecond,include_playhead=self.playheadMs) if self.snapEnabled else max(0,int(value_ms))

    @Slot(str,int,result=bool)
    def reorderScene(self,scene_id:str,new_index:int): return self._edit(lambda:self.service.edits.reorder_scene(self._project_id,scene_id,new_index),"Scene reordered")
    @Slot(str,int,result=bool)
    def trimSceneRight(self,scene_id:str,duration_ms:int): return self._edit(lambda:self.service.edits.trim_scene_right(self._project_id,scene_id,duration_ms),"Scene trimmed")
    @Slot(str,int,result=bool)
    def trimSceneLeft(self,scene_id:str,trim_ms:int): return self._edit(lambda:self.service.edits.trim_scene_left(self._project_id,scene_id,trim_ms),"Scene trimmed")
    @Slot(result=bool)
    def splitSelected(self):
        if self._selected.get("sourceType") not in {"scene_video","scene_image"}: return self._reject("Select a video or image scene to split.")
        scene_id=str(self._selected.get("sourceId","")); mapped=self.service.project_to_scene_time(self._project_id,self.playheadMs)
        if not mapped or mapped[0]!=scene_id:return self._reject("The playhead must be inside the selected clip.")
        return self._edit(lambda:self.service.edits.split_scene(self._project_id,scene_id,mapped[1]),"Scene split")
    @Slot(result=bool)
    def duplicateSelected(self):
        if self._selected.get("sourceType") not in {"scene_video","scene_image"}: return self._reject("This clip cannot be duplicated here.")
        return self._edit(lambda:self.service.edits.duplicate_scene(self._project_id,str(self._selected.get("sourceId",""))),"Scene duplicated")
    @Slot(result=bool)
    def deleteSelected(self):
        kind=str(self._selected.get("sourceType","")); source=str(self._selected.get("sourceId",""))
        if kind in {"scene_video","scene_image"}: return self._edit(lambda:self.service.edits.delete_scene(self._project_id,source),"Scene deleted")
        if kind=="scene_overlay":
            scene_id=str(self._selected.get("metadata",{}).get("sceneId","")); return self._edit(lambda:self.service.edits.delete_overlay(self._project_id,scene_id,source),"Overlay deleted")
        return self._reject("Use its source editor to remove this clip safely.")

    @Slot(str,int,int,result=bool)
    def setOverlayTiming(self,overlay_id:str,start_ms:int,end_ms:int):
        clip=self._flat.get(f"overlay:{overlay_id}",{}); scene_id=str(clip.get("metadata",{}).get("sceneId","")); scene_start=next((int(x["startMs"]) for x in self.service.mapping.scene_ranges(self._project_id) if str(x["sceneId"])==scene_id),0)
        return self._edit(lambda:self.service.edits.set_overlay_timing(self._project_id,scene_id,overlay_id,start_ms-scene_start,end_ms-scene_start),"Overlay timing updated")
    @Slot(str,int,int,result=bool)
    def setSubtitleTiming(self,cue_id:str,start_ms:int,end_ms:int): return self._edit(lambda:self.service.edits.set_subtitle_timing(self._project_id,cue_id,start_ms,end_ms),"Subtitle timing updated")
    @Slot(str,int,result=bool)
    def setNarrationVolume(self,scene_id:str,volume:int): return self._edit(lambda:self.service.edits.set_scene_audio(self._project_id,scene_id,narration_volume=max(0,min(100,volume))/100),"Narration volume updated")
    @Slot(str,int,result=bool)
    def setSourceAudioVolume(self,scene_id:str,volume:int): return self._edit(lambda:self.service.edits.set_scene_audio(self._project_id,scene_id,source_volume=max(0,min(100,volume))/100),"Source audio volume updated")
    @Slot(str,bool,result=bool)
    def setNarrationMuted(self,scene_id:str,muted:bool): return self._edit(lambda:self.service.edits.set_scene_audio(self._project_id,scene_id,narration_enabled=not muted),"Narration mute updated")
    @Slot(str,bool,result=bool)
    def setSourceAudioMuted(self,scene_id:str,muted:bool): return self._edit(lambda:self.service.edits.set_scene_audio(self._project_id,scene_id,source_enabled=not muted),"Source audio mute updated")
    @Slot(str,str,int,result=bool)
    def setTransition(self,scene_id:str,kind:str,duration_ms:int): return self._edit(lambda:self.service.edits.set_transition(self._project_id,scene_id,kind,duration_ms),"Transition updated")
    @Slot(str,bool,result=bool)
    def setTrackLocked(self,track_type:str,value:bool): return self._edit(lambda:self.service.edits.set_track_state(self._project_id,track_type,locked=value),"Track lock updated")
    @Slot(str,bool,result=bool)
    def setTrackMuted(self,track_type:str,value:bool): return self._edit(lambda:self.service.edits.set_track_state(self._project_id,track_type,muted=value),"Track mute updated")
    @Slot(str,bool,result=bool)
    def setTrackVisible(self,track_type:str,value:bool): return self._edit(lambda:self.service.edits.set_track_state(self._project_id,track_type,visible=value),"Track visibility updated")

    @Slot(str,result=bool)
    def addMarker(self,label:str="Marker"):
        try:self.service.add_marker(self._project_id,self.playheadMs,label); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,int,str,result=bool)
    def updateMarker(self,marker_id:str,time_ms:int,label:str):
        try:self.service.update_marker(self._project_id,marker_id,time_ms,label); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,result=bool)
    def deleteMarker(self,marker_id:str):
        try:self.service.delete_marker(self._project_id,marker_id); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(result=bool)
    def undo(self):
        try:
            if not self.service.edits.undo():return False
            self.refresh(); self.historyChanged.emit(); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(result=bool)
    def redo(self):
        try:
            if not self.service.edits.redo():return False
            self.refresh(); self.historyChanged.emit(); return True
        except Exception as exc:self._fail(exc); return False

    def _edit(self,fn,message:str)->bool:
        try: fn(); self.refresh(); self.historyChanged.emit(); self.operationSucceeded.emit(message); return True
        except Exception as exc:self._fail(exc); return False
    def _reject(self,message:str)->bool:self.operationFailed.emit(message); return False
    def _fail(self,exc): self.logger.exception("Timeline action failed"); self.operationFailed.emit(str(exc) or "Timeline action could not be completed.")

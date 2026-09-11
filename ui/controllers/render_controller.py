from __future__ import annotations

import logging
from concurrent.futures import Future
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from domain.render_settings import RenderSettings
from rendering.errors import RenderCancelled
from services.platform_service import reveal_in_folder
from services.render_service import RenderService
from ui.models.media_format import format_duration, format_file_size
from workers.cancellation import CancellationToken
from workers.worker_pool import WorkerPool


class RenderController(QObject):
    contextChanged=Signal(); stateChanged=Signal(); historyChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str); playRequested=Signal(str,str,int)
    _progressReady=Signal(object); _jobReady=Signal(object); _jobFailed=Signal(object)

    def __init__(self,service:RenderService,worker_pool:WorkerPool,logger=None,parent=None)->None:
        super().__init__(parent); self.service=service; self.worker_pool=worker_pool; self.logger=logger or logging.getLogger("sp_video_studio.render_controller")
        self._project_id=""; self._busy=False; self._progress=0.0; self._stage="idle"; self._status="Ready to render"; self._speed=0.0; self._token:CancellationToken|None=None; self._future:Future|None=None; self._last_output={}; self._history=[]; self._last_settings=None
        self._progressReady.connect(self._apply_progress); self._jobReady.connect(self._apply_result); self._jobFailed.connect(self._apply_failure)

    @Property(str,notify=contextChanged)
    def currentProjectId(self)->str:return self._project_id
    @Property(bool,notify=stateChanged)
    def busy(self)->bool:return self._busy
    @Property(float,notify=stateChanged)
    def progress(self)->float:return self._progress
    @Property(str,notify=stateChanged)
    def stage(self)->str:return self._stage
    @Property(str,notify=stateChanged)
    def statusMessage(self)->str:return self._status
    @Property(float,notify=stateChanged)
    def speed(self)->float:return self._speed
    @Property("QVariantMap",notify=stateChanged)
    def lastOutput(self):return dict(self._last_output)
    @Property("QVariantList",notify=historyChanged)
    def history(self):return list(self._history)
    @Property("QVariantList",notify=contextChanged)
    def presets(self):return [x.to_dict() for x in self.service.presets()]
    @Property("QVariantList",notify=contextChanged)
    def encoderOptions(self):
        try:return self.service.encoder_options()
        except Exception:return []
    @Property("QVariantList",notify=contextChanged)
    def subtitleTracks(self):
        if not self._project_id:return []
        try:return [{"id":x.id,"name":x.name,"language":x.language,"bilingual":x.is_bilingual} for x in self.service.subtitles.list_tracks(self._project_id)]
        except Exception:return []

    @Slot(str)
    def setCurrentProject(self,project_id:str)->None:
        project_id=(project_id or "").strip()
        if project_id==self._project_id:return
        if self._busy:self.cancel()
        self._project_id=project_id; self._last_output={}; self._progress=0; self._stage="idle"; self._status="Ready to render"; self.refresh(); self.contextChanged.emit(); self.stateChanged.emit()

    @Slot()
    def refresh(self)->None:
        if not self._project_id:self._history=[]
        else:
            try:self._history=[self._output_map(x) for x in self.service.history(self._project_id,12)]
            except Exception:self._history=[]
        self.historyChanged.emit(); self.contextChanged.emit()

    @Slot(str,int,int,int,str,str,str,bool,result="QVariantList")
    def validate(self,preset_id:str,width:int,height:int,fps:int,encoder:str,quality:str,subtitle_track_id:str,keep_temp:bool):
        if not self._project_id:return [{"severity":"error","message":"Open a project first."}]
        try:
            settings=RenderSettings(width,height,fps,encoder or "auto",quality or "balanced",subtitle_track_id or "",keep_temp=keep_temp)
            plan=self.service.build_plan(self._project_id,settings,preset_id=preset_id or "custom")
            return [{"severity":i.severity,"code":i.code,"message":i.message,"sceneId":i.scene_id} for i in self.service.validate_plan(plan)]
        except Exception as exc:return [{"severity":"error","message":self._friendly(exc)}]

    @Slot(str,int,int,int,str,str,str,bool,result=bool)
    def start(self,preset_id:str,width:int,height:int,fps:int,encoder:str,quality:str,subtitle_track_id:str,keep_temp:bool)->bool:
        if self._busy or not self._project_id:return False
        settings=RenderSettings(width,height,fps,encoder or "auto",quality or "balanced",subtitle_track_id or "",keep_temp=keep_temp); self._last_settings=(preset_id,settings)
        try:
            plan=self.service.build_plan(self._project_id,settings,preset_id=preset_id or "custom"); issues=self.service.validate_plan(plan); errors=[i for i in issues if i.severity=="error"]
            if errors:self.operationFailed.emit(errors[0].message);return False
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False
        self._token=CancellationToken(); self._busy=True; self._progress=0; self._stage="preparing"; self._status="Preparing render…"; self.stateChanged.emit()
        def report(state):self._progressReady.emit(state)
        self._future=self.worker_pool.submit(self.service.render,self._project_id,settings,preset_id=preset_id or "custom",cancellation=self._token,progress_callback=report); self._future.add_done_callback(self._done); return True

    @Slot()
    def cancel(self)->None:
        if self._busy and self._token:self._token.cancel();self._stage="cancelling";self._status="Stopping render…";self.stateChanged.emit()

    @Slot(result=bool)
    def retryLast(self)->bool:
        if not self._last_settings:return False
        preset,settings=self._last_settings
        return self.start(preset,settings.width,settings.height,settings.fps,settings.encoder,settings.quality_code,settings.subtitle_track_id,settings.keep_temp)

    @Slot(str)
    def playOutput(self,output_id:str)->None:
        item=next((x for x in self._history if x.get("id")==output_id),None) or (self._last_output if self._last_output.get("id")==output_id else None)
        if item and Path(str(item.get("filePath",""))).is_file():self.playRequested.emit(str(item["filePath"]),str(item.get("name","Rendered video")),int(item.get("durationMs",0) or 0))

    @Slot(str)
    def openFolder(self,output_id:str)->None:
        item=next((x for x in self._history if x.get("id")==output_id),None) or (self._last_output if self._last_output.get("id")==output_id else None)
        if item:reveal_in_folder(str(item.get("filePath","")))

    @Slot(str,result=bool)
    def deleteOutput(self,output_id:str)->bool:
        try:self.service.delete_output(self._project_id,output_id);self.refresh();self.operationSucceeded.emit("Rendered video deleted.");return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(object)
    def _apply_progress(self,state)->None:
        self._progress=float(state.overall_progress);self._stage=str(state.stage);self._speed=float(state.speed); labels={"rendering_scene":f"Rendering scene {state.scene_index+1} / {state.scene_count}","combining_scenes":"Combining scenes","finalizing":"Finalizing video"};self._status=labels.get(self._stage,self._stage.replace("_"," ").title());self.stateChanged.emit()

    @Slot(object)
    def _apply_result(self,item)->None:
        self._busy=False;self._progress=1;self._stage="completed";self._status="Video ready";self._last_output=self._output_map(item);self.refresh();self.stateChanged.emit();self.operationSucceeded.emit("Video rendering completed.")

    @Slot(object)
    def _apply_failure(self,exc)->None:
        self._busy=False;self._stage="cancelled" if isinstance(exc,RenderCancelled) else "failed";self._status="Render cancelled" if isinstance(exc,RenderCancelled) else "Video rendering failed";self.stateChanged.emit()
        if not isinstance(exc,RenderCancelled):self.operationFailed.emit(self._friendly(exc))

    def _done(self,future:Future)->None:
        try:self._jobReady.emit(future.result())
        except Exception as exc:self._jobFailed.emit(exc)

    @staticmethod
    def _output_map(item):
        data=item.to_dict();data["name"]=Path(item.file_path).name;data["durationText"]=format_duration(item.duration_ms);data["fileSizeText"]=format_file_size(item.file_size);data["resolutionText"]=f"{item.width} × {item.height}";return data

    @staticmethod
    def _friendly(exc:Exception)->str:
        text=str(exc).strip();return text if text else "SP Video Studio could not render this video."

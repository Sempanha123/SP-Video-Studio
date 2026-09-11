from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl

from domain.export_request import ExportRequest
from rendering.errors import RenderCancelled
from services.export_service import ExportService
from services.platform_service import open_path, reveal_in_folder
from ui.models.media_format import format_duration, format_file_size
from workers.cancellation import CancellationToken
from workers.worker_pool import WorkerPool


class ExportController(QObject):
    contextChanged=Signal(); stateChanged=Signal(); presetsChanged=Signal(); historyChanged=Signal(); validationChanged=Signal()
    operationSucceeded=Signal(str); operationFailed=Signal(str); playRequested=Signal(str,str,int)
    _progressReady=Signal(object); _doneReady=Signal(object); _doneFailed=Signal(object)

    def __init__(self,service:ExportService,worker_pool:WorkerPool,logger=None,parent=None)->None:
        super().__init__(parent); self.service=service; self.worker_pool=worker_pool; self.logger=logger or logging.getLogger("sp_video_studio.export_controller")
        self._project_id=""; self._draft={}; self._presets=[]; self._encoders=[]; self._subtitle_tracks=[]; self._history=[]; self._issues=[]; self._summary={}; self._last_output={}; self._last_request:ExportRequest|None=None
        self._busy=False; self._progress=0.0; self._stage="setup"; self._status="Ready to export"; self._speed=0.0; self._token:CancellationToken|None=None; self._future:Future|None=None; self._pre_export_flush:Callable[[],bool]|None=None
        self._progressReady.connect(self._apply_progress); self._doneReady.connect(self._apply_result); self._doneFailed.connect(self._apply_failure)

    def set_pre_export_flush(self,callback:Callable[[],bool])->None:self._pre_export_flush=callback

    @Property(str,notify=contextChanged)
    def currentProjectId(self):return self._project_id
    @Property("QVariantMap",notify=contextChanged)
    def draft(self):return dict(self._draft)
    @Property("QVariantList",notify=presetsChanged)
    def presets(self):return list(self._presets)
    @Property("QVariantList",notify=contextChanged)
    def encoderOptions(self):return list(self._encoders)
    @Property("QVariantList",notify=contextChanged)
    def subtitleTracks(self):return list(self._subtitle_tracks)
    @Property("QVariantList",notify=historyChanged)
    def history(self):return list(self._history)
    @Property("QVariantList",notify=validationChanged)
    def validationIssues(self):return list(self._issues)
    @Property("QVariantMap",notify=validationChanged)
    def summary(self):return dict(self._summary)
    @Property("QVariantMap",notify=stateChanged)
    def lastOutput(self):return dict(self._last_output)
    @Property(bool,notify=stateChanged)
    def busy(self):return self._busy
    @Property(float,notify=stateChanged)
    def progress(self):return self._progress
    @Property(float,notify=stateChanged)
    def speed(self):return self._speed
    @Property(str,notify=stateChanged)
    def stage(self):return self._stage
    @Property(str,notify=stateChanged)
    def statusMessage(self):return self._status

    @Slot(str)
    def setCurrentProject(self,project_id:str)->None:
        project_id=(project_id or "").strip()
        if project_id==self._project_id and self._draft:return
        if self._busy:self.cancel()
        self._project_id=project_id; self._last_output={}; self._issues=[]; self._summary={}; self._progress=0; self._stage="setup"; self._status="Ready to export"
        self.refresh()
        if project_id:
            try:self._draft=self.service.default_request(project_id).to_dict()
            except Exception as exc:self._draft={};self.operationFailed.emit(self._friendly(exc))
        else:self._draft={}
        self.contextChanged.emit();self.stateChanged.emit();self.validationChanged.emit()

    @Slot()
    def refresh(self)->None:
        try:self._presets=[p.to_dict() for p in self.service.presets.list_all()]
        except Exception:self._presets=[]
        try:self._encoders=self.service.encoder_options()
        except Exception:self._encoders=[{"id":"auto","name":"Auto","available":True}]
        if self._project_id:
            try:self._subtitle_tracks=self.service.subtitle_tracks(self._project_id)
            except Exception:self._subtitle_tracks=[]
            try:self._history=[self._output_map(x) for x in self.service.history(self._project_id,30)]
            except Exception:self._history=[]
        else:self._subtitle_tracks=[];self._history=[]
        self.presetsChanged.emit();self.historyChanged.emit();self.contextChanged.emit()

    @Slot(QUrl,result=str)
    def localPathFromUrl(self,url:QUrl)->str:
        return url.toLocalFile() if url.isLocalFile() else url.toString()

    @Slot(str,result=bool)
    def selectPreset(self,preset_id:str)->bool:
        if not self._project_id:return False
        try:
            req=self._request(); self.service.apply_preset(req,preset_id); self._draft=req.to_dict(); self._issues=[];self._summary={};self.contextChanged.emit();self.validationChanged.emit();return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot("QVariantMap",result=bool)
    def updateDraft(self,changes)->bool:
        try:
            data=dict(self._draft); data.update(dict(changes or {})); data["projectId"]=self._project_id
            req=ExportRequest.from_dict(data); self._draft=req.to_dict(); self._issues=[];self._summary={};self.contextChanged.emit();self.validationChanged.emit();return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(result="QVariantList")
    def validateDraft(self):
        try:
            issues,summary=self.service.validate(self._request()); self._issues=[{"severity":i.severity,"code":i.code,"message":i.message,"sceneId":i.scene_id} for i in issues]; self._summary=self._summary_map(summary.to_dict()); self.validationChanged.emit(); return list(self._issues)
        except Exception as exc:
            self._issues=[{"severity":"error","code":"export_invalid","message":self._friendly(exc)}];self._summary={};self.validationChanged.emit();return list(self._issues)

    @Slot(result=bool)
    def start(self)->bool:
        if self._busy or not self._project_id:return False
        if self._pre_export_flush and not self._pre_export_flush():self.operationFailed.emit("Project changes could not be saved, so export did not start.");return False
        req=self._request(); issues=self.validateDraft()
        if any(i.get("severity")=="error" for i in issues):return False
        self._last_request=ExportRequest.from_dict(req.to_dict()); self._token=CancellationToken(); self._busy=True;self._progress=0;self._stage="preparing";self._status="Preparing export…";self.stateChanged.emit()
        def report(state):self._progressReady.emit(state)
        self._future=self.worker_pool.submit(self.service.export,req,cancellation=self._token,progress_callback=report);self._future.add_done_callback(self._done);return True

    @Slot()
    def cancel(self)->None:
        if self._busy and self._token:self._token.cancel();self._stage="cancelling";self._status="Stopping export…";self.stateChanged.emit()

    @Slot(result=bool)
    def retry(self)->bool:
        if not self._last_request or self._busy:return False
        self._draft=self._last_request.to_dict();self.contextChanged.emit();return self.start()

    @Slot(str,result=bool)
    def exportAgain(self,output_id:str)->bool:
        try:self._draft=self.service.request_from_output(self._project_id,output_id).to_dict();self._stage="setup";self._last_output={};self.contextChanged.emit();self.stateChanged.emit();return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(str,str,result=bool)
    def saveAsPreset(self,name:str,description:str)->bool:
        try:self.service.presets.create_custom(name,description,self._request());self.refresh();self.operationSucceeded.emit("Export preset saved.");return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(str,result=bool)
    def duplicatePreset(self,preset_id:str)->bool:
        try:self.service.presets.duplicate(preset_id);self.refresh();self.operationSucceeded.emit("Export preset duplicated.");return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(str,result=bool)
    def deletePreset(self,preset_id:str)->bool:
        try:self.service.presets.delete(preset_id);self.refresh();self.operationSucceeded.emit("Export preset deleted.");return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(str)
    def playOutput(self,output_id:str)->None:
        item=self._find_output(output_id)
        if item and Path(str(item.get("filePath",""))).is_file():self.playRequested.emit(str(item["filePath"]),str(item.get("name","Exported video")),int(item.get("durationMs",0) or 0))

    @Slot(str)
    def openFile(self,output_id:str)->None:
        item=self._find_output(output_id)
        if item and Path(str(item.get("filePath",""))).exists():open_path(str(item["filePath"]))

    @Slot(str)
    def openFolder(self,output_id:str)->None:
        item=self._find_output(output_id)
        if item:reveal_in_folder(str(item.get("filePath","")))

    @Slot(str,bool,result=bool)
    def deleteOutput(self,output_id:str,allow_external:bool=False)->bool:
        try:self.service.delete_export(self._project_id,output_id,allow_external=allow_external);self.refresh();self.operationSucceeded.emit("Export deleted.");return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(str,result=bool)
    def removeFromHistory(self,output_id:str)->bool:
        try:self.service.remove_history(self._project_id,output_id);self.refresh();return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc));return False

    @Slot(object)
    def _apply_progress(self,state)->None:
        self._progress=float(state.overall_progress);self._speed=float(state.speed);self._stage=str(state.stage);labels={"rendering_scene":f"Rendering scene {state.scene_index+1} / {state.scene_count}","combining_scenes":"Combining scenes","finalizing":"Finalizing video"};self._status=labels.get(self._stage,self._stage.replace("_"," ").title());self.stateChanged.emit()

    @Slot(object)
    def _apply_result(self,item)->None:
        self._busy=False;self._progress=1;self._stage="completed";self._status="Video ready";self._last_output=self._output_map(item);self.refresh();self.stateChanged.emit();self.operationSucceeded.emit("Video export completed.")

    @Slot(object)
    def _apply_failure(self,exc)->None:
        self._busy=False;self._stage="cancelled" if isinstance(exc,RenderCancelled) else "failed";self._status="Export cancelled" if isinstance(exc,RenderCancelled) else "Export failed";self.stateChanged.emit()
        if not isinstance(exc,RenderCancelled):self.operationFailed.emit(self._friendly(exc))

    def _done(self,future:Future)->None:
        try:self._doneReady.emit(future.result())
        except Exception as exc:self._doneFailed.emit(exc)

    def _request(self)->ExportRequest:
        data=dict(self._draft);data["projectId"]=self._project_id;return ExportRequest.from_dict(data)

    def _find_output(self,output_id:str):
        return next((x for x in self._history if x.get("id")==output_id),None) or (self._last_output if self._last_output.get("id")==output_id else None)

    @staticmethod
    def _summary_map(data:dict)->dict:
        result=dict(data);result["durationText"]=format_duration(int(result.get("durationMs",0) or 0));result["estimatedSizeText"]=format_file_size(int(result.get("estimatedSizeBytes",0) or 0));return result

    @staticmethod
    def _output_map(item):
        data=item.to_dict(); path=Path(item.file_path);data["name"]=path.name;data["durationText"]=format_duration(item.duration_ms);data["fileSizeText"]=format_file_size(item.file_size);data["resolutionText"]=f"{item.width} × {item.height}";data["fileMissing"]=not path.is_file();data["externalOutput"]=bool(item.metadata.get("externalOutput",False));data["presetId"]=str(item.metadata.get("exportPresetId",item.metadata.get("presetId","")));return data

    @staticmethod
    def _friendly(exc:Exception)->str:
        text=str(exc).strip();return text if text else "SP Video Studio could not export this video."

from __future__ import annotations

import logging
from concurrent.futures import Future

from PySide6.QtCore import QObject, Property, Signal, Slot

from commands.timeline.commands import ValueCommand
from services.manual_speech_editor_service import ManualSpeechEditorService, ManualSpeechError, format_timecode
from workers.cancellation import CancellationToken


class ManualSpeechController(QObject):
    rowsChanged=Signal(); selectionChanged=Signal(); optionsChanged=Signal(); stateChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str)
    timelineRefreshRequested=Signal(); seekRequested=Signal(int,bool); playAudioRequested=Signal(str); voicePreviewRequested=Signal(str); togglePreviewRequested=Signal(); _jobDone=Signal(object,object); _progress=Signal(object)

    def __init__(self,service:ManualSpeechEditorService,workers,*,command_stack=None,autosave=None,logger=None,parent=None):
        super().__init__(parent);self.service=service;self.workers=workers;self.command_stack=command_stack;self.logger=logger or logging.getLogger("sp_video_studio.manual_speech")
        self.autosave=autosave;self._project_id="";self._rows=[];self._speakers=[];self._voices=[];self._selected:set[str]=set();self._busy=False;self._current=0;self._total=0;self._current_label="";self._token=None;self._future=None
        self._jobDone.connect(self._apply_job_done);self._progress.connect(self._apply_progress)

    @Property(str,notify=rowsChanged)
    def currentProjectId(self):return self._project_id
    @Property('QVariantList',notify=rowsChanged)
    def rows(self):return list(self._rows)
    @Property('QVariantList',notify=optionsChanged)
    def speakers(self):return list(self._speakers)
    @Property('QVariantList',notify=optionsChanged)
    def voices(self):return list(self._voices)
    @Property('QVariantList',notify=selectionChanged)
    def selectedIds(self):return list(self._selected)
    @Property(int,notify=selectionChanged)
    def selectedCount(self):return len(self._selected)
    @Property(bool,notify=stateChanged)
    def busy(self):return self._busy
    @Property(int,notify=stateChanged)
    def generationCurrent(self):return self._current
    @Property(int,notify=stateChanged)
    def generationTotal(self):return self._total
    @Property(str,notify=stateChanged)
    def generationLabel(self):return self._current_label
    @Property('QVariantMap',notify=selectionChanged)
    def selectedRow(self):
        if not self._selected:return {}
        key=next(iter(self._selected));return dict(next((r for r in self._rows if r.get("id")==key),{}))

    @Slot(str)
    def setCurrentProject(self,project_id:str):
        value=(project_id or "").strip()
        if value==self._project_id:return
        self.cancelGeneration();self._project_id=value;self._selected.clear();self.refresh();self.selectionChanged.emit()

    @Slot()
    def refresh(self):
        if not self._project_id:self._rows=[];self._speakers=[];self._voices=[]
        else:
            try:
                self._rows=self.service.rows(self._project_id);self._speakers=self.service.speakers(self._project_id);self._voices=self.service.voices_list()
            except Exception as exc:self._fail(exc);return
        self.rowsChanged.emit();self.optionsChanged.emit()

    @Slot(str,bool)
    def select(self,block_id:str,selected:bool=True):
        if selected:self._selected.add(block_id)
        else:self._selected.discard(block_id)
        self.selectionChanged.emit()

    @Slot()
    def clearSelection(self):self._selected.clear();self.selectionChanged.emit()
    @Slot()
    def selectAll(self):self._selected={str(r.get("id","")) for r in self._rows if r.get("id")};self.selectionChanged.emit()
    @Slot(str)
    def selectStatus(self,status:str):
        key=(status or "").strip().lower();self._selected=set()
        for row in self._rows:
            audio=str(row.get("audioStatus","")).lower()
            if key=="outdated" and audio=="outdated":self._selected.add(row["id"])
            elif key=="failed" and audio=="failed":self._selected.add(row["id"])
            elif key in {"ungenerated","not_generated"} and audio=="not_generated":self._selected.add(row["id"])
        self.selectionChanged.emit()

    @Slot(str,str,result=bool)
    def editText(self,block_id:str,text:str):
        try:
            before=self.service.blocks.repository.block(self._project_id,block_id).text
            self.service.edit_text(self._project_id,block_id,text)
            self._push_value("Speech Text",lambda value:self.service.edit_text(self._project_id,block_id,str(value)),before,text,f"speech:{block_id}:text")
            return self._changed("Speech text saved")
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,str,result=bool)
    def setTimingText(self,block_id:str,start_text:str,end_text:str):
        try:
            old=self.service.blocks.repository.block(self._project_id,block_id);before=(old.timeline_start_ms,old.timeline_end_ms)
            item=self.service.set_timing_text(self._project_id,block_id,start_text,end_text);after=(item.timeline_start_ms,item.timeline_end_ms)
            self._push_value("Speech Timing",lambda pair:self.service.set_timing(self._project_id,block_id,int(pair[0]),int(pair[1])),before,after,f"speech:{block_id}:timing")
            return self._changed("Speech timing updated")
        except Exception as exc:self._fail(exc);return False

    @Slot(str,int,int,result=bool)
    def setTimingMs(self,block_id:str,start_ms:int,end_ms:int):
        try:
            old=self.service.blocks.repository.block(self._project_id,block_id);before=(old.timeline_start_ms,old.timeline_end_ms)
            item=self.service.set_timing(self._project_id,block_id,start_ms,end_ms);after=(item.timeline_start_ms,item.timeline_end_ms)
            self._push_value("Speech Timing",lambda pair:self.service.set_timing(self._project_id,block_id,int(pair[0]),int(pair[1])),before,after,f"speech:{block_id}:timing")
            return self._changed("Speech timing updated")
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,result=bool)
    def addSpeech(self,section_id:str,text:str="New speech"):
        try:
            sid=section_id or self._default_section()
            if not sid:raise ManualSpeechError("Create or open a script section before adding speech.")
            language=str((self._rows[0].get("language") if self._rows else "en") or "en")
            start=max([int(r.get("timelineEndMs") or 0) for r in self._rows] or [0]);self.service.add(self._project_id,sid,text=text,language=language,start_ms=start,end_ms=start+2000);return self._changed("Speech block added")
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def deleteSelected(self):
        try:self.service.delete(self._project_id,self._selected);self._selected.clear();self.selectionChanged.emit();return self._changed("Selected speech removed")
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,str,int,result=bool)
    def splitBlock(self,block_id:str,before_text:str,after_text:str,split_ms:int):
        try:self.service.split(self._project_id,block_id,split_ms,before_text,after_text);return self._changed("Speech block split")
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,str,str,result=bool)
    def mergeBlocks(self,first_id:str,second_id:str,speaker_id:str="",voice_id:str=""):
        try:self.service.merge(self._project_id,first_id,second_id,speaker_id=(speaker_id or None),voice_id=(voice_id or None));return self._changed("Speech blocks merged")
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,str,result=int)
    def replaceText(self,query:str,replacement:str,scope:str="selected"):
        try:
            ids=self._selected if scope=="selected" else None;items=self.service.replace(self._project_id,query,replacement,block_ids=ids,replace_all=(scope!="current"));self.refresh();self.timelineRefreshRequested.emit();return len(items)
        except Exception as exc:self._fail(exc);return 0

    @Slot(str,result=bool)
    def setSpeakerSelected(self,speaker_id:str):return self._bulk(speaker_id=speaker_id)
    @Slot(str,result=bool)
    def setVoiceSelected(self,voice_id:str):return self._bulk(voice_id=voice_id)
    @Slot(str,result=bool)
    def setLanguageSelected(self,language:str):return self._bulk(language=language)

    @Slot(str,str,str,str,str,bool)
    def filterVoices(self,language:str="all",role:str="all",style:str="",tone:str="",energy:str="",favorites:bool=False):
        try:self._voices=self.service.voices_list(language=language,role=role,style=style,tone=tone,energy=energy,favorites=favorites);self.optionsChanged.emit()
        except Exception as exc:self._fail(exc)

    @Slot(str,result='QVariantList')
    def takesFor(self,block_id:str):
        try:return self.service.takes(self._project_id,block_id)
        except Exception as exc:self._fail(exc);return []
    @Slot(str,str,result=bool)
    def activateTake(self,block_id:str,audio_id:str):
        try:self.service.activate_take(self._project_id,block_id,audio_id);return self._changed("Speech take activated")
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def generateSelected(self):return self._start_generation(list(self._selected),False,False)
    @Slot(result=bool)
    def generateOutdated(self):return self._start_generation([],True,False)
    @Slot(result=bool)
    def generateAll(self):return self._start_generation([],False,True)
    @Slot()
    def cancelGeneration(self):
        if self._token:self._token.cancel();self._current_label="Cancelling remaining…";self.stateChanged.emit()

    @Slot(str,result=bool)
    def fitAudio(self,block_id:str):
        try:
            row=next((r for r in self._rows if r.get("id")==block_id),{});duration=int((row.get("metadata") or {}).get("generatedDurationMs",0) or 0);self.service.blocks.fit_audio(self._project_id,block_id,duration);return self._changed("Audio fit saved")
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def extendSegment(self,block_id:str):
        try:
            row=next((r for r in self._rows if r.get("id")==block_id),{});duration=int((row.get("metadata") or {}).get("generatedDurationMs",0) or 0);self.service.blocks.extend_segment(self._project_id,block_id,duration);return self._changed("Speech segment extended")
        except Exception as exc:self._fail(exc);return False

    @Slot(str)
    def seekRow(self,block_id:str):
        row=next((r for r in self._rows if r.get("id")==block_id),None)
        if row:self.seekRequested.emit(int(row.get("timelineStartMs") or 0),False)
    @Slot(str)
    def playTake(self,audio_id:str):
        try:
            item=self.service.audio.get(audio_id)
            if item:self.playAudioRequested.emit(str(item.file_path))
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def previewVoice(self,voice_id:str):
        value=(voice_id or "").strip()
        if value:self.voicePreviewRequested.emit(value)

    @Slot()
    def togglePreview(self):self.togglePreviewRequested.emit()

    def _start_generation(self,ids,outdated,all_rows)->bool:
        if self._busy:return False
        if not all_rows and not outdated and not ids:self.operationFailed.emit("Select one or more TTS speech rows first.");return False
        self._busy=True;self._current=0;self._total=0;self._current_label="Preparing speech generation…";self._token=CancellationToken();self.stateChanged.emit()
        def progress(value):self._progress.emit(value)
        def job():return self.service.generate(self._project_id,ids,outdated_only=outdated,all_rows=all_rows,cancellation=self._token,progress_callback=progress)
        self._future=self.workers.submit(job);self._future.add_done_callback(lambda f:self._jobDone.emit(None if f.exception() else f.result(),f.exception()));return True

    @Slot(object)
    def _apply_progress(self,value):
        self._current=int(getattr(value,"current",0));self._total=int(getattr(value,"total",0));self._current_label=f"{getattr(value,'speaker','Speech')} — {format_timecode(getattr(value,'start_ms',None))}";self.stateChanged.emit();self.refresh()
    @Slot(object,object)
    def _apply_job_done(self,result,error):
        self._busy=False;self._token=None;self._future=None
        if error is not None:self._current_label="Generation stopped";self.stateChanged.emit();self.refresh();self._fail(error);return
        self._current=self._total;self._current_label="Speech generation complete";self.stateChanged.emit();self.refresh();self.timelineRefreshRequested.emit();self.operationSucceeded.emit("Speech audio generated")

    def _bulk(self,**kwargs)->bool:
        try:
            if not self._selected:raise ManualSpeechError("Select one or more speech rows first.")
            self.service.bulk_assign(self._project_id,self._selected,**kwargs);return self._changed("Selected speech updated")
        except Exception as exc:self._fail(exc);return False
    def _changed(self,message:str)->bool:
        if self.autosave is not None and self._project_id:
            try:self.autosave.mark_structural_saved(self._project_id,"speech_text")
            except Exception:pass
        self.refresh();self.timelineRefreshRequested.emit();self.operationSucceeded.emit(message);return True
    def _push_value(self,label,setter,before,after,key):
        if self.command_stack is None or before==after:return
        try:self.command_stack.push_executed(ValueCommand(label,setter,before,after,key))
        except Exception:pass
    def _default_section(self)->str:
        try:
            with self.service.blocks.repository.database.connect() as c:
                row=c.execute("""SELECT s.id FROM script_sections s JOIN scripts sc ON sc.id=s.script_id WHERE sc.project_id=? ORDER BY s.section_order LIMIT 1""",(self._project_id,)).fetchone()
            return str(row["id"]) if row else ""
        except Exception:return ""
    def _fail(self,exc):
        self.logger.exception("Manual Speech editor action failed");self.operationFailed.emit(str(exc).strip() or "Speech editor could not complete this action.")

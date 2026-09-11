from __future__ import annotations

import logging
from concurrent.futures import Future
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from services.media_service import MediaService
from services.subtitle_preset_service import SubtitlePresetService
from services.subtitle_preview_service import SubtitlePreviewService
from services.subtitle_service import SubtitleService
from services.subtitle_timing_service import SubtitleTimingService
from ui.models.subtitle_cue_model import SubtitleCueListModel
from workers.worker_pool import WorkerPool


class SubtitleController(QObject):
    contextChanged=Signal(); trackChanged=Signal(); tracksChanged=Signal(); stateChanged=Signal(); presetsChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str); playbackRequested=Signal(str,int,bool); previewReady=Signal(str); _previewDone=Signal(object); _previewFailed=Signal(object)
    def __init__(self,service:SubtitleService,presets:SubtitlePresetService,preview:SubtitlePreviewService,media_service:MediaService,worker_pool:WorkerPool,logger=None,parent=None):
        super().__init__(parent); self.service=service; self.presets=presets; self.preview=preview; self.media_service=media_service; self.worker_pool=worker_pool; self.logger=logger or logging.getLogger('sp_video_studio.subtitle_controller')
        self.cueModel=SubtitleCueListModel(self); self._project_id=""; self._track=None; self._style=None; self._selected_cue=""; self._save_state='Saved'; self._dirty={}; self._busy=False; self._playhead=0; self._active_cue={}
        self._timer=QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(900); self._timer.timeout.connect(self.saveEdits); self._previewDone.connect(self._apply_preview); self._previewFailed.connect(self._preview_failure)
    @Property(QObject,constant=True)
    def cues(self): return self.cueModel
    @Property(str,notify=contextChanged)
    def currentProjectId(self): return self._project_id
    @Property('QVariantList',notify=tracksChanged)
    def tracks(self):
        if not self._project_id: return []
        try: return [{**t.to_dict(),"statusName":t.status_code.replace('_',' ').title(),"cueCount":len(self.service.repository.cues(t.track_id))} for t in self.service.list_tracks(self._project_id)]
        except Exception: return []
    @Property('QVariantMap',notify=contextChanged)
    def sources(self):
        try: return self.service.source_options(self._project_id) if self._project_id else {"transcripts":[],"translations":[]}
        except Exception: return {"transcripts":[],"translations":[]}
    @Property('QVariantList',notify=presetsChanged)
    def presetList(self): return self.presets.list_presets()
    @Property('QVariantMap',notify=trackChanged)
    def track(self): return self._track.to_dict() if self._track else {}
    @Property('QVariantMap',notify=trackChanged)
    def style(self): return self._style.to_dict() if self._style else {}
    @Property(str,notify=trackChanged)
    def selectedCueId(self): return self._selected_cue
    @Property(str,notify=stateChanged)
    def saveState(self): return self._save_state
    @Property(int,notify=trackChanged)
    def cueCount(self): return len(self.cueModel.all_cues())
    @Property(bool,notify=stateChanged)
    def busy(self): return self._busy
    @Property(int,notify=stateChanged)
    def playhead(self): return self._playhead
    @Property('QVariantMap',notify=stateChanged)
    def activeCue(self): return dict(self._active_cue)
    @Property('QVariantMap',notify=trackChanged)
    def validationSummary(self):
        if not self._track: return {"errors":0,"warnings":0,"issues":[]}
        issues=self.service.validate_track(self._project_id,self._track.track_id); errors,warnings=self.service.validation_service.counts(issues)
        return {"errors":errors,"warnings":warnings,"issues":[i.to_dict() for i in issues]}
    @Slot(str)
    def setCurrentProject(self,project_id):
        if project_id==self._project_id:return
        self.flush(); self._project_id=project_id or ''; self._track=None; self._style=None; self._selected_cue=''; self.cueModel.replace([]); self.contextChanged.emit(); self.tracksChanged.emit(); self.trackChanged.emit()
        if self._project_id:
            try:
                tracks=self.service.list_tracks(self._project_id)
                preferred=next((item for item in tracks if item.is_default), tracks[0] if tracks else None)
                if preferred: self.loadTrack(preferred.track_id)
            except Exception: pass
    @Slot(str,result=bool)
    def loadTrack(self,track_id):
        if not self.flush(): return False
        try:
            self._track,self._style,cues=self.service.get(self._project_id,track_id); self.cueModel.replace(cues); self._selected_cue=cues[0].cue_id if cues else ''; self.trackChanged.emit(); return True
        except Exception as exc: self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,str,result=bool)
    def createFromTranscript(self,transcript_id,preset_id='clean'):
        try: t=self.service.create_from_transcript(self._project_id,transcript_id,preset_id=preset_id); self.tracksChanged.emit(); return self.loadTrack(t.track_id)
        except Exception as exc: self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,str,result=bool)
    def createFromTranslation(self,translation_id,preset_id='clean'):
        try: t=self.service.create_from_translation(self._project_id,translation_id,preset_id=preset_id); self.tracksChanged.emit(); return self.loadTrack(t.track_id)
        except Exception as exc: self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,str,str,str,result=bool)
    def createBilingual(self,transcript_id,translation_id,preset_id='clean',primary='source'):
        try: t=self.service.create_bilingual(self._project_id,transcript_id,translation_id,preset_id=preset_id,primary=primary); self.tracksChanged.emit(); return self.loadTrack(t.track_id)
        except Exception as exc: self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,str,result=bool)
    def createManual(self,language,preset_id='clean'):
        try: t=self.service.create_manual(self._project_id,language,preset_id=preset_id); self.tracksChanged.emit(); return self.loadTrack(t.track_id)
        except Exception as exc: self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,str,str,result=bool)
    def importSubtitle(self,url,language,preset_id='clean'):
        try: t=self.service.import_file(self._project_id,self._url_path(url),language,preset_id=preset_id); self.tracksChanged.emit(); return self.loadTrack(t.track_id)
        except Exception as exc: self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str)
    def selectCue(self,cue_id):
        self._selected_cue=cue_id; cue=self.cueModel.cue(cue_id)
        if cue and self._track:
            media_id=self.service.media_id_for_track(self._project_id,self._track.track_id)
            if media_id:self.playbackRequested.emit(media_id,cue.start_ms,False)
        self.trackChanged.emit()
    @Slot(str,str,str)
    def queueText(self,cue_id,text,secondary=''):
        self._dirty[cue_id]=(text,secondary); self._save_state='Unsaved'; self._timer.start(); self.stateChanged.emit()
    @Slot(result=bool)
    def saveEdits(self):
        if not self._track or not self._dirty: self._save_state='Saved'; self.stateChanged.emit(); return True
        dirty=dict(self._dirty); self._save_state='Saving…'; self.stateChanged.emit()
        try:
            for cue_id,(text,secondary) in dirty.items(): self.service.update_cue(self._project_id,self._track.track_id,cue_id,text=text,secondary_text=secondary)
            self._dirty.clear(); self._save_state='Saved'; self._reload(); return True
        except Exception as exc: self._save_state='Save Failed'; self.operationFailed.emit(self._friendly(exc)); self.stateChanged.emit(); return False
    @Slot(result=bool)
    def flush(self):
        self._timer.stop(); return self.saveEdits()
    @Slot(str,int,int,result=bool)
    def setTiming(self,cue_id,start_ms,end_ms):
        try:self.service.update_cue(self._project_id,self._track.track_id,cue_id,start_ms=start_ms,end_ms=end_ms); self._reload(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,int,str,str,result=bool)
    def splitCue(self,cue_id,split_ms,before,after):
        try:self.service.split_cue(self._project_id,self._track.track_id,cue_id,split_ms,before,after); self._reload(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,str,result=bool)
    def mergeCues(self,first_id,second_id):
        try:self.service.merge_cues(self._project_id,self._track.track_id,first_id,second_id); self._reload(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(int,result=bool)
    def shiftAll(self,delta_ms):
        try:self.service.shift_timing(self._project_id,self._track.track_id,delta_ms); self._reload(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(result=bool)
    def addCueAtPlayhead(self):
        try:q=self.service.add_cue(self._project_id,self._track.track_id,self._playhead); self._reload(); self.selectCue(q.cue_id); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,result=bool)
    def deleteCue(self,cue_id):
        try:self.service.delete_cue(self._project_id,self._track.track_id,cue_id); self._reload(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,result=bool)
    def applyPreset(self,preset_id):
        try:self._style=self.service.apply_preset(self._project_id,self._track.track_id,preset_id); self.trackChanged.emit(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,'QVariant',result=bool)
    def setStyleValue(self,key,value):
        try:self._style=self.service.update_style(self._project_id,self._track.track_id,{key:value}); self.trackChanged.emit(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,result=bool)
    def saveStylePreset(self,name):
        try:self.presets.save_user_preset(name,self._style); self.presetsChanged.emit(); self.operationSucceeded.emit('Subtitle preset saved'); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,result=bool)
    def deletePreset(self,preset_id):
        try:self.presets.delete_user_preset(preset_id); self.presetsChanged.emit(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,str,result=bool)
    def exportTrack(self,fmt,url):
        try:self.service.export(self._project_id,self._track.track_id,fmt,self._url_path(url)); self.operationSucceeded.emit('Subtitles exported'); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(result=bool)
    def syncSource(self):
        try:result=self.service.sync_source(self._project_id,self._track.track_id); self._reload(); self.operationSucceeded.emit(f"Source sync: {result['added']} added, {result['changed']} changed"); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,result=bool)
    def setDefault(self,track_id):
        try:self.service.set_default(self._project_id,track_id); self.tracksChanged.emit(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,result=bool)
    def duplicateTrack(self,track_id):
        try:t=self.service.duplicate_track(self._project_id,track_id); self.tracksChanged.emit(); return self.loadTrack(t.track_id)
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str,result=bool)
    def deleteTrack(self,track_id):
        try:self.service.delete_track(self._project_id,track_id); self._track=None; self._style=None; self.cueModel.replace([]); self.tracksChanged.emit(); self.trackChanged.emit(); return True
        except Exception as exc:self.operationFailed.emit(self._friendly(exc)); return False
    @Slot(str)
    def search(self,value): self.cueModel.set_search(value)
    @Slot(str)
    def filter(self,value): self.cueModel.set_filter(value)
    @Slot(int)
    def setPlayhead(self,value):
        self._playhead=int(value); self.cueModel.set_playhead(value); self._active_cue={}
        cues=self.cueModel.all_cues(); lo,hi=0,len(cues)-1
        while lo<=hi:
            mid=(lo+hi)//2; cue=cues[mid]
            if self._playhead<cue.start_ms: hi=mid-1
            elif self._playhead>=cue.end_ms: lo=mid+1
            else:
                active_word=""
                for word in cue.words:
                    if word.start_ms<=self._playhead<word.end_ms: active_word=word.text; break
                self._active_cue={"id":cue.cue_id,"text":cue.text,"secondaryText":cue.secondary_text,"activeWord":active_word,"startMs":cue.start_ms,"endMs":cue.end_ms}; break
        self.stateChanged.emit()
    @Slot(result=bool)
    def renderPreview(self):
        if self._busy or not self._track:
            return False
        try:
            media_id=self.service.media_id_for_track(self._project_id,self._track.track_id)
            if not media_id:
                raise RuntimeError("A video source is required to render a subtitle preview.")
            asset=self.media_service.get_media(self._project_id,media_id)
            if asset.type != "video":
                raise RuntimeError("Subtitle burn-in preview requires a video source.")
            project=self.service.project_repository.get_by_id(self._project_id)
            if project is None:
                raise RuntimeError("Project could not be found.")
            cache=Path(project.project_path)/"cache"/"subtitles"
            cache.mkdir(parents=True,exist_ok=True)
            subtitle_path=cache/f"{self._track.track_id}-preview.ass"
            destination=cache/f"{self._track.track_id}-preview.mp4"
            self.service.export(self._project_id,self._track.track_id,"ass",subtitle_path)
            self._busy=True; self.stateChanged.emit()
            future=self.worker_pool.submit(self.preview.render,Path(asset.project_path),subtitle_path,destination,start_ms=max(0,self._playhead-1000),duration_ms=7000)
            future.add_done_callback(self._preview_future_done)
            return True
        except Exception as exc:
            self._busy=False; self.stateChanged.emit(); self.operationFailed.emit(self._friendly(exc)); return False
    def _preview_future_done(self,future:Future):
        try: self._previewDone.emit(future.result())
        except Exception as exc: self._previewFailed.emit(exc)
    @Slot(bool)
    def playSelected(self,autoplay=True):
        cue=self.cueModel.cue(self._selected_cue)
        if cue and self._track:
            media_id=self.service.media_id_for_track(self._project_id,self._track.track_id)
            if media_id:self.playbackRequested.emit(media_id,cue.start_ms,autoplay)
    def _reload(self):
        if self._track:self._track,self._style,cues=self.service.get(self._project_id,self._track.track_id); self.cueModel.replace(cues); self.trackChanged.emit(); self.stateChanged.emit()
    @staticmethod
    def _url_path(value):
        parsed=urlparse(str(value)); return Path(unquote(parsed.path.lstrip('/')) if parsed.scheme=='file' and len(parsed.path)>2 and parsed.path[2]==':' else unquote(parsed.path) if parsed.scheme=='file' else str(value))
    @staticmethod
    def _friendly(exc): return str(exc) or 'Subtitle action could not be completed.'
    def _apply_preview(self,value): self._busy=False; self.stateChanged.emit(); self.previewReady.emit(str(value))
    def _preview_failure(self,exc): self._busy=False; self.stateChanged.emit(); self.operationFailed.emit(self._friendly(exc))

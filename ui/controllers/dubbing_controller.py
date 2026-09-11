from __future__ import annotations

import logging
from PySide6.QtCore import QObject, Property, Signal, Slot

from domain.dub_mix_settings import DubMixSettings
from services.dubbing_validation_service import DubbingValidationService
from workers.cancellation import CancellationToken
from workers.dubbing_worker import DubbingWorker


class DubbingController(QObject):
    contextChanged=Signal(); segmentsChanged=Signal(); mixChanged=Signal(); readinessChanged=Signal(); optionsChanged=Signal(); busyChanged=Signal()
    operationSucceeded=Signal(str); operationFailed=Signal(str); navigationRequested=Signal(str)
    generationProgress=Signal(int,int,str); generationFinished=Signal(bool,str); previewRequested=Signal(str)

    def __init__(self, service, validation:DubbingValidationService, worker_pool=None, apply_service=None, transcript_repository=None, media_repository=None, logger=None, parent=None):
        super().__init__(parent); self.service=service; self.validation=validation; self.worker_pool=worker_pool; self.apply_service=apply_service
        self.logger=logger or logging.getLogger("sp_video_studio.dubbing_controller"); self.transcript_repository=transcript_repository; self.media_repository=media_repository
        self._project_id=""; self._project={}; self._segments=[]; self._mix={}; self._readiness={}
        self._busy=False; self._cancellation=None; self._future=None; self.generationFinished.connect(self._generation_done)

    @Property(str,notify=contextChanged)
    def currentProjectId(self): return self._project_id
    @Property('QVariantMap',notify=contextChanged)
    def project(self): return self._project
    @Property('QVariantList',notify=segmentsChanged)
    def segments(self): return self._segments
    @Property('QVariantMap',notify=mixChanged)
    def mixSettings(self): return self._mix
    @Property('QVariantMap',notify=readinessChanged)
    def readiness(self): return self._readiness
    @Property('QVariantMap',notify=contextChanged)
    def previewPaths(self):
        if not self._project_id:return {}
        output=self.service.repository.latest_output(self._project_id,"final_mix")
        if output is None:return {"sourceMediaId":self._project.get("sourceMediaId","")}
        return {"sourceMediaId":self._project.get("sourceMediaId",""),"mixed":output.file_path,"dub":str(output.metadata.get("narrationPath","") or ""),"durationMs":output.duration_ms}
    @Property('QVariantList',notify=optionsChanged)
    def sourceVideos(self):
        if not self._project_id or self.media_repository is None:return []
        try:return [{"id":m.id,"name":m.name,"durationMs":int(m.duration_ms or 0)} for m in self.media_repository.list_by_project(self._project_id,media_type="video") if getattr(m,"type","")=="video"]
        except Exception:return []
    @Property('QVariantList',notify=optionsChanged)
    def transcriptOptions(self):
        if not self._project_id or self.transcript_repository is None:return []
        try:return [{"id":t.id,"label":f"{(t.detected_language or t.language_mode or 'auto').upper()} · {t.status_code}","mediaId":t.media_id,"status":t.status_code} for t in self.transcript_repository.list_for_project(self._project_id) if t.status_code in {"ready","outdated"}]
        except Exception:return []
    @Property('QVariantList',notify=optionsChanged)
    def translationOptions(self):
        if not self._project_id:return []
        try:
            project=self.service.ensure_project(self._project_id); result=[]
            for t in self.service.translation_repository.list_for_project(self._project_id):
                if t.status_code in {"failed","cancelled"} or t.target_language!=project.target_language:continue
                if project.transcript_id and (t.source_type_code!="transcript" or t.source_id!=project.transcript_id):continue
                result.append({"id":t.id,"label":f"{t.source_language.upper()} → {t.target_language.upper()} · {t.status_code}","status":t.status_code})
            return result
        except Exception:return []
    @Property('QVariantList',notify=optionsChanged)
    def voiceOptions(self):
        if not self._project_id:return []
        try:
            project=self.service.ensure_project(self._project_id)
            return [{"id":v.voice_id,"label":f"{v.name} · {v.category}","name":v.name,"type":v.type_code} for v in self.service.voice_service.browse(language=project.target_language,project_language=project.target_language,project_workflow="translate")]
        except Exception:return []
    @Property(bool,notify=busyChanged)
    def busy(self): return self._busy

    @Slot(str)
    def setCurrentProject(self, project_id): self._project_id=(project_id or "").strip(); self.refresh()

    @Slot()
    def refresh(self):
        if not self._project_id:
            self._project={}; self._segments=[]; self._mix={}; self._readiness={}; self._emit_all(); return
        try:
            project=self.service.ensure_project(self._project_id); segments=self.service.repository.segments(self._project_id)
            output=self.service.repository.latest_output(self._project_id,"final_mix")
            self._project=project.to_dict(); self._segments=[s.to_dict() for s in segments]
            self._mix=self.service.repository.get_mix_settings(self._project_id).to_dict()
            self._readiness=self.validation.validate(project,segments,output).to_dict(); self._emit_all()
        except Exception as exc: self._fail(exc)

    @Slot(str,str,str,result=bool)
    def updateSetup(self, media_id, source_language, target_language):
        try:self.service.assign_source(self._project_id,media_id,source_language,target_language);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def linkTranscript(self, transcript_id):
        try:self.service.link_transcript(self._project_id,transcript_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def linkTranslation(self, translation_id):
        try:
            project=self.service.link_translation(self._project_id,translation_id)
            self.service.sync_translation_segments(self._project_id,self.service.translation_repository.segments(project.translation_id))
            self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def syncTranslation(self):
        try:
            project=self.service.ensure_project(self._project_id)
            if project.translation_id:self.service.sync_translation_segments(self._project_id,self.service.translation_repository.segments(project.translation_id))
            self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def setProjectVoice(self, voice_id):
        try:self.service.set_project_voice(self._project_id,voice_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,result=bool)
    def setSegmentVoice(self, segment_id, voice_id):
        try:self.service.set_segment_voice(self._project_id,segment_id,voice_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,int,bool,result=bool)
    def updateTiming(self, segment_id, mode, offset_ms, allow_overlap=False):
        try:self.service.update_timing(self._project_id,segment_id,timing_mode=mode,start_offset_ms=offset_ms,allow_overlap=allow_overlap);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,bool,result=bool)
    def lockSegment(self, segment_id, locked):
        try:self.service.lock_segment(self._project_id,segment_id,locked);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,float,float,float,float,int,result=bool)
    def updateMix(self, mode, original_volume, dub_volume, duck_normal, duck_under, fade_ms):
        try:
            item=DubMixSettings(self._project_id,mode,float(original_volume),float(dub_volume),float(duck_normal),float(duck_under),int(fade_ms))
            self.service.repository.save_mix_settings(item);self.service.repository.mark_outputs_outdated(self._project_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot('QVariantList',result=bool)
    def generateSelected(self, ids): return self._start_generation({str(x) for x in ids})
    @Slot(result=bool)
    def generateAll(self): return self._start_generation(None)

    @Slot()
    def cancelGeneration(self):
        if self._cancellation is not None:self._cancellation.cancel()

    @Slot(result=bool)
    def rebuildMix(self):
        try:self.service.build_final_mix_for_project(self._project_id);self.refresh();self.operationSucceeded.emit("Dub audio mix rebuilt");return True
        except Exception as exc:self._fail(exc);return False

    @Slot(bool,result=bool)
    def createSubtitles(self,bilingual=False):
        if self.apply_service is None:return False
        try:self.apply_service.create_subtitles(self._project_id,bilingual=bool(bilingual));self.refresh();self.operationSucceeded.emit("Dub subtitles created");return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str)
    def requestPreview(self, mode): self.previewRequested.emit(mode)
    @Slot(str)
    def openModule(self, mode): self.navigationRequested.emit(mode)

    def _start_generation(self,selected_ids):
        if self._busy:return False
        token=CancellationToken(); worker=DubbingWorker(self.service,self._project_id,selected_ids=selected_ids,cancellation=token,progress_callback=self._progress)
        if self.worker_pool is None:
            try:worker.run();self.refresh();self.operationSucceeded.emit("Dub audio generated");return True
            except Exception as exc:self._fail(exc);return False
        self._busy=True;self._cancellation=token;self.busyChanged.emit()
        self._future=self.worker_pool.submit(worker.run)
        def done(future):
            try:future.result();self.generationFinished.emit(True,"")
            except Exception as exc:self.generationFinished.emit(False,str(exc))
        self._future.add_done_callback(done);return True

    @Slot(bool,str)
    def _generation_done(self,ok,message):
        self._busy=False;self._cancellation=None;self._future=None;self.busyChanged.emit();self.refresh()
        if ok:self.operationSucceeded.emit("Dub audio generated")
        elif "cancel" in message.lower():self.operationSucceeded.emit("Dub generation cancelled")
        else:self.operationFailed.emit(message or "Dub generation failed")

    def _progress(self,index,total,segment_id):self.generationProgress.emit(index,total,segment_id)
    def _emit_all(self):self.contextChanged.emit();self.segmentsChanged.emit();self.mixChanged.emit();self.readinessChanged.emit();self.optionsChanged.emit()
    def _fail(self,exc):self.logger.exception("Dubbing action failed");self.operationFailed.emit(getattr(exc,"user_message",None) or str(exc) or "Dubbing action could not be completed.")

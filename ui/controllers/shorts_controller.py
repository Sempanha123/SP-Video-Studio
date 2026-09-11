from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot


class ShortsController(QObject):
    changed=Signal(); selectionChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str); shortProjectCreated=Signal(str)

    def __init__(self, shorts_service, candidate_service, caption_service, reframe_service, repository, media_repository,
                 transcript_repository, scene_repository, project_repository, language_service=None, logger=None, parent=None) -> None:
        super().__init__(parent); self.shorts=shorts_service; self.candidates_service=candidate_service; self.captions=caption_service
        self.reframe=reframe_service; self.repository=repository; self.media=media_repository; self.transcripts=transcript_repository
        self.scenes=scene_repository; self.projects=project_repository; self.languages=language_service
        self.logger=logger or logging.getLogger("sp_video_studio.shorts_controller")
        self._project_id=""; self._settings={}; self._candidates=[]; self._media=[]; self._transcripts=[]; self._scenes=[]; self._selected=""; self._readiness={}; self._workflow=""

    @Property(str,notify=changed)
    def currentProjectId(self): return self._project_id
    @Property(str,notify=changed)
    def workflow(self): return self._workflow
    @Property('QVariantMap',notify=changed)
    def settings(self): return dict(self._settings)
    @Property('QVariantList',notify=changed)
    def candidates(self): return list(self._candidates)
    @Property('QVariantList',notify=changed)
    def mediaOptions(self): return list(self._media)
    @Property('QVariantList',notify=changed)
    def transcriptOptions(self): return list(self._transcripts)
    @Property('QVariantList',notify=changed)
    def sceneOptions(self): return list(self._scenes)
    @Property(str,notify=selectionChanged)
    def selectedCandidateId(self): return self._selected
    @Property('QVariantMap',notify=selectionChanged)
    def selectedCandidate(self):
        return next((dict(x) for x in self._candidates if str(x.get("id",""))==self._selected),{})
    @Property('QVariantMap',notify=selectionChanged)
    def readiness(self): return dict(self._readiness)
    @Property('QVariantList',notify=changed)
    def languageOptions(self):
        if self.languages is None:return []
        try:return self.languages.search("")
        except Exception:return []

    @Slot(str)
    def setCurrentProject(self,project_id:str):
        value=(project_id or "").strip()
        if value==self._project_id:return
        self._project_id=value; self._selected=""; self.refresh()

    @Slot()
    def refresh(self):
        if not self._project_id:
            self._settings={}; self._candidates=[]; self._media=[]; self._transcripts=[]; self._scenes=[]; self._workflow=""; self.changed.emit(); return
        try:
            project=self.projects.get_by_id(self._project_id); self._workflow=str(project.workflow) if project else ""
            meta=self.shorts.load_or_create(self._project_id); self._settings=meta.to_dict()
            self._candidates=[x.to_dict() for x in self.repository.list_candidates(self._project_id)]
            self._media=[{"id":x.id,"name":x.name,"durationMs":int(x.duration_ms or 0),"type":x.type,"thumbnail":x.thumbnail_path or ""} for x in self.media.list_by_project(self._project_id) if x.type=="video"]
            self._transcripts=[{"id":x.id,"mediaId":x.media_id,"language":x.detected_language or x.language_mode,"status":x.status_code,"label":f"{x.detected_language or x.language_mode} · {x.id[:8]}"} for x in self.transcripts.list_for_project(self._project_id) if x.status_code in {"ready","outdated"}]
            self._scenes=[{"id":x.id,"name":x.name,"durationMs":x.duration_ms,"order":x.order} for x in self.scenes.list_for_project(self._project_id)]
            if self._selected and not any(str(x.get("id"))==self._selected for x in self._candidates):self._selected=""
            self.changed.emit(); self.selectionChanged.emit()
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def selectCandidate(self,candidate_id:str):
        self._selected=str(candidate_id or ""); self._update_readiness(); self.selectionChanged.emit()

    @Slot(int,result=bool)
    def setIn(self,position_ms:int):
        return self._op(lambda:self.shorts.set_in(self._project_id,position_ms),"In point set")
    @Slot(int,result=bool)
    def setOut(self,position_ms:int):
        return self._op(lambda:self.shorts.set_out(self._project_id,position_ms),"Out point set")

    @Slot(str,str,result=bool)
    def createManual(self,media_id:str,title:str="Short"):
        return self._op(lambda:self.shorts.create_from_in_out(self._project_id,media_id,title=title),"Short candidate created",select_result=True)

    @Slot(str,'QVariantList',str,result=bool)
    def createFromTranscript(self,transcript_id:str,segment_ids,title:str="Transcript Short"):
        target=int(self._settings.get("targetDurationMs",30000) or 30000)
        return self._op(lambda:self.candidates_service.create_from_transcript(self._project_id,transcript_id,[str(x) for x in segment_ids],title=title,target_duration_ms=target),"Transcript Short created",select_result=True)

    @Slot('QVariantList',str,str,result=bool)
    def createFromScenes(self,scene_ids,title:str="Scene Short",source_type:str="scenes"):
        target=int(self._settings.get("targetDurationMs",30000) or 30000)
        language=str(self._settings.get("language","en") or "en")
        kind=str(source_type or "scenes")
        if kind in {"auto","scenes"} and self._workflow in {"news","story"}: kind=self._workflow
        if kind=="auto": kind="scenes"
        return self._op(lambda:self.candidates_service.create_from_scenes(self._project_id,[str(x) for x in scene_ids],title=title,target_duration_ms=target,source_type=kind,language=language),"Scene Short created",select_result=True)

    @Slot(str,'QVariantList',str,result=bool)
    def createMultiRange(self,media_id:str,ranges,title:str="Multi-range Short"):
        target=int(self._settings.get("targetDurationMs",30000) or 30000); language=str(self._settings.get("language","en") or "en")
        normalized=[dict(x) for x in ranges]
        return self._op(lambda:self.candidates_service.create_multi_range(self._project_id,media_id,normalized,title=title,language=language,target_duration_ms=target),"Multi-range Short created",select_result=True)

    @Slot(str,result=bool)
    def suggestFromTranscript(self,transcript_id:str):
        target=int(self._settings.get("targetDurationMs",30000) or 30000)
        return self._op(lambda:self.candidates_service.suggest_from_transcript(self._project_id,transcript_id,target),"Deterministic suggestions created")

    @Slot(str,result=bool)
    def duplicateCandidate(self,candidate_id:str):
        return self._op(lambda:self.shorts.duplicate_candidate(self._project_id,candidate_id),"Candidate duplicated",select_result=True)

    @Slot(str,result=bool)
    def deleteCandidate(self,candidate_id:str):
        return self._op(lambda:self.repository.delete_candidate(self._project_id,candidate_id),"Candidate deleted")

    @Slot(str,str,str,result=bool)
    def editCandidate(self,candidate_id:str,title:str,hook:str):
        return self._op(lambda:self.shorts.update_candidate(self._project_id,candidate_id,title=title,hook=hook),"Candidate updated")

    @Slot(str,result=bool)
    def createEditableShort(self,candidate_id:str):
        try:
            duplicate,target=self.shorts.approve_to_project(candidate_id)
            self.operationSucceeded.emit("Independent Short project created")
            self.shortProjectCreated.emit(duplicate.id)
            self.refresh(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(str,float,result=bool)
    def applyReframePreset(self,scene_id:str,preset:str,scale:float=1.0):
        return self._op(lambda:self.reframe.apply_preset(self._project_id,scene_id,preset,scale=scale),"Reframe updated")

    @Slot(str,str,int,result=bool)
    def createCaptions(self,candidate_id:str,preset_id:str="creator",max_words:int=4):
        if self._workflow!="shorts": return self._reject("Create the independent Short project before adding Short captions.")
        return self._op(lambda:self.captions.create_track(self._project_id,candidate_id,preset_id=preset_id,max_words=max_words),"Short captions created")

    @Slot(int,str,str,str,str,result=bool)
    def updateSettings(self,target_duration_ms:int,aspect_ratio:str,language:str,platform:str,style:str):
        return self._op(lambda:self.shorts.update_settings(self._project_id,target_duration_ms=target_duration_ms,aspect_ratio=aspect_ratio,language=language,platform=platform,style=style),"Short settings updated")

    @Slot(result=str)
    def recommendedExportPreset(self):
        try:return self.shorts.recommended_export_preset(self._project_id)
        except Exception:return "generic_vertical"

    @Slot(str,result='QVariantList')
    def silenceSuggestions(self,transcript_id:str):
        try:return self.candidates_service.silence_suggestions(transcript_id)
        except Exception as exc:self._fail(exc); return []

    @Slot(int,int,result=bool)
    def applySilenceRemoval(self,start_ms:int,end_ms:int):
        return self._op(lambda:self.shorts.apply_silence_removal(self._project_id,start_ms,end_ms),"Silence range removed")

    @Slot(str,result='QVariantList')
    def transcriptSegments(self,transcript_id:str):
        try:
            return [{"id":x.id,"startMs":x.start_ms,"endMs":x.end_ms,"text":x.text} for x in self.transcripts.segments(transcript_id)]
        except Exception as exc:self._fail(exc); return []

    def _update_readiness(self):
        if not self._selected:self._readiness={}; return
        try:self._readiness=self.shorts.readiness(self._project_id,self._selected)
        except Exception:self._readiness={}

    def _op(self,fn,message:str,*,select_result:bool=False):
        try:
            result=fn()
            if select_result and hasattr(result,"id"):self._selected=str(result.id)
            self.refresh(); self._update_readiness(); self.operationSucceeded.emit(message); return True
        except Exception as exc:self._fail(exc); return False

    def _reject(self,message:str):self.operationFailed.emit(message); return False
    def _fail(self,exc:Exception):
        self.logger.exception("Shorts action failed",exc_info=exc); self.operationFailed.emit(str(exc).strip() or getattr(exc,"user_message","Shorts Maker could not complete that action."))

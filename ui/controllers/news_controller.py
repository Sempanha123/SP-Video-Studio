from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from services.news_brief_service import NewsBriefService
from services.news_claim_service import NewsClaimService
from services.news_errors import NewsError
from services.news_script_service import NewsScriptService
from services.news_service import NewsService
from services.news_source_service import NewsSourceService
from services.news_validation_service import NewsValidationService
from workers.worker_pool import WorkerPool


class NewsController(QObject):
    contextChanged = Signal()
    sourcesChanged = Signal()
    claimsChanged = Signal()
    briefChanged = Signal()
    groundingChanged = Signal()
    busyChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    navigationRequested = Signal(str)
    _jobFinished = Signal(str, object, object)

    def __init__(self, service: NewsService, sources: NewsSourceService, claims: NewsClaimService,
                 briefs: NewsBriefService, scripts: NewsScriptService, validation: NewsValidationService,
                 workers: WorkerPool, logger=None, parent=None) -> None:
        super().__init__(parent)
        self.service=service; self.sources_service=sources; self.claims_service=claims
        self.briefs_service=briefs; self.scripts_service=scripts; self.validation=validation
        self.workers=workers; self.logger=logger or logging.getLogger("sp_video_studio.news_controller")
        self._project_id=""; self._project={}; self._overview={}; self._sources=[]; self._claims=[]
        self._briefs=[]; self._source={}; self._snapshot={}; self._grounding={}; self._busy=False
        self._jobFinished.connect(self._on_job_finished)

    @Property(str, notify=contextChanged)
    def currentProjectId(self): return self._project_id
    @Property('QVariantMap', notify=contextChanged)
    def project(self): return self._project
    @Property('QVariantMap', notify=contextChanged)
    def overview(self): return self._overview
    @Property('QVariantList', notify=sourcesChanged)
    def sources(self): return self._sources
    @Property('QVariantList', notify=claimsChanged)
    def claims(self): return self._claims
    @Property('QVariantList', notify=briefChanged)
    def briefs(self): return self._briefs
    @Property('QVariantMap', notify=sourcesChanged)
    def currentSource(self): return self._source
    @Property('QVariantMap', notify=sourcesChanged)
    def currentSnapshot(self): return self._snapshot
    @Property('QVariantMap', notify=groundingChanged)
    def grounding(self): return self._grounding
    @Property(bool, notify=busyChanged)
    def busy(self): return self._busy

    @Slot(str)
    def setCurrentProject(self, project_id:str):
        value=(project_id or "").strip()
        if value==self._project_id: return
        self._project_id=value; self._source={}; self._snapshot={}; self._grounding={}
        self.refresh()

    @Slot()
    def refresh(self):
        if not self._project_id:
            self._project={}; self._overview={}; self._sources=[]; self._claims=[]; self._briefs=[]
            self.contextChanged.emit(); self.sourcesChanged.emit(); self.claimsChanged.emit(); self.briefChanged.emit(); return
        try:
            meta=self.service.load_or_create(self._project_id); self._project=meta.to_dict(); self._overview=self.service.overview(self._project_id)
            self._sources=[self._source_row(s) for s in self.service.repository.list_sources(self._project_id)]
            self._claims=[self._claim_row(c) for c in self.service.repository.list_claims(self._project_id)]
            self._briefs=[{**b.to_dict(),"itemCount":len(self.service.repository.brief_items(b.id))} for b in self.service.repository.list_briefs(self._project_id)]
            self.contextChanged.emit(); self.sourcesChanged.emit(); self.claimsChanged.emit(); self.briefChanged.emit()
        except Exception as exc: self._fail(exc)

    @Slot(str,str,str,str,int,str,result=bool)
    def updateSetup(self,topic,angle,language,platform,duration_ms,region=""):
        try:
            self.service.update_setup(self._project_id,topic=topic,angle=angle,language=language,platform=platform,target_duration_ms=int(duration_ms),region=region)
            self.refresh(); self.operationSucceeded.emit("News setup saved"); return True
        except Exception as exc: self._fail(exc); return False

    @Slot(str,str,str,str,str,str,result=bool)
    def addManualSource(self,title,text,publisher="",published_at="",language="auto",category="manual_note"):
        try:
            item=self.sources_service.add_manual(self._project_id,title,text,publisher=publisher,published_at=published_at or None,language=language,category=category)
            self.selectSource(item.id); self.refresh(); self.operationSucceeded.emit("Source added"); return True
        except Exception as exc: self._fail(exc); return False

    @Slot(str,str,str,str,result=bool)
    def addUrlSource(self,url,title="",language="auto",category="reporting"):
        if self._busy: return False
        try:
            item=self.sources_service.add_url(self._project_id,url,title=title,language=language,category=category,fetch=False)
            self._run("refresh", self.sources_service.refresh, self._project_id, item.id); return True
        except Exception as exc: self._fail(exc); return False

    @Slot(str,str,str,str,result=bool)
    def addLocalSource(self,path,title="",language="auto",category="primary_document"):
        try:
            local=self._local_path(path); item=self.sources_service.add_local(self._project_id,local,title=title,language=language,category=category)
            self.selectSource(item.id); self.refresh(); self.operationSucceeded.emit("Local source copied into the project"); return True
        except Exception as exc: self._fail(exc); return False

    @Slot(str)
    def selectSource(self,source_id):
        source=self.service.repository.source(self._project_id,source_id)
        snap=self.service.repository.latest_snapshot(self._project_id,source_id) if source else None
        self._source=self._source_row(source) if source else {}; self._snapshot=snap.to_dict() if snap else {}
        if snap: self._snapshot["contentText"]=snap.content_text
        self.sourcesChanged.emit()

    @Slot(str,result=bool)
    def refreshSource(self,source_id):
        if self._busy:return False
        try:self._run("refresh",self.sources_service.refresh,self._project_id,source_id); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(str,str,result=bool)
    def updateManualSourceText(self,source_id,text):
        try:self.sources_service.update_manual_text(self._project_id,source_id,text);self.selectSource(source_id);self.refresh();self.operationSucceeded.emit("Manual source version saved");return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,str,result=bool)
    def updateSourceDetails(self,source_id,category,notes):
        try:self.sources_service.update_details(self._project_id,source_id,category=category,notes=notes);self.selectSource(source_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def refreshAllSources(self):
        if self._busy:return False
        try:self._run("refresh_all",self.sources_service.refresh_all,self._project_id);return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def removeSource(self,source_id):
        try:self.sources_service.remove(self._project_id,source_id); self._source={};self._snapshot={};self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def extractClaims(self,source_id):
        if self._busy:return False
        try:self._run("extract",self.claims_service.extract_candidates,self._project_id,source_id);return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,str,str,int,int,result=bool)
    def createClaim(self,source_id,snapshot_id,evidence_text,claim_text,start_offset=-1,end_offset=-1):
        try:
            self.claims_service.create_manual(self._project_id,claim_text,source_id=source_id or None,snapshot_id=snapshot_id or None,evidence_text=evidence_text,start_offset=int(start_offset),end_offset=int(end_offset))
            self.refresh(); return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,result=bool)
    def approveClaim(self,claim_id,override_note=""):
        try:self.claims_service.approve(self._project_id,claim_id,override_note=override_note);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def rejectClaim(self,claim_id):
        try:self.claims_service.reject(self._project_id,claim_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,bool,result=bool)
    def lockClaim(self,claim_id,locked):
        try:self.claims_service.set_locked(self._project_id,claim_id,locked);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def editClaim(self,claim_id,text):
        try:self.claims_service.edit(self._project_id,claim_id,text);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,str,result=bool)
    def resolveConflict(self,claim_a,claim_b,choice):
        try:self.claims_service.resolve_conflict(self._project_id,claim_a,claim_b,choice);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def mergeClaims(self,target_id,source_id):
        try:self.claims_service.merge(self._project_id,target_id,source_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def createBrief(self):
        try:self.briefs_service.create_from_approved(self._project_id);self.refresh();self.operationSucceeded.emit("News Brief created");return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def setBriefStatus(self,brief_id,status):
        try:self.briefs_service.set_status(self._project_id,brief_id,status);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def buildScript(self,brief_id=""):
        try:
            script,_,_=self.scripts_service.build_script(self._project_id,brief_id=brief_id or None)
            self._grounding=self.scripts_service.validate_grounding(self._project_id,script.id);self.groundingChanged.emit();self.refresh();self.operationSucceeded.emit("Source-grounded News script created");return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def validateScript(self):
        try:self._grounding=self.scripts_service.validate_grounding(self._project_id);self.groundingChanged.emit();self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def createScenes(self):
        try:self.scripts_service.create_scenes(self._project_id);self.operationSucceeded.emit("Scenes created from the grounded script");return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def createDirectorPlan(self):
        try:self.scripts_service.create_director_plan(self._project_id);self.operationSucceeded.emit("News production plan created");return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def createTranslation(self,target_language="km",engine_id="manual"):
        try:self.scripts_service.create_translation(self._project_id,target_language=target_language,engine_id=engine_id);self.operationSucceeded.emit("Translation workspace created");return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=str)
    def sourceListText(self):
        try:return self.sources_service.source_list_text(self._project_id)
        except Exception as exc:self._fail(exc);return ""
    @Slot(str,result=bool)
    def exportSources(self,path):
        try:self.sources_service.export_sources(self._project_id,self._local_path(path));self.operationSucceeded.emit("Source list exported");return True
        except Exception as exc:self._fail(exc);return False
    @Slot(result=bool)
    def copySourceList(self):
        try:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.clipboard().setText(self.sources_service.source_list_text(self._project_id)); self.operationSucceeded.emit("Source list copied"); return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def openSource(self,source_id):
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            source=self.service.repository.source(self._project_id,source_id)
            if source is None:return False
            target=QUrl(source.url) if source.type_code=="url" else QUrl.fromLocalFile(source.source_path)
            return bool(QDesktopServices.openUrl(target))
        except Exception as exc:self._fail(exc);return False
    @Slot(str)
    def navigate(self,mode): self.navigationRequested.emit(mode)

    def _source_row(self,s):
        if not s:return {}
        snap=self.service.repository.latest_snapshot(self._project_id,s.id); evidence_count=0
        for c in self.service.repository.list_claims(self._project_id): evidence_count += sum(e.source_id==s.id for e in self.service.repository.evidence_for_claim(c.id))
        return {**s.to_dict(),"snapshotHash":snap.content_hash if snap else "","snapshotId":snap.id if snap else "","evidenceCount":evidence_count}
    def _claim_row(self,c):
        evidence=self.service.repository.evidence_for_claim(c.id)
        sources={e.source_id for e in evidence}
        return {**c.to_dict(),"evidenceCount":len(evidence),"sourceCount":len(sources),"evidence":[e.to_dict() for e in evidence]}
    def _run(self,kind,fn,*args):
        self._busy=True;self.busyChanged.emit(); future=self.workers.submit(fn,*args)
        future.add_done_callback(lambda f:self._jobFinished.emit(kind, None if f.exception() else f.result(), f.exception()))
    @Slot(str,object,object)
    def _on_job_finished(self,kind,result,error):
        self._busy=False;self.busyChanged.emit()
        if error is not None:self._fail(error);return
        self.refresh(); self.operationSucceeded.emit("Sources refreshed" if kind in {"refresh","refresh_all"} else "Candidate claims extracted")
    def _local_path(self,value):
        text=str(value or "")
        if text.startswith("file:"):
            from PySide6.QtCore import QUrl
            return Path(QUrl(text).toLocalFile())
        return Path(text)
    def _fail(self,exc):
        self.logger.exception("News Studio action failed")
        message=getattr(exc,"user_message","") or str(exc) or "News Studio could not complete this action."
        self.operationFailed.emit(message)

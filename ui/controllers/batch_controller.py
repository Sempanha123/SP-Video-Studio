from __future__ import annotations

import logging
from pathlib import Path
try:
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
except ImportError:  # pragma: no cover - importable test fallback
    class QObject:
        def __init__(self,*a,**k): pass
    class Signal:
        def __init__(self,*a): pass
        def emit(self,*a): pass
    def Slot(*a,**k): return lambda f:f
    def Property(*a,**k): return property
    class QUrl:
        def __init__(self,s=""): self.s=s
        def toLocalFile(self): return self.s.removeprefix("file://")

from domain.batch_mapping import BatchMapping
from domain.batch_variant import BatchVariantConfig


def _path(value):
    text=str(value or "")
    return Path(QUrl(text).toLocalFile()) if text.startswith("file:") else Path(text)


class BatchController(QObject):
    batchesChanged=Signal(); batchChanged=Signal(); itemsChanged=Signal(); inputChanged=Signal(); dryRunChanged=Signal(); hasMoreItemsChanged=Signal()
    operationSucceeded=Signal(str); operationFailed=Signal(str); openProjectRequested=Signal(str)

    def __init__(self,service,imports,repository,item_repository,templates,scheduler,*,logger=None,parent=None):
        super().__init__(parent)
        self.service=service; self.imports=imports; self.repository=repository; self.item_repository=item_repository
        self.templates=templates; self.scheduler=scheduler; self.logger=logger or logging.getLogger("sp_video_studio.batch_controller")
        self._batch_id=""; self._rows=[]; self._dry={}; self._filter="all"; self._search=""; self._input_search=""; self._item_limit=240; self._item_page=240; self._has_more=False; self._items_cache=[]

    @Property("QVariantList",notify=batchesChanged)
    def batches(self): return self.service.history()

    @Property("QVariantList",constant=True)
    def templateChoices(self):
        try:
            return [{"id":x.id,"name":x.name,"category":x.category,"workflow":x.workflow,"version":x.version} for x in self.templates.list_templates(sort="recommended")]
        except Exception:
            return []

    @Property("QVariantMap",notify=batchChanged)
    def currentBatch(self):
        batch=self.repository.get(self._batch_id) if self._batch_id else None
        if batch is None:return {}
        data=batch.to_dict(); summary=self.item_repository.summary_for_batch(batch.id) if hasattr(self.item_repository,"summary_for_batch") else None
        if summary is None:
            rows=self.item_repository.list_for_batch(batch.id); counts={key:0 for key in ("running","pending","completed","failed","skipped","cancelled")}; active={"validating","project_setup","translation","tts","subtitles","scene_setup","rendering","exporting"}
            for item in rows:
                status=item.status_code
                if status in active:counts["running"]+=1
                elif status in {"failed","interrupted","output_missing","needs_review"}:counts["failed"]+=1
                elif status in counts:counts[status]+=1
            summary={"counts":counts,"overallProgress":(sum(float(x.progress) for x in rows)/len(rows)) if rows else 0.0}
        data["statusCounts"]=summary["counts"]; data["overallProgress"]=summary["overallProgress"]
        try:data["pauseReason"]=self.repository.pause_reason(batch.id)
        except Exception:data["pauseReason"]=""
        return data

    @Property("QVariantList",notify=itemsChanged)
    def items(self):
        if not self._batch_id:return []
        rows=self.item_repository.list_for_batch(self._batch_id,status=self._filter,search=self._search,limit=self._item_limit+1)
        self._has_more=len(rows)>self._item_limit;self._items_cache=[x.to_dict() for x in rows[:self._item_limit]]
        return self._items_cache
    @Property(bool,notify=hasMoreItemsChanged)
    def hasMoreItems(self):return bool(self._has_more)
    @Slot()
    def loadMoreItems(self):
        if not self._has_more:return
        self._item_limit+=self._item_page;self.itemsChanged.emit();self.hasMoreItemsChanged.emit()

    @Property("QVariantList",notify=inputChanged)
    def inputRows(self):
        query=self._input_search.casefold().strip(); result=[]
        for row in self._rows:
            data=row.to_dict() if hasattr(row,"to_dict") else dict(row)
            if query and query not in str(data.get("data",{})).casefold():continue
            result.append(data)
        return result

    @Property("QVariantMap",notify=dryRunChanged)
    def dryRunSummary(self): return dict(self._dry)

    @Slot()
    def refresh(self):
        self.batchesChanged.emit(); self.batchChanged.emit(); self.itemsChanged.emit()

    @Slot(str)
    def openBatch(self,bid):
        self._batch_id=str(bid or ""); self._item_limit=self._item_page; self.batchChanged.emit(); self.itemsChanged.emit()

    @Slot(str,result=bool)
    def importInput(self,url):
        try:
            self._rows=self.imports.import_path(_path(url)); self._input_search=""; self.inputChanged.emit(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot("QVariantList")
    def setManualRows(self,rows):
        try:self._rows=self.imports.manual_rows([dict(x) for x in rows]); self.inputChanged.emit()
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def setInputSearch(self,text): self._input_search=str(text or ""); self.inputChanged.emit()

    @Slot(int,bool)
    def setRowSelected(self,row_index,selected):
        try:
            row=next(x for x in self._rows if int(x.row_index)==int(row_index)); row.selected=bool(selected); self.inputChanged.emit()
        except Exception:pass

    @Slot(str,result="QVariantList")
    def suggestMappings(self,template_id):
        try:
            tpl=self.templates.get(str(template_id)); keys=set()
            for row in self._rows[:20]: keys.update(str(k) for k in row.data)
            by_fold={k.casefold():k for k in keys}; result=[]
            for ph in tpl.placeholders:
                source=by_fold.get(ph.id.casefold(),"")
                if source:result.append({"target":ph.id,"kind":"column","source":source,"required":bool(ph.required)})
                elif ph.default_value not in ("",None):result.append({"target":ph.id,"kind":"default","defaultValue":ph.default_value,"required":bool(ph.required)})
            for field in ("language","source_language","voice","output_name","script","headline","body"):
                source=by_fold.get(field.casefold())
                if source and not any(x["target"]==field for x in result):result.append({"target":field,"kind":"column","source":source})
            return result
        except Exception as exc:self._fail(exc); return []

    @Slot(str,str,str,"QVariantList","QVariantMap","QVariantMap",result=str)
    def createBatch(self,name,template_id,output_dir,mappings,variants,settings):
        try:
            tpl=self.templates.get(template_id); maps=[]
            for raw in mappings:
                raw=dict(raw); maps.append(BatchMapping("",str(raw.get("target") or ""),str(raw.get("kind") or "column"),str(raw.get("source") or ""),raw.get("value",""),bool(raw.get("required",False)),raw.get("defaultValue",""),list(raw.get("transforms") or []),dict(raw.get("metadata") or {})))
            v=dict(variants or {}); config=BatchVariantConfig("",list(v.get("languages") or []),list(v.get("voices") or []),list(v.get("platforms") or []),list(v.get("aspectRatios") or []),list(v.get("templateOptions") or []),str(v.get("sourceLanguage") or ""),int(v.get("seed") or 0),dict(v.get("metadata") or {}))
            rows=[dict(x.data) for x in self._rows if bool(getattr(x,"selected",True))]
            if not rows:raise ValueError("Select at least one input row.")
            batch=self.service.create_batch(name,tpl,rows,maps,config,_path(output_dir),settings=dict(settings or {})); self._batch_id=batch.id
            self.batchesChanged.emit(); self.batchChanged.emit(); self.operationSucceeded.emit("Batch created. Validate it before running."); return batch.id
        except Exception as exc:self._fail(exc); return ""

    @Slot(result="QVariantMap")
    def validateBatch(self):
        try:self._dry=self.service.dry_run(self._batch_id).to_dict(); self.dryRunChanged.emit(); return self._dry
        except Exception as exc:self._fail(exc); return {}

    @Slot(bool,result=int)
    def prepareQueue(self,skip_invalid=False):
        try:
            rows=self.service.prepare_items(self._batch_id,skip_invalid=bool(skip_invalid)); self.itemsChanged.emit(); self.batchChanged.emit(); return len(rows)
        except Exception as exc:self._fail(exc); return 0

    @Slot(result=bool)
    def runBatch(self):
        try:self.scheduler.start(self._batch_id); self.operationSucceeded.emit("Batch started."); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(result=bool)
    def pauseBatch(self):
        try:self.scheduler.pause(self._batch_id); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(result=bool)
    def resumeBatch(self):
        try:self.scheduler.resume(self._batch_id); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(bool,result=bool)
    def cancelBatch(self,include_current=False):
        try:self.scheduler.cancel(self._batch_id,include_current=bool(include_current)); self.refresh(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(str,result=bool)
    def retryItem(self,item_id):
        try:self.service.retry_item(item_id); self.itemsChanged.emit(); self.batchChanged.emit(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(str,result=bool)
    def skipItem(self,item_id):
        try:self.service.skip_item(item_id); self.itemsChanged.emit(); self.batchChanged.emit(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(result=int)
    def retryAllFailed(self):
        try:n=self.service.retry_all_failed(self._batch_id); self.itemsChanged.emit(); self.batchChanged.emit(); return n
        except Exception as exc:self._fail(exc); return 0

    @Slot(str,str)
    def setQueueFilter(self,status,search=""):
        self._filter=str(status or "all"); self._search=str(search or ""); self._item_limit=self._item_page; self.itemsChanged.emit(); self.hasMoreItemsChanged.emit()

    @Slot(str)
    def openGeneratedProject(self,item_id):
        item=self.item_repository.get(item_id)
        if item and item.project_id:
            self.service.mark_manually_modified(item_id,True); self.openProjectRequested.emit(item.project_id)

    @Slot(str,result=bool)
    def exportResults(self,url):
        try:self.service.export_results_csv(self._batch_id,_path(url)); self.operationSucceeded.emit("Batch results exported."); return True
        except Exception as exc:self._fail(exc); return False

    def _fail(self,exc):
        self.logger.exception("Batch action failed")
        self.operationFailed.emit(str(exc).strip() or getattr(exc,"user_message","Batch action could not be completed."))

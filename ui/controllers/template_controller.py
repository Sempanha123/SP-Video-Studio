from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from services.template_apply_service import TemplateApplyService
from services.template_service import TemplateService


def _path(value: str) -> Path:
    text=(value or "").strip()
    if text.startswith("file:"):
        local=QUrl(text).toLocalFile()
        return Path(local)
    return Path(text)


class TemplateController(QObject):
    templatesChanged=Signal(); selectedChanged=Signal(); filtersChanged=Signal(); operationSucceeded=Signal(str); operationFailed=Signal(str); projectCreated=Signal(str)

    def __init__(self,service:TemplateService,apply_service:TemplateApplyService,logger=None,parent=None):
        super().__init__(parent); self.service=service; self.apply=apply_service; self.logger=logger or logging.getLogger("sp_video_studio.template_controller")
        self._items=[]; self._selected={}; self._query=""; self._category="all"; self._sort="recommended"; self._current_project_id=""; self.refresh()

    @Property('QVariantList',notify=templatesChanged)
    def templates(self): return self._items
    @Property('QVariantMap',notify=selectedChanged)
    def selectedTemplate(self): return dict(self._selected)
    @Property('QVariantList',notify=filtersChanged)
    def categories(self): return ["All",*self.service.categories()]
    @Property(str,notify=filtersChanged)
    def query(self): return self._query
    @Property(str,notify=filtersChanged)
    def category(self): return self._category
    @Property(str,notify=filtersChanged)
    def sortMode(self): return self._sort
    @Property(str,notify=selectedChanged)
    def currentProjectId(self): return self._current_project_id

    @Slot()
    def refresh(self):
        try:
            self.service.refresh(); self._refresh_rows()
        except Exception as exc:self._fail(exc)

    @Slot(str)
    def setCurrentProject(self,project_id:str): self._current_project_id=(project_id or "").strip(); self.selectedChanged.emit()
    @Slot(str)
    def setQuery(self,value:str): self._query=value or ""; self.filtersChanged.emit(); self._refresh_rows()
    @Slot(str)
    def setCategory(self,value:str): self._category=(value or "all"); self.filtersChanged.emit(); self._refresh_rows()
    @Slot(str)
    def setSortMode(self,value:str): self._sort=(value or "recommended"); self.filtersChanged.emit(); self._refresh_rows()

    @Slot(str,result=bool)
    def selectTemplate(self,template_id:str):
        try:
            item=self.service.get(template_id); row=self.service.preview(item.id); row["components"]=[c.to_dict() for c in item.components]; row["placeholders"]=[p.to_dict() for p in item.placeholders]; row["compatibility"]={}
            self._selected=row; self.selectedChanged.emit(); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(str,str,str,str,'QVariantMap','QVariantList',result=str)
    def createProject(self,template_id:str,title:str,language:str,aspect_ratio:str,resolutions,components)->str:
        try:
            item=self.service.get(template_id); project,result=self.apply.create_project_from_template(item,title.strip() or item.name,language or "en",aspect_ratio or (item.supported_aspect_ratios[0] if item.supported_aspect_ratios else "16:9"),resolutions=dict(resolutions or {}),selected_components=list(components or [] ) or None,allow_unresolved=True)
            self.operationSucceeded.emit("Project created from template." if result.ready else "Project created. Template setup is incomplete."); self.projectCreated.emit(project.id); return project.id
        except Exception as exc:self._fail(exc); return ""

    @Slot(str,'QVariantMap','QVariantList',str,str,result=bool)
    def applyToCurrent(self,template_id:str,resolutions,components,mode:str,selected_scene_id:str)->bool:
        if not self._current_project_id:self.operationFailed.emit("Open a project before applying a template."); return False
        try:
            item=self.service.get(template_id); result=self.apply.apply_to_project(item,self._current_project_id,resolutions=dict(resolutions or {}),selected_components=list(components or []) or None,mode=mode or "merge",selected_scene_id=selected_scene_id or "",allow_unresolved=True)
            self.operationSucceeded.emit("Template applied." if result.ready else "Template applied. Some placeholders still need setup."); return True
        except Exception as exc:self._fail(exc); return False

    @Slot(str,'QVariantList',result='QVariantMap')
    def impact(self,template_id:str,components):
        try:return self.apply.impact_summary(self.service.get(template_id),list(components or []) or None)
        except Exception as exc:self._fail(exc); return {}

    @Slot(str,str,str,'QVariantList',bool,result=str)
    def saveCurrentAsTemplate(self,name:str,category:str,description:str,components,include_text:bool=False)->str:
        if not self._current_project_id:self.operationFailed.emit("Open a project before saving a template."); return ""
        try:
            selected=set(str(x) for x in (components or [])) or None; item=self.service.save_project_as_template(self._current_project_id,name,category,description,include_components=selected,include_text=bool(include_text)); self._refresh_rows(); self.operationSucceeded.emit("Template saved locally."); return item.id
        except Exception as exc:self._fail(exc); return ""

    @Slot(str,result=str)
    def duplicateTemplate(self,template_id:str)->str:
        try:item=self.service.duplicate(template_id); self._refresh_rows(); self.operationSucceeded.emit("Template duplicated."); return item.id
        except Exception as exc:self._fail(exc); return ""
    @Slot(str,str,result=bool)
    def renameTemplate(self,template_id:str,name:str)->bool:
        try:self.service.rename(template_id,name); self._refresh_rows(); self.operationSucceeded.emit("Template renamed."); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,result=bool)
    def deleteTemplate(self,template_id:str)->bool:
        try:self.service.delete(template_id); self._selected={}; self.selectedChanged.emit(); self._refresh_rows(); self.operationSucceeded.emit("Template deleted."); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,str,result=bool)
    def exportTemplate(self,template_id:str,destination:str)->bool:
        try:self.service.export_package(template_id,_path(destination)); self.operationSucceeded.emit("Template package exported."); return True
        except Exception as exc:self._fail(exc); return False
    @Slot(str,str,result=str)
    def importTemplate(self,package:str,conflict:str="keep_both")->str:
        try:item=self.service.import_package(_path(package),conflict=conflict or "keep_both"); self._refresh_rows(); self.operationSucceeded.emit("Template package imported."); return item.id
        except Exception as exc:self._fail(exc); return ""
    @Slot(str,str,str,result='QVariantMap')
    def compatibility(self,template_id:str,language:str,aspect_ratio:str):
        try:return self.apply.validation.compatibility(self.service.get(template_id),language=language or "en",aspect_ratio=aspect_ratio or "16:9")
        except Exception as exc:self._fail(exc); return {"state":"missing_features","issues":[]}

    def _refresh_rows(self):
        items=self.service.list_templates(query=self._query,category=self._category,sort=self._sort); self._items=[]
        for item in items:
            row=self.service.preview(item.id); usage=self.service.repository.usage(item.id); row.update({"lastUsedAt":usage.get("lastUsedAt",""),"useCount":usage.get("useCount",0)})
            self._items.append(row)
        self.templatesChanged.emit(); self.filtersChanged.emit()

    def _fail(self,exc:Exception):
        self.logger.exception("Template action failed")
        message=str(exc).strip() or getattr(exc,"user_message","Template action could not be completed.")
        self.operationFailed.emit(message)

from __future__ import annotations
import hashlib
import json
import logging
import shutil
from pathlib import Path

from domain.news_source import NewsSource, NewsSourceSnapshot, NewsSourceStatus, NewsSourceType
from domain.project import utc_now_iso
from services.news_errors import NewsInvalidSource, NewsSourceFetchError, NewsSourceParseError
from services.news_source_fetch_service import HtmlArticleExtractor, NewsSourceFetchService, PlainTextExtractor
from storage.repositories.news_repository import NewsRepository
from storage.repositories.project_repository import ProjectRepository


def content_hash(text:str)->str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class NewsSourceService:
    SUPPORTED_LOCAL={".txt",".md",".html",".htm"}
    def __init__(self,repository:NewsRepository,project_repository:ProjectRepository,fetcher:NewsSourceFetchService|None=None,logger=None)->None:
        self.repository=repository; self.project_repository=project_repository; self.fetcher=fetcher or NewsSourceFetchService(); self.logger=logger or logging.getLogger("sp_video_studio.news_sources")
    def add_manual(self,project_id:str,title:str,text:str,*,publisher:str="",published_at:str|None=None,url:str="",language:str="auto",category:str="manual_note",notes:str="")->NewsSource:
        self._project(project_id)
        if not text.strip(): raise NewsInvalidSource("Paste source text before adding the source.")
        source=NewsSource(project_id,NewsSourceType.MANUAL,title.strip() or "Manual Source",url=url.strip(),publisher=publisher.strip(),published_at=published_at,accessed_at=utc_now_iso(),language=language,status=NewsSourceStatus.READY,category=category,notes=notes)
        self.repository.create_source(source); self._snapshot(source,text,source.title,"",published_at,{"origin":"manual"}); self.logger.info("News source added: %s manual",source.id); return source
    def update_manual_text(self,project_id:str,source_id:str,text:str)->NewsSourceSnapshot:
        source=self._owned(project_id,source_id)
        if source.type_code!="manual": raise NewsInvalidSource("Fetched source snapshots are immutable. Create a manual source instead.")
        if not text.strip(): raise NewsInvalidSource("Manual source text cannot be empty.")
        return self._snapshot(source,text,source.title,source.author,source.published_at,{"origin":"manual_edit"})
    def add_local(self,project_id:str,path:Path,*,title:str="",language:str="auto",category:str="primary_document",notes:str="")->NewsSource:
        project=self._project(project_id); source_path=Path(path)
        if not source_path.is_file() or source_path.suffix.lower() not in self.SUPPORTED_LOCAL:
            raise NewsInvalidSource("Choose a TXT, Markdown, or HTML source document.")
        try:
            raw=source_path.read_bytes()
            if len(raw)>10*1024*1024: raise NewsInvalidSource("Local source document is larger than the allowed limit.")
            if source_path.suffix.lower() in {".html",".htm"}:
                extracted=HtmlArticleExtractor().extract(raw,content_type="text/html",charset="utf-8",url=source_path.resolve().as_uri())
                text=extracted.content_text; resolved_title=title.strip() or extracted.title or source_path.stem
            else:
                extracted=PlainTextExtractor().extract(raw,content_type="text/plain",charset="utf-8",url=source_path.resolve().as_uri())
                text=extracted.content_text; resolved_title=title.strip() or source_path.stem
        except UnicodeDecodeError as exc: raise NewsSourceParseError("Local text source must be readable Unicode text.") from exc
        managed=Path(project.project_path)/"sources"; managed.mkdir(parents=True,exist_ok=True)
        target=managed/source_path.name
        if target.exists(): target=managed/f"{source_path.stem}_{content_hash(str(source_path))[:8]}{source_path.suffix}"
        shutil.copy2(source_path,target)
        source=NewsSource(project_id,NewsSourceType.LOCAL,resolved_title,language=language,status=NewsSourceStatus.READY,source_path=str(target),category=category,notes=notes,accessed_at=utc_now_iso(),metadata={"original_path":str(source_path)})
        self.repository.create_source(source); self._snapshot(source,text,resolved_title,"",None,{"origin":"local","managed_copy":True}); self.logger.info("News source added: %s local",source.id); return source
    def add_url(self,project_id:str,url:str,*,title:str="",language:str="auto",category:str="reporting",notes:str="",fetch:bool=True)->NewsSource:
        self._project(project_id); self.fetcher.validate_url(url)
        source=NewsSource(project_id,NewsSourceType.URL,title.strip(),url=url.strip(),language=language,status=NewsSourceStatus.PENDING,category=category,notes=notes)
        self.repository.create_source(source)
        if fetch: self.refresh(project_id,source.id)
        return self._owned(project_id,source.id)
    def refresh(self,project_id:str,source_id:str)->NewsSourceSnapshot:
        source=self._owned(project_id,source_id)
        if source.type_code!="url": raise NewsInvalidSource("Only web sources can be refreshed from the network.")
        source.status=NewsSourceStatus.FETCHING; self.repository.update_source(source)
        try: result=self.fetcher.fetch(source.url)
        except Exception:
            source.status=NewsSourceStatus.FAILED; self.repository.update_source(source); raise
        previous=self.repository.latest_snapshot(project_id,source_id)
        source.title=source.title or result.title or source.url; source.publisher=source.publisher or result.publisher; source.author=result.author or source.author
        source.published_at=result.published_at or source.published_at; source.accessed_at=utc_now_iso(); source.status=NewsSourceStatus.READY
        new_hash=content_hash(result.content_text); source.source_updated=bool(previous and previous.content_hash!=new_hash)
        snap=self._snapshot(source,result.content_text,result.title or source.title,result.author,result.published_at,{"content_type":result.content_type,"charset":result.charset,"resolved_url":result.url})
        self.logger.info("News source refreshed: %s changed=%s",source.id,source.source_updated); return snap
    def refresh_all(self,project_id:str)->list[NewsSourceSnapshot]:
        out=[]
        for source in self.repository.list_sources(project_id):
            if source.type_code=="url": out.append(self.refresh(project_id,source.id))
        return out
    def remove(self,project_id:str,source_id:str)->None:
        source=self._owned(project_id,source_id); self.repository.mark_source_removed(project_id,source_id); self.logger.info("News source removed: %s",source.id)
    def update_details(self,project_id:str,source_id:str,*,category:str|None=None,notes:str|None=None,title:str|None=None,publisher:str|None=None)->NewsSource:
        source=self._owned(project_id,source_id)
        if category is not None: source.category=category.strip() or "other"
        if notes is not None: source.notes=notes
        if title is not None: source.title=title.strip()
        if publisher is not None: source.publisher=publisher.strip()
        return self.repository.update_source(source)
    def search(self,project_id:str,query:str)->list[NewsSource]:
        q=(query or "").strip().casefold(); items=self.repository.list_sources(project_id)
        if not q:return items
        out=[]
        for s in items:
            snap=self.repository.latest_snapshot(project_id,s.id); hay=" ".join((s.title,s.publisher,s.notes,snap.content_text if snap else "")).casefold()
            if q in hay:out.append(s)
        return out
    def export_sources(self,project_id:str,path:Path,*,include_content:bool=False)->Path:
        self._project(project_id); target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
        data=[]
        for s in self.repository.list_sources(project_id):
            item=s.to_dict(); snap=self.repository.latest_snapshot(project_id,s.id)
            if snap:
                item["snapshot"]={"id":snap.id,"contentHash":snap.content_hash,"retrievedAt":snap.retrieved_at}
                if include_content:item["snapshot"]["contentText"]=snap.content_text
            data.append(item)
        target.write_text(json.dumps({"schemaVersion":1,"sources":data},ensure_ascii=False,indent=2),encoding="utf-8"); return target
    def source_list_text(self,project_id:str)->str:
        lines=["Sources",""]
        for i,s in enumerate(self.repository.list_sources(project_id),1):
            lines += [f"{i}. {s.title or 'Untitled Source'}",f"   {s.publisher}" if s.publisher else "",f"   Published: {s.published_at}" if s.published_at else "",f"   Accessed: {s.accessed_at}" if s.accessed_at else "",f"   URL: {s.url}" if s.url else "",""]
        return "\n".join(x for x in lines if x is not None).rstrip()+"\n"
    def _snapshot(self,source:NewsSource,text:str,title:str,author:str,published_at:str|None,metadata:dict[str,object])->NewsSourceSnapshot:
        snap=NewsSourceSnapshot(source.id,text,content_hash(text),title=title,author=author,published_at=published_at,metadata=metadata)
        previous=self.repository.latest_snapshot(source.project_id,source.id)
        source.source_updated=bool(previous and previous.content_hash!=snap.content_hash); source.status=NewsSourceStatus.READY; source.accessed_at=utc_now_iso()
        self.repository.create_snapshot(snap,source); return snap
    def _owned(self,project_id:str,source_id:str)->NewsSource:
        source=self.repository.source(project_id,source_id)
        if source is None: raise NewsInvalidSource("Source could not be found in this project.")
        return source
    def _project(self,project_id:str):
        project=self.project_repository.get_by_id(project_id)
        if project is None: raise NewsInvalidSource("Project could not be found.")
        return project

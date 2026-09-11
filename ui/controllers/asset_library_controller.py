from __future__ import annotations
import logging
from pathlib import Path
try:
    from PySide6.QtCore import QObject,Property,Signal,Slot,QUrl
except ImportError:  # test/import fallback
    class QObject:
        def __init__(self,*a,**k):pass
    class Signal:
        def __init__(self,*a):pass
        def emit(self,*a):pass
    def Slot(*a,**k):return lambda f:f
    def Property(*a,**k):return property
    class QUrl:
        def __init__(self,s=''):self.s=s
        def toLocalFile(self):return self.s.removeprefix('file://')

def _path(value):
    text=str(value or '');return Path(QUrl(text).toLocalFile()) if text.startswith('file:') else Path(text)

class AssetLibraryController(QObject):
    assetsChanged=Signal();selectedChanged=Signal();filtersChanged=Signal();collectionsChanged=Signal();hasMoreChanged=Signal();operationSucceeded=Signal(str);operationFailed=Signal(str);projectMediaAdded=Signal(str)
    def __init__(self,service,repository,usage,project_integration,*,importer,relink,logger=None,parent=None):
        super().__init__(parent);self.service=service;self.repository=repository;self.usage=usage;self.project_integration=project_integration;self.importer=importer;self.relink=relink;self.logger=logger or logging.getLogger('sp_video_studio.asset_controller');self._rows=[];self._selected={};self._query='';self._filter='all';self._sort='recent_added';self._collection='';self._project_id='';self._page_size=160;self._limit=self._page_size;self._has_more=False;self._refresh_rows()
    @Property('QVariantList',notify=assetsChanged)
    def assets(self):return self._rows
    @Property('QVariantMap',notify=selectedChanged)
    def selectedAsset(self):return dict(self._selected)
    @Property(bool,notify=hasMoreChanged)
    def hasMore(self):return bool(self._has_more)
    @Property('QVariantList',notify=collectionsChanged)
    def collections(self):return self.service.collections()
    @Property(str,notify=filtersChanged)
    def query(self):return self._query
    @Property(str,notify=filtersChanged)
    def filterMode(self):return self._filter
    @Property(str,notify=selectedChanged)
    def currentProjectId(self):return self._project_id
    @Property('QVariantMap',notify=assetsChanged)
    def storageUsage(self):return self.service.storage_usage()
    @Slot()
    def refresh(self):
        try:self.service.lightweight_startup_scan();self._refresh_rows()
        except Exception as exc:self._fail(exc)
    @Slot(str)
    def setCurrentProject(self,pid):self._project_id=str(pid or '');self.selectedChanged.emit()
    @Slot(str)
    def setQuery(self,v):self._query=str(v or '');self._reset_page();self.filtersChanged.emit();self._refresh_rows()
    @Slot(str)
    def setFilter(self,v):self._filter=str(v or 'all');self._reset_page();self.filtersChanged.emit();self._refresh_rows()
    @Slot(str)
    def setSort(self,v):self._sort=str(v or 'recent_added');self._reset_page();self.filtersChanged.emit();self._refresh_rows()
    @Slot(str)
    def setCollection(self,v):self._collection=str(v or '');self._reset_page();self.filtersChanged.emit();self._refresh_rows()
    @Slot(str,result=bool)
    def selectAsset(self,aid):
        try:self._selected=self.service.details(aid);self.selectedChanged.emit();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,bool,str,str,result=str)
    def importAsset(self,url,managed=True,subtype='general',duplicate_policy='use_existing'):
        try:a=self.importer.import_file(_path(url),managed=bool(managed),subtype=subtype or 'general',duplicate_policy=duplicate_policy or 'use_existing');self._refresh_rows();self.operationSucceeded.emit('Asset added to your reusable library.');return a.id
        except Exception as exc:self._fail(exc);return ''
    @Slot(str,result=str)
    def addToCurrentProject(self,aid):
        if not self._project_id:self.operationFailed.emit('Open a project before adding this asset.');return ''
        try:m=self.usage.add_to_project(self._project_id,aid,'other');self.projectMediaAdded.emit(m.id);self.operationSucceeded.emit('Reusable asset added to Project Media.');self._refresh_rows();return m.id
        except Exception as exc:self._fail(exc);return ''
    @Slot(str,int,str,result='QVariant')
    def addAtPlayhead(self,aid,position_ms=0,track='auto'):
        if not self._project_id:return ''
        try:return self.project_integration.add_at_playhead(self._project_id,aid,position_ms,track)
        except Exception as exc:self._fail(exc);return ''
    @Slot(str,str,str,str,result='QVariant')
    def addToScene(self,aid,scene_id,role='broll',speaker_id=''):
        if not self._project_id:return {}
        try:
            layer=self.project_integration.add_to_scene(self._project_id,scene_id,aid,role,speaker_id);return layer.to_dict() if hasattr(layer,'to_dict') else {'id':getattr(layer,'id','')}
        except Exception as exc:self._fail(exc);return {}
    @Slot(str,bool,result=bool)
    def setFavorite(self,aid,value):
        try:self.service.set_favorite(aid,value);self._refresh_rows();self.selectAsset(aid);return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,'QVariantList',result=bool)
    def setTags(self,aid,tags):
        try:self.service.set_tags(aid,list(tags or []));self.selectAsset(aid);self._refresh_rows();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=str)
    def createCollection(self,name,description=''):
        try:item=self.service.create_collection(name,description);self.collectionsChanged.emit();return item.id
        except Exception as exc:self._fail(exc);return ''
    @Slot(str,str,bool,result=bool)
    def setCollectionMembership(self,aid,cid,enabled):
        try:self.service.set_collection(aid,cid,enabled);self.collectionsChanged.emit();self.selectAsset(aid);return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,str,str,result=bool)
    def updateAsset(self,aid,name,subtype,notes):
        try:self.service.update(aid,name=name,subtype=subtype,notes=notes);self._refresh_rows();self.selectAsset(aid);return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,str,bool,str,result=bool)
    def setRights(self,aid,status,license_name,attribution_required,attribution_text):
        try:self.service.set_license(aid,rights_status=status or 'unknown',license_name=license_name,attribution_required=bool(attribution_required),attribution_text=attribution_text);self.selectAsset(aid);return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def removeAsset(self,aid,strategy='cancel'):
        try:self.service.delete_asset(aid,strategy=strategy or 'cancel');self._selected={};self.selectedChanged.emit();self._refresh_rows();self.operationSucceeded.emit('Asset removed from the reusable library.');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,bool,result=bool)
    def relinkAsset(self,aid,url,force=False):
        try:self.relink.relink(aid,_path(url),force=bool(force));self._refresh_rows();self.selectAsset(aid);self.operationSucceeded.emit('Asset relinked.');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result='QVariantList')
    def attributionSummary(self,project_id):
        try:return self.usage.attribution_summary(project_id)
        except Exception as exc:self._fail(exc);return []
    @Slot(str,str,result=bool)
    def migrateLibrary(self,path,mode='move'):
        try:self.service.migrate_library(_path(path),mode=mode or 'move');self._refresh_rows();self.operationSucceeded.emit('Asset Library location updated.');return True
        except Exception as exc:self._fail(exc);return False
    @Slot()
    def loadMore(self):
        if not self._has_more:return
        self._limit += self._page_size;self._refresh_rows()
    def _reset_page(self):
        self._limit=self._page_size
    def _refresh_rows(self):
        service=getattr(self.service,'search_service',None)
        if service is not None and hasattr(service,'search_rows'):
            records=service.search_rows(query=self._query,filter_id=self._filter,sort=self._sort,collection_id=self._collection,limit=self._limit+1)
        else:
            records=[{'asset':a,'tags':self.repository.tags(a.id),'usageCount':self.repository.usage_count(a.id),'collections':[]} for a in self.service.list_assets(query=self._query,filter_id=self._filter,sort=self._sort,collection_id=self._collection)[:self._limit+1]]
        self._has_more=len(records)>self._limit;records=records[:self._limit];self._rows=[]
        for meta in records:
            a=meta['asset'];row=a.to_dict();row.update({'tags':list(meta.get('tags') or []),'usageCount':int(meta.get('usageCount') or 0),'resolvedPath':str(a.resolved_path(self.repository.library_root)),'thumbnailResolved':str(a.resolved_thumbnail(self.repository.library_root) or '')});self._rows.append(row)
        self.assetsChanged.emit();self.hasMoreChanged.emit();self.collectionsChanged.emit()
    def _fail(self,exc):
        self.logger.exception('Asset Library action failed');self.operationFailed.emit(str(exc).strip() or getattr(exc,'user_message','Asset action could not be completed.'))

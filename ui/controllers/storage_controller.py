from __future__ import annotations
import logging
from pathlib import Path

try:
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtGui import QDesktopServices
except ImportError:  # pragma: no cover - headless tests
    class QObject:
        def __init__(self,*a,**k): pass
    class Signal:
        def __init__(self,*a,**k): pass
        def emit(self,*a,**k): pass
    def Slot(*a,**k): return lambda fn: fn
    def Property(*a,**k):
        def deco(fn): return property(fn)
        return deco
    class QUrl:
        def __init__(self,value=''): self.value=str(value)
        @classmethod
        def fromLocalFile(cls,value): return cls(value)
        def toLocalFile(self): return self.value.removeprefix('file://')
    class QDesktopServices:
        @staticmethod
        def openUrl(_url): return True

from domain.cleanup_policy import CleanupPolicy
from domain.storage_category import StorageCategory
from domain.storage_usage import readable_size


def _local_path(value: str) -> Path:
    text = str(value or "")
    if text.startswith("file:"):
        return Path(QUrl(text).toLocalFile())
    return Path(text)


class StorageController(QObject):
    storageChanged = Signal()
    scanStateChanged = Signal()
    cleanupPreviewChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    lowDiskWarning = Signal(str)
    criticalDisk = Signal(str)

    def __init__(self, usage, cleanup, cache, migration, disk_monitor, stale, *, worker_pool=None, logger=None, parent=None):
        super().__init__(parent)
        self.usage = usage; self.cleanup = cleanup; self.cache = cache; self.migration = migration; self.disk = disk_monitor; self.stale = stale
        self.worker_pool = worker_pool
        self.logger = logger or logging.getLogger("sp_video_studio.storage_controller")
        self._overview = {"totalOwnedBytes":0,"totalOwnedDisplay":"0 B","categories":[],"projects":[],"cacheBreakdown":[]}
        self._disk_status = []
        self._calculating = False
        self._cleanup_preview = {}
        self.refresh()

    @Property('QVariantMap', notify=storageChanged)
    def overview(self): return dict(self._overview)
    @Property('QVariantList', notify=storageChanged)
    def categories(self): return list(self._overview.get("categories") or [])
    @Property('QVariantList', notify=storageChanged)
    def projects(self): return list(self._overview.get("projects") or [])
    @Property('QVariantList', notify=storageChanged)
    def cacheBreakdown(self): return list(self._overview.get("cacheBreakdown") or [])
    @Property('QVariantList', notify=storageChanged)
    def diskStatus(self): return list(self._disk_status)
    @Property(bool, notify=scanStateChanged)
    def calculating(self): return self._calculating
    @Property('QVariantMap', notify=cleanupPreviewChanged)
    def cleanupPreview(self): return dict(self._cleanup_preview)
    @Property('QVariantMap', notify=storageChanged)
    def preferences(self):
        p=self.cache.preferences
        return {**p,"maximumCacheDisplay":"Unlimited" if int(p.get("maximumCacheBytes") or 0)<=0 else readable_size(int(p.get("maximumCacheBytes") or 0))}

    @Slot()
    def refresh(self):
        if self._calculating: return
        self._calculating=True; self.scanStateChanged.emit()
        if self.worker_pool is None:
            self._finish_refresh(self._scan_safe())
            return
        try:
            future=self.worker_pool.submit(self._scan_safe)
            future.add_done_callback(lambda f:self._finish_refresh(f.result() if not f.exception() else {"error":str(f.exception())}))
        except Exception:
            self._finish_refresh(self._scan_safe())

    @Slot()
    def recalculate(self):
        self.usage.invalidate(); self.refresh()

    def _scan_safe(self):
        try:
            overview=self.usage.recalculate(force=True)
            roots=[("Cache",self.cache.root),("Models",self.cache.paths.models),("Recovery",getattr(self.cache.paths,"recovery")),("Exports",getattr(self.cache.paths,"exports")),("Asset Library",getattr(self.cache.paths,"assets"))]
            disks=[x.to_dict() for x in self.disk.check_many(roots)]
            return {"overview":overview,"disks":disks}
        except Exception as exc:
            return {"error":str(exc)}

    def _finish_refresh(self, result):
        self._calculating=False; self.scanStateChanged.emit()
        if result.get("error"):
            self.operationFailed.emit(result["error"]); return
        self._overview=result.get("overview") or self._overview; self._disk_status=result.get("disks") or []
        self.storageChanged.emit()
        critical=[x for x in self._disk_status if x.get("state")=="critical"]
        low=[x for x in self._disk_status if x.get("state")=="low"]
        if critical:self.criticalDisk.emit("Storage is almost full. Free space before rendering.")
        elif low:self.lowDiskWarning.emit("Disk space is getting low.")

    @Slot('QVariantList', str, result='QVariantMap')
    def previewSelected(self, categories, project_id=''):
        try:
            selected=[StorageCategory(str(x)) for x in list(categories or [])]
            plan=self.cleanup.preview_cleanup(selected,project_id=str(project_id or ''),reason='ui_preview')
            self._cleanup_preview={**plan.to_dict(),"estimatedDisplay":readable_size(plan.estimated_bytes)};self.cleanupPreviewChanged.emit();return dict(self._cleanup_preview)
        except Exception as exc:self._fail(exc);return {}

    @Slot(result='QVariantMap')
    def previewAllCache(self):
        try:
            plan=self.cleanup.clear_all_cache(dry_run=True);self._cleanup_preview={**plan.to_dict(),"estimatedDisplay":readable_size(plan.estimated_bytes)};self.cleanupPreviewChanged.emit();return dict(self._cleanup_preview)
        except Exception as exc:self._fail(exc);return {}

    @Slot('QVariantList', str, result=bool)
    def clearSelected(self,categories,project_id=''):
        try:
            selected=[StorageCategory(str(x)) for x in list(categories or [])]
            result=self.cleanup.clear_categories(selected,project_id=str(project_id or ''))
            self._after_cleanup(result);return True
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def clearAllCache(self):
        try:result=self.cleanup.clear_all_cache();self._after_cleanup(result);return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def clearProjectCache(self,project_id):
        try:result=self.cleanup.clear_project_cache(str(project_id));self._after_cleanup(result);return True
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def clearOldLogs(self):
        try:
            days=int(self.cache.preferences.get('logRetentionDays') or 14);result=self.cleanup.cleanup_old_logs(retention_days=days);self._after_cleanup(result);return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,str,bool,result=bool)
    def changeCacheLocation(self,path,mode='move',delete_old=False):
        try:
            self.migration.migrate(_local_path(path),mode=str(mode or 'move'),delete_old_after_switch=bool(delete_old));self.usage.invalidate();self.refresh();self.operationSucceeded.emit('Cache location updated safely.');return True
        except Exception as exc:self._fail(exc);return False

    @Slot(float,result=bool)
    def setMaximumCacheGB(self,value):
        try:
            number=float(value);size=0 if number<=0 else int(number*1024**3);self.cache.update_preferences(maximumCacheBytes=size);self.storageChanged.emit();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def setAutomaticCleanup(self,mode):
        try:self.cache.update_preferences(automaticCleanup=str(mode).casefold().replace(' ','_'));self.storageChanged.emit();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(bool,result=bool)
    def setCleanupStaleTemp(self,value):
        try:self.cache.update_preferences(cleanupStaleTemp=bool(value));self.storageChanged.emit();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(int,result=bool)
    def setLogRetentionDays(self,value):
        try:self.cache.update_preferences(logRetentionDays=max(1,int(value)));self.storageChanged.emit();return True
        except Exception as exc:self._fail(exc);return False

    @Slot(result=bool)
    def enforceCacheLimit(self):
        try:
            maximum=int(self.cache.preferences.get('maximumCacheBytes') or 0)
            if maximum<=0:return True
            result=self.stale.enforce_limit(maximum);self._after_cleanup(result);return True
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=bool)
    def openFolder(self,path):
        try:
            target=_local_path(path).expanduser();target.mkdir(parents=True,exist_ok=True);return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))))
        except Exception as exc:self._fail(exc);return False

    @Slot(str,result=str)
    def formatBytes(self,value):
        try:return readable_size(int(value))
        except Exception:return '0 B'

    def _after_cleanup(self,result):
        self.usage.invalidate();self.operationSucceeded.emit(f"Freed {readable_size(result.freed_bytes)}. Skipped {len(result.skipped_active)} active file(s)." if result.skipped_active else f"Freed {readable_size(result.freed_bytes)}.");self.refresh()

    def _fail(self,exc):
        if self.logger:self.logger.exception('Storage action failed')
        self.operationFailed.emit(str(exc).strip() or 'Storage action could not be completed.')

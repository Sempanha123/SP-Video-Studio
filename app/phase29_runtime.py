from __future__ import annotations
"""Phase 29 cache/storage management extension layered on Phase 27.

Phase 28 changed QML presentation only, so the runtime foundation remains Phase 27.
This layer adds storage services without creating a second project, media, render,
model, recovery, or Batch ownership system.
"""
import threading
from pathlib import Path
from typing import Any

import app.phase27_runtime as p27
from app.paths import AppPaths
from domain.cache_entry import CacheEntry
from domain.storage_category import StorageCategory
from services.cache_service import CacheService
from services.storage_usage_service import StorageUsageService
from services.cleanup_service import CleanupService
from services.cache_migration_service import CacheMigrationService
from services.disk_monitor_service import DiskMonitorService, DiskState
from services.stale_file_service import StaleFileService
from ui.controllers.storage_controller import StorageController


def _resolve_optional(container, cls):
    try: return container.resolve(cls)
    except Exception: return None


def _project_rows(project_repository):
    if project_repository is None: return []
    for name in ("list_all", "list_projects", "all", "list"):
        fn=getattr(project_repository,name,None)
        if callable(fn):
            try:return list(fn() or [])
            except TypeError:continue
            except Exception:return []
    return []


def _project_id(item):
    if isinstance(item,dict):return str(item.get('project_id') or item.get('id') or item.get('projectId') or '')
    return str(getattr(item,'project_id',None) or getattr(item,'id',None) or '')


def _project_root(item):
    if isinstance(item,dict): raw=item.get('folder') or item.get('path') or item.get('project_path') or item.get('projectPath') or item.get('root')
    else: raw=getattr(item,'folder',None) or getattr(item,'path',None) or getattr(item,'project_path',None) or getattr(item,'projectPath',None) or getattr(item,'root',None)
    return Path(raw).resolve(strict=False) if raw else None


def _generated_audio_reference_checker(db):
    """Best-effort reference protection across existing Phase 8/18/22+ tables.

    The check is intentionally fail-safe: database errors return True (protect).
    File paths are compared both by generated_audio id->file_path where available
    and by path fields used by dubbing/scene/timeline generations.
    """
    def checker(path:Path,project_id:str)->bool:
        candidate=str(Path(path).resolve(strict=False))
        try:
            with db.connect() as c:
                tables={str(r[0]) for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                audio_ids=[]
                if 'generated_audio' in tables:
                    cols={str(r[1]) for r in c.execute('PRAGMA table_info(generated_audio)')}
                    path_col=next((x for x in ('file_path','path','output_path') if x in cols),None)
                    if path_col:
                        fields = "id, active" if "active" in cols else "id"
                        query=f"SELECT {fields} FROM generated_audio WHERE {path_col}=?"
                        args=[candidate]
                        if 'project_id' in cols and project_id:query += ' AND project_id=?';args.append(project_id)
                        rows=list(c.execute(query,args))
                        if "active" in cols and any(bool(r[1]) for r in rows):
                            return True
                        audio_ids=[str(r[0]) for r in rows]
                # Direct path references.
                for table,column in (('dub_segments','generated_audio_path'),('dub_audio_outputs','file_path')):
                    if table in tables:
                        cols={str(r[1]) for r in c.execute(f'PRAGMA table_info({table})')}
                        if column in cols:
                            q=f"SELECT 1 FROM {table} WHERE {column}=? LIMIT 1";a=[candidate]
                            if 'project_id' in cols and project_id:q=q.replace(' LIMIT 1',' AND project_id=? LIMIT 1');a.append(project_id)
                            if c.execute(q,a).fetchone():return True
                if audio_ids:
                    marks=','.join('?' for _ in audio_ids)
                    for table,column in (('speech_blocks','audio_id'),('dub_segments','generated_audio_id'),('timeline_items','audio_id'),('scenes','audio_id'),('render_plan_items','audio_id')):
                        if table not in tables:continue
                        cols={str(r[1]) for r in c.execute(f'PRAGMA table_info({table})')}
                        if column in cols and c.execute(f"SELECT 1 FROM {table} WHERE {column} IN ({marks}) LIMIT 1",audio_ids).fetchone():return True
                return False
        except Exception:
            return True
    return checker


def _active_checker(container, scheduler, db):
    def active(path:Path,entry:CacheEntry)->bool:
        # Batch scheduler already owns a single active Batch lease.
        if scheduler is not None and str(getattr(scheduler,'_active_batch','') or ''):
            if entry.category in {StorageCategory.BATCH_INTERMEDIATE,StorageCategory.RENDER_TEMP,StorageCategory.GENERATED_AUDIO,StorageCategory.TRANSLATION_CACHE}:
                return True
        owner=str(entry.owner_id or '')
        try:
            with db.connect() as c:
                tables={str(r[0]) for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'render_jobs' in tables:
                    cols={str(r[1]) for r in c.execute('PRAGMA table_info(render_jobs)')}
                    if owner and 'id' in cols and 'status' in cols:
                        row=c.execute("SELECT status FROM render_jobs WHERE id=?",(owner,)).fetchone()
                        if row and str(row[0]) in {'queued','preparing','rendering','validating'}:return True
                    path_col=next((x for x in ('temp_path','temp_dir','working_directory') if x in cols),None)
                    if path_col and 'status' in cols:
                        rows=c.execute(f"SELECT {path_col} FROM render_jobs WHERE status IN ('queued','preparing','rendering','validating')").fetchall()
                        resolved=Path(path).resolve(strict=False)
                        for row in rows:
                            if not row[0]:continue
                            base=Path(str(row[0])).resolve(strict=False)
                            if resolved==base or base in resolved.parents:return True
        except Exception:
            # Cleanup must not become unsafe because an activity query failed.
            return True
        return False
    return active


def _asset_external_bytes(asset_repository):
    if asset_repository is None:return 0
    total=0
    try:
        for item in asset_repository.list_all():
            if not bool(getattr(item,'managed',True)):total+=max(0,int(getattr(item,'file_size',0) or 0))
    except Exception:return 0
    return total


def _extend_phase29(container, *, asset_repository=None, scheduler=None, recovery=None):
    paths=container.resolve(AppPaths);logger=container.resolve('logger')
    db=container.resolve(p27.SQLiteDatabase)
    project_repository=_resolve_optional(container,p27.p26.p25.p24.ProjectRepository)
    projects=lambda:_project_rows(project_repository)
    asset_root=lambda:getattr(asset_repository,'library_root',paths.assets) if asset_repository is not None else paths.assets
    cache=CacheService(paths,logger=logger)
    disk=DiskMonitorService(logger=logger)
    cleanup=CleanupService(cache,paths,active_checker=_active_checker(container,scheduler,db),generated_audio_referenced=_generated_audio_reference_checker(db),recovery_veto=(lambda path: str(Path(path).resolve(strict=False)).startswith(str(Path(paths.recovery).resolve(strict=False)))),project_provider=projects,asset_root_provider=asset_root,logger=logger)
    usage=StorageUsageService(paths,cache,project_provider=projects,asset_root_provider=asset_root,external_asset_bytes_provider=(lambda:_asset_external_bytes(asset_repository)),logger=logger)
    migration=CacheMigrationService(cache,active_jobs=(lambda: bool(scheduler is not None and str(getattr(scheduler,'_active_batch','') or ''))),logger=logger)
    stale=StaleFileService(cleanup,cache,logger=logger)
    for cls,obj in ((CacheService,cache),(DiskMonitorService,disk),(CleanupService,cleanup),(StorageUsageService,usage),(CacheMigrationService,migration),(StaleFileService,stale)):
        container.register_instance(cls,obj)
    validation=_resolve_optional(container,p27.p26.BatchValidationService)
    if validation is not None:
        validation.disk_monitor=disk

    # Phase 26 had its own minimal reserve check. Route it through the central
    # Phase 29 monitor so Batch and Storage use one low-disk source of truth.
    if scheduler is not None and not getattr(scheduler._disk_ok,'_phase29_disk',False):
        def disk_ok(batch):
            estimate=int(getattr(batch,'settings',{}).get('disk_reserve_bytes') or 0)
            return disk.can_start_heavy(Path(batch.output_directory),estimated_bytes=estimate)
        disk_ok._phase29_disk=True;scheduler._disk_ok=disk_ok

    # Existing render/export methods are guarded without changing their engines.
    for class_name in ('RenderService','ExportService'):
        try:
            module=__import__(f'services.{class_name[:-7].lower()}_service',fromlist=[class_name]);cls=getattr(module,class_name);obj=_resolve_optional(container,cls)
        except Exception:obj=None
        if obj is None:continue
        for name in ('render','start_render','export'):
            original=getattr(obj,name,None)
            if not callable(original) or getattr(original,'_phase29_disk',False):continue
            def make(orig,operation):
                def wrapped(*args,**kwargs):
                    destination=kwargs.get('destination') or kwargs.get('output_path')
                    if not destination and args:
                        req=args[0];destination=getattr(req,'output_path',None) or getattr(req,'destination',None)
                    if destination:disk.require_space(destination,estimated_bytes=int(kwargs.get('estimated_bytes') or 0),operation=operation)
                    return orig(*args,**kwargs)
                wrapped._phase29_disk=True;return wrapped
            setattr(obj,name,make(original,name))

    # Intentional project deletion may remove cache owned by that project, but
    # Recovery remains owned by Phase27's explicit retention/delete behavior.
    try:
        from services.project_service import ProjectService
        project_service=container.resolve(ProjectService);old_delete=project_service.delete_project
        if not getattr(old_delete,'_phase29_cache_delete',False):
            def delete_project(project_id,*args,**kwargs):
                result=old_delete(project_id,*args,**kwargs)
                try:cleanup.clear_project_cache(str(project_id),include_unreferenced_audio=True)
                except Exception:
                    if logger:logger.warning('Project cache cleanup skipped after deletion',exc_info=True)
                return result
            delete_project._phase29_cache_delete=True;project_service.delete_project=delete_project
    except Exception:pass

    # Obvious stale temp cleanup is lightweight and asynchronous; no large cache
    # purge happens automatically on every launch.
    def startup():
        try:stale.startup_cleanup()
        except Exception:
            if logger:logger.warning('Phase 29 startup stale cleanup skipped',exc_info=True)
    threading.Thread(target=startup,name='Phase29StaleCleanup',daemon=True).start()
    return cache,usage,cleanup,migration,disk,stale


def run()->int:
    p26=p27.p26;p25=p26.p25;p24=p25.p24
    try:from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:return p24.bootstrap.run()
    container=p24.bootstrap.build_container()
    dub_service,dub_apply,dub_validation=p24.extend_phase21(container)
    phase22_repository,languages,visual,speakers,blocks,universal=p24._extend_phase22(container)
    short_repository,candidates,reframe,captions,shorts=p24._extend_phase23(container)
    template_repository,templates,template_apply=p24._extend_phase24(container,phase22_repository,languages,visual,speakers,short_repository)
    asset_repository,assets,asset_usage,asset_project=p25._extend_phase25(container)
    batch_repository,item_repository,imports,batch_service,execution,scheduler=p26._extend_phase26(container,templates,template_apply,asset_repository,languages)
    autosave,recovery,snapshots,shutdown=p27._extend_phase27(container)
    cache,usage,cleanup,migration,disk,stale=_extend_phase29(container,asset_repository=asset_repository,scheduler=scheduler,recovery=recovery)
    worker_pool=container.resolve(p24.WorkerPool);logger=container.resolve('logger');transcript_repository=container.resolve(p24.TranscriptRepository);media_repository=container.resolve(p24.MediaRepository);scene_repository=container.resolve(p24.SceneRepository);project_repository=container.resolve(p24.ProjectRepository)
    class RuntimeDubbingController(p24.DubbingController):
        def __init__(self,parent=None):super().__init__(dub_service,dub_validation,worker_pool,dub_apply,transcript_repository=transcript_repository,media_repository=media_repository,logger=logger,parent=parent)
    class RuntimeLanguageController(p24.LanguageController):
        def __init__(self,parent=None):super().__init__(languages,parent)
    class RuntimeVideoStudioController(p24.VideoStudioController):
        def __init__(self,parent=None):super().__init__(universal,visual,speakers,blocks,phase22_repository,media_repository,container.resolve(p24.SceneService),languages,parent,logger)
    class RuntimeWordTimingController(p24.WordTimingController):
        def __init__(self,parent=None):super().__init__(container.resolve(p24.WordTimingService),parent,logger)
    class RuntimeShortsController(p24.ShortsController):
        def __init__(self,parent=None):super().__init__(shorts,candidates,captions,reframe,short_repository,media_repository,transcript_repository,scene_repository,project_repository,languages,logger,parent)
    class RuntimeTemplateController(p24.TemplateController):
        def __init__(self,parent=None):super().__init__(templates,template_apply,logger,parent)
    class RuntimeAssetController(p25.AssetLibraryController):
        def __init__(self,parent=None):super().__init__(assets,asset_repository,asset_usage,asset_project,importer=container.resolve(p25.AssetImportService),relink=container.resolve(p25.AssetRelinkService),logger=logger,parent=parent)
    class RuntimeBatchController(p26.BatchController):
        def __init__(self,parent=None):super().__init__(batch_service,imports,batch_repository,item_repository,templates,scheduler,logger=logger,parent=parent)
    class RuntimeRecoveryController(p27.RecoveryController):
        def __init__(self,parent=None):super().__init__(autosave,recovery,snapshots,shutdown,logger,parent)
    class RuntimeStorageController(StorageController):
        def __init__(self,parent=None):super().__init__(usage,cleanup,cache,migration,disk,stale,worker_pool=worker_pool,logger=logger,parent=parent)
    for cls,module,name in ((RuntimeDubbingController,'SPVideoStudio.Phase21','Dubbing'),(RuntimeLanguageController,'SPVideoStudio.Phase22','LanguageCatalog'),(RuntimeVideoStudioController,'SPVideoStudio.Phase22','VideoStudio'),(RuntimeWordTimingController,'SPVideoStudio.Phase22','WordTiming'),(RuntimeShortsController,'SPVideoStudio.Phase23','Shorts'),(RuntimeTemplateController,'SPVideoStudio.Phase24','Templates'),(RuntimeAssetController,'SPVideoStudio.Phase25','AssetLibrary'),(RuntimeBatchController,'SPVideoStudio.Phase26','BatchFactoryController'),(RuntimeRecoveryController,'SPVideoStudio.Phase27','Recovery'),(RuntimeStorageController,'SPVideoStudio.Phase29','Storage')):
        qmlRegisterSingletonType(cls,module,1,0,name)
    originals=p27._install_controller_bridges(p24.bootstrap,autosave);engine_patch=p27._install_recovery_overlay_engine(logger)
    original_build=p24.bootstrap.build_container;p24.bootstrap.build_container=lambda:container
    try:return p24.bootstrap.run()
    finally:
        p24.bootstrap.build_container=original_build
        for name,cls in originals.items():setattr(p24.bootstrap,name,cls)
        if engine_patch:engine_patch[0].QQmlApplicationEngine=engine_patch[1]

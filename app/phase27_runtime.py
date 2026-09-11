from __future__ import annotations
"""Phase 27 autosave + recovery extension layered on Phase 26."""
from pathlib import Path
from typing import Any
import app.phase26_runtime as p26

from app.paths import AppPaths
from domain.recovery_errors import AutosaveFailed
from services.autosave_service import AutosaveService
from services.project_integrity_service import ProjectIntegrityService
from services.project_snapshot_codec import ProjectSnapshotCodec
from services.recovery_snapshot_service import RecoverySnapshotService
from services.recovery_service import RecoveryService
from services.interrupted_job_recovery_service import InterruptedJobRecoveryService
from services.shutdown_service import ShutdownService
from services.temp_recovery_service import TempRecoveryService
from storage.database import SQLiteDatabase
from storage.recovery_store import RecoveryStore
from storage.repositories.recovery_repository import RecoveryRepository
from ui.controllers.recovery_controller import RecoveryController


def _version()->str:
    try:
        from importlib.metadata import version
        return version('sp-video-studio')
    except Exception:return '27'

def _resolve_optional(container,cls):
    try:return container.resolve(cls)
    except Exception:return None

def _project_id(obj,args,kwargs,index=0):
    value=kwargs.get('project_id') or kwargs.get('projectId')
    if value:return str(value)
    if len(args)>index and isinstance(args[index],str):return str(args[index])
    value=getattr(obj,'project_id',None) or getattr(obj,'projectId',None)
    return str(value or '')

def _patch_methods(obj,names,autosave,topic='structural',project_index=0):
    if obj is None:return
    for name in names:
        original=getattr(obj,name,None)
        if not callable(original) or getattr(original,'_phase27_patched',False):continue
        def make(orig):
            def wrapped(*args,**kwargs):
                result=orig(*args,**kwargs)
                pid=_project_id(result,args,kwargs,project_index)
                if pid:autosave.mark_structural_saved(pid,topic)
                return result
            wrapped._phase27_patched=True
            return wrapped
        setattr(obj,name,make(original))

def _extend_phase27(container):
    db=container.resolve(SQLiteDatabase);paths=container.resolve(AppPaths);logger=container.resolve('logger')
    repo=RecoveryRepository(db);store=RecoveryStore(paths.recovery,retention=8);autosave=AutosaveService(repo,logger=logger);codec=ProjectSnapshotCodec(db,logger)
    integrity=ProjectIntegrityService(db,logger)
    batch_recovery=_resolve_optional(container,p26.BatchRecoveryService)
    jobs=InterruptedJobRecoveryService(db,repo,batch_recovery=batch_recovery,logger=logger)
    snapshots=RecoverySnapshotService(repo,store,codec,autosave,app_version=_version(),logger=logger)
    recovery=RecoveryService(repo,store,snapshots,codec,autosave,integrity,jobs,app_version=_version(),logger=logger)
    shutdown=ShutdownService(autosave,recovery,snapshots,logger=logger)
    temp=TempRecoveryService(paths.temp,logger=logger)
    for cls,obj in ((RecoveryRepository,repo),(RecoveryStore,store),(AutosaveService,autosave),(ProjectSnapshotCodec,codec),(ProjectIntegrityService,integrity),(InterruptedJobRecoveryService,jobs),(RecoverySnapshotService,snapshots),(RecoveryService,recovery),(ShutdownService,shutdown),(TempRecoveryService,temp)):
        container.register_instance(cls,obj)
    recovery.start_session()

    # Existing structural services already transact their own durable mutations.
    # Phase 27 only adds revision bookkeeping; it does not duplicate serialization.
    p24=p26.p25.p24
    structural=[
        (_resolve_optional(container,p24.SceneService),('add_scene','delete_scene','move_scene','reorder_scenes','assign_media','set_transition'),'scene'),
        (_resolve_optional(container,p24.TimelineService),('add_track','remove_track','move_item','trim_item','split_item','update_item'),'timeline'),
    ]
    try:
        from services.speaker_service import SpeakerService
        structural.append((_resolve_optional(container,SpeakerService),('create','update','delete'),'speaker'))
    except Exception:pass
    try:
        from services.speech_block_service import SpeechBlockService
        structural.append((_resolve_optional(container,SpeechBlockService),('add','update','move','delete'),'speech_text'))
    except Exception:pass
    for service,names,topic in structural:_patch_methods(service,names,autosave,topic,0)

    # Template apply is an immediate structural milestone.
    try:
        from services.template_apply_service import TemplateApplyService
        apply=_resolve_optional(container,TemplateApplyService)
        _patch_methods(apply,('apply_to_project',),autosave,'template_apply',1)
    except Exception:pass

    # Critical derived work refuses to continue when pending edits cannot flush.
    def protect_call(obj,name,kind,project_getter):
        if obj is None:return
        original=getattr(obj,name,None)
        if not callable(original) or getattr(original,'_phase27_critical',False):return
        def wrapped(*args,**kwargs):
            pid=str(project_getter(args,kwargs) or '')
            if pid and autosave.state(pid).dirty:
                try:snapshots.create(pid,recovery.session.session_id,snapshot_type=f'pre_{kind}',reason=f'Recovery point before {kind}')
                except Exception:pass
                if not autosave.critical_flush(pid,reason=kind):raise AutosaveFailed('Your latest changes could not be saved. The operation was cancelled.')
            return original(*args,**kwargs)
        wrapped._phase27_critical=True;setattr(obj,name,wrapped)
    try:
        from services.export_service import ExportService
        protect_call(_resolve_optional(container,ExportService),'export','export',lambda a,k:getattr(a[0] if a else k.get('request'),'project_id',''))
    except Exception:pass
    try:
        from services.render_service import RenderService
        render=_resolve_optional(container,RenderService)
        for method in ('render','start_render'):
            protect_call(render,method,'render',lambda a,k:getattr(a[0] if a else None,'project_id',''))
    except Exception:pass

    scheduler=_resolve_optional(container,p26.BatchScheduler)
    if scheduler and not getattr(scheduler.start,'_phase27_critical',False):
        original_start=scheduler.start
        def start(batch_id):
            dirty=list(autosave.dirty_projects())
            for pid in dirty:
                try:snapshots.create(pid,recovery.session.session_id,snapshot_type='pre_batch',reason='Recovery point before Batch start')
                except Exception:pass
            if not autosave.flush_all(reason='batch_start'):raise AutosaveFailed('Your latest changes could not be saved. Batch start was cancelled.')
            return original_start(batch_id)
        start._phase27_critical=True;scheduler.start=start
        shutdown.register_heavy_job_hook(scheduler.shutdown)

    # Intentional project deletion removes hidden recovery copies by default.
    try:
        from services.project_service import ProjectService
        projects=container.resolve(ProjectService);old_delete=projects.delete_project
        if not getattr(old_delete,'_phase27_delete',False):
            def delete_project(project_id,*args,**kwargs):
                result=old_delete(project_id,*args,**kwargs);snapshots.delete_project(project_id);return result
            delete_project._phase27_delete=True;projects.delete_project=delete_project
    except Exception:pass
    return autosave,recovery,snapshots,shutdown


class _AutosaveTimerBridge:
    def __init__(self,autosave,controller,topic):self.autosave=autosave;self.controller=controller;self.topic=topic
    def start(self,*_):
        pid=str(getattr(self.controller,'_project_id','') or '')
        if pid:self.autosave.mark_dirty(pid,self.topic)
    def stop(self):pass
    def isActive(self):return False
    def setInterval(self,*_):pass
    def setSingleShot(self,*_):pass


def _centralized_controller(base,autosave,topic,timer_attr,save_name):
    direct=getattr(base,save_name)
    class Central(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            timer=getattr(self,timer_attr,None)
            try:timer.stop()
            except Exception:pass
            setattr(self,timer_attr,_AutosaveTimerBridge(autosave,self,topic))
            def handler(pid,_topics,_revision):
                if str(getattr(self,'_project_id',''))!=pid:return
                result=direct(self)
                if result is False:raise AutosaveFailed(f'{topic} save failed')
            autosave.register_handler(topic,handler)
    def save(self,*args,**kwargs):
        pid=str(getattr(self,'_project_id','') or '')
        controller_dirty=bool(getattr(self,'_dirty',False) or getattr(self,'_dirty_ids',False) or getattr(self,'_dirty_script',False))
        if pid and controller_dirty and not autosave.state(pid).dirty:autosave.mark_dirty(pid,topic)
        if pid and autosave.state(pid).dirty:
            try:return autosave.flush(pid,reason='manual')
            except AutosaveFailed:return False
        return direct(self,*args,**kwargs)
    setattr(Central,save_name,save);Central.__name__='Phase27'+base.__name__;return Central


def _install_controller_bridges(bootstrap,autosave):
    originals={}
    for attr,topic,timer,save in (('ScriptController','script','_autosave','save'),('TranslationController','translation','_autosave','saveEdits'),('SubtitleController','subtitle_text','_timer','saveEdits')):
        base=getattr(bootstrap,attr,None)
        if base:
            originals[attr]=base;setattr(bootstrap,attr,_centralized_controller(base,autosave,topic,timer,save))
    return originals


def _install_recovery_overlay_engine(logger):
    try:
        import PySide6.QtQml as QtQml
        from PySide6.QtCore import QUrl
    except ImportError:return None
    original=QtQml.QQmlApplicationEngine
    host=Path(__file__).resolve().parents[1]/'ui'/'qml'/'recovery'/'RecoveryHost.qml'
    class Phase27Engine(original):
        def load(self,url):
            super().load(url)
            try:
                roots=self.rootObjects()
                if not roots:return
                component=QtQml.QQmlComponent(self,QUrl.fromLocalFile(str(host)))
                obj=component.create(self.rootContext())
                if obj is None:
                    if logger:logger.warning('Phase 27 recovery overlay failed: %s',component.errors())
                    return
                root=roots[0];content=root.property('contentItem')
                if content is not None and hasattr(obj,'setParentItem'):obj.setParentItem(content)
                obj.setParent(root);self._phase27_recovery_host=obj
            except Exception:
                if logger:logger.exception('Could not mount Phase 27 recovery UI')
    QtQml.QQmlApplicationEngine=Phase27Engine
    return QtQml,original


def run()->int:
    p25=p26.p25;p24=p25.p24
    try:from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:return p24.bootstrap.run()
    container=p24.bootstrap.build_container()
    dub_service,dub_apply,dub_validation=p24.extend_phase21(container)
    phase22_repository,languages,visual,speakers,blocks,universal=p24._extend_phase22(container)
    short_repository,candidates,reframe,captions,shorts=p24._extend_phase23(container)
    template_repository,templates,template_apply=p24._extend_phase24(container,phase22_repository,languages,visual,speakers,short_repository)
    asset_repository,assets,asset_usage,asset_project=p25._extend_phase25(container)
    batch_repository,item_repository,imports,batch_service,execution,scheduler=p26._extend_phase26(container,templates,template_apply,asset_repository,languages)
    autosave,recovery,snapshots,shutdown=_extend_phase27(container)
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
    class RuntimeRecoveryController(RecoveryController):
        def __init__(self,parent=None):super().__init__(autosave,recovery,snapshots,shutdown,logger,parent)
    for cls,module,name in ((RuntimeDubbingController,'SPVideoStudio.Phase21','Dubbing'),(RuntimeLanguageController,'SPVideoStudio.Phase22','LanguageCatalog'),(RuntimeVideoStudioController,'SPVideoStudio.Phase22','VideoStudio'),(RuntimeWordTimingController,'SPVideoStudio.Phase22','WordTiming'),(RuntimeShortsController,'SPVideoStudio.Phase23','Shorts'),(RuntimeTemplateController,'SPVideoStudio.Phase24','Templates'),(RuntimeAssetController,'SPVideoStudio.Phase25','AssetLibrary'),(RuntimeBatchController,'SPVideoStudio.Phase26','BatchFactoryController'),(RuntimeRecoveryController,'SPVideoStudio.Phase27','Recovery')):
        qmlRegisterSingletonType(cls,module,1,0,name)
    originals=_install_controller_bridges(p24.bootstrap,autosave);engine_patch=_install_recovery_overlay_engine(logger)
    original_build=p24.bootstrap.build_container;p24.bootstrap.build_container=lambda:container
    try:return p24.bootstrap.run()
    finally:
        p24.bootstrap.build_container=original_build
        for name,cls in originals.items():setattr(p24.bootstrap,name,cls)
        if engine_patch:engine_patch[0].QQmlApplicationEngine=engine_patch[1]

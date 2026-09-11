from __future__ import annotations
"""Phase 25 global Asset Library extension layered on the Phase 24 runtime."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import app.phase24_runtime as p24
from app.paths import AppPaths
from domain.media import MediaAsset,MediaStatus,media_utc_now_iso
from services.asset_import_service import AssetImportService
from services.asset_library_service import AssetLibraryService
from services.asset_project_integration_service import AssetProjectIntegrationService
from services.asset_relink_service import AssetRelinkService
from services.asset_search_service import AssetSearchService
from services.asset_template_integration_service import AssetTemplateIntegrationService
from services.asset_usage_service import AssetUsageService
from services.asset_validation_service import AssetValidationService
from services.media_service import MediaService
from services.project_service import ProjectService
from services.template_apply_service import TemplateApplyService
from services.universal_video_service import UniversalVideoService
from services.visual_layer_service import VisualLayerService
from storage.database import SQLiteDatabase
from storage.repositories.asset_repository import AssetRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from ui.controllers.asset_library_controller import AssetLibraryController


def _extend_phase25(container):
    db=container.resolve(SQLiteDatabase); paths=container.resolve(AppPaths)
    repo=AssetRepository(db,paths.assets); validation=AssetValidationService(); media_service=container.resolve(MediaService)
    importer=AssetImportService(repo,media_service,validation,container.resolve('logger'))
    search=AssetSearchService(repo); usage=AssetUsageService(repo,container.resolve(ProjectRepository),container.resolve(MediaRepository),container.resolve(VisualLayerService),container.resolve('logger'))
    relink=AssetRelinkService(repo,importer,container.resolve(MediaRepository),validation,container.resolve('logger'))
    library=AssetLibraryService(repo,search,importer,usage,relink,validation,container.resolve('logger'))
    try:universal=container.resolve(UniversalVideoService)
    except Exception:universal=None
    project_integration=AssetProjectIntegrationService(usage,universal)
    template_integration=AssetTemplateIntegrationService(usage)
    for cls,obj in ((AssetRepository,repo),(AssetValidationService,validation),(AssetImportService,importer),(AssetSearchService,search),(AssetUsageService,usage),(AssetRelinkService,relink),(AssetLibraryService,library),(AssetProjectIntegrationService,project_integration),(AssetTemplateIntegrationService,template_integration)):
        container.register_instance(cls,obj)

    # Project Media remains authoritative, but global references must never be treated as project-owned files.
    if not getattr(media_service,'_phase25_global_asset_patch',False):
        original_remove=media_service.remove_media; original_duplicate=media_service.duplicate_project_media_map; media_repo=container.resolve(MediaRepository)
        def remove_media_safe(project_id,asset_id):
            m=media_repo.get_by_id(asset_id)
            if m is not None and m.project_id==project_id and (m.metadata_json.get('globalAssetId') or m.metadata_json.get('externalReference')):
                repo.remove_usage_for_media(m.id);media_repo.delete(m.id);return
            return original_remove(project_id,asset_id)
        def duplicate_media_safe(source,duplicate):
            source_items=media_repo.list_by_project(source.project_id)
            local=[m for m in source_items if not (m.metadata_json.get('globalAssetId') or m.metadata_json.get('externalReference'))]
            refs=[m for m in source_items if m not in local]
            saved=media_repo.list_by_project
            def filtered(project_id,*args,**kwargs):
                if project_id==source.project_id:return list(local)
                return saved(project_id,*args,**kwargs)
            media_repo.list_by_project=filtered
            try:mapping=original_duplicate(source,duplicate)
            finally:media_repo.list_by_project=saved
            for m in refs:
                nid=str(uuid4());clone=MediaAsset(asset_id=nid,project_id=duplicate.project_id,media_type=m.type,name=m.name,original_path=m.original_path,project_path=m.project_path,thumbnail_path=m.thumbnail_path,duration_ms=m.duration_ms,width=m.width,height=m.height,fps=m.fps,codec=m.codec,audio_codec=m.audio_codec,sample_rate=m.sample_rate,channels=m.channels,file_size=m.file_size,mime_type=m.mime_type,extension=m.extension,created_at=m.created_at,imported_at=media_utc_now_iso(),status=m.status,metadata_json=deepcopy(m.metadata_json));media_repo.create(clone);mapping[m.id]=nid
                aid=str(clone.metadata_json.get('globalAssetId',''))
                if aid and repo.get(aid):
                    from domain.asset_usage import AssetUsage
                    repo.record_usage(AssetUsage(aid,duplicate.project_id,nid,str(clone.metadata_json.get('assetUsageType','other'))))
            return mapping
        media_service.remove_media=remove_media_safe;media_service.duplicate_project_media_map=duplicate_media_safe;media_service._phase25_global_asset_patch=True

    project_service=container.resolve(ProjectService)
    if not getattr(project_service,'_phase25_usage_patch',False):
        old_delete=project_service.delete_project
        def delete_with_usage(project_id):repo.remove_usage_for_project(project_id);return old_delete(project_id)
        project_service.delete_project=delete_with_usage;project_service._phase25_usage_patch=True

    # Phase 24 placeholders may explicitly request a local global Asset. Convert that request to a normal project MediaAsset before apply.
    apply=container.resolve(TemplateApplyService)
    if not getattr(apply,'_phase25_asset_patch',False):
        old_apply=apply.apply_to_project
        def apply_with_assets(template,project_id,**kwargs):
            if 'resolutions' in kwargs:kwargs['resolutions']=template_integration.resolve_map(project_id,kwargs.get('resolutions') or {})
            return old_apply(template,project_id,**kwargs)
        apply.apply_to_project=apply_with_assets;apply._phase25_asset_patch=True
    return repo,library,usage,project_integration


def run()->int:
    try:from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:return p24.bootstrap.run()
    container=p24.bootstrap.build_container()
    dub_service,dub_apply,dub_validation=p24.extend_phase21(container)
    phase22_repository,languages,visual,speakers,blocks,universal=p24._extend_phase22(container)
    short_repository,candidates,reframe,captions,shorts=p24._extend_phase23(container)
    template_repository,templates,template_apply=p24._extend_phase24(container,phase22_repository,languages,visual,speakers,short_repository)
    asset_repository,assets,asset_usage,asset_project=_extend_phase25(container)
    worker_pool=container.resolve(p24.WorkerPool);logger=container.resolve('logger')
    transcript_repository=container.resolve(p24.TranscriptRepository);media_repository=container.resolve(p24.MediaRepository);scene_repository=container.resolve(p24.SceneRepository);project_repository=container.resolve(p24.ProjectRepository)
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
    class RuntimeAssetController(AssetLibraryController):
        def __init__(self,parent=None):super().__init__(assets,asset_repository,asset_usage,asset_project,importer=container.resolve(AssetImportService),relink=container.resolve(AssetRelinkService),logger=logger,parent=parent)
    qmlRegisterSingletonType(RuntimeDubbingController,'SPVideoStudio.Phase21',1,0,'Dubbing');qmlRegisterSingletonType(RuntimeLanguageController,'SPVideoStudio.Phase22',1,0,'LanguageCatalog');qmlRegisterSingletonType(RuntimeVideoStudioController,'SPVideoStudio.Phase22',1,0,'VideoStudio');qmlRegisterSingletonType(RuntimeWordTimingController,'SPVideoStudio.Phase22',1,0,'WordTiming');qmlRegisterSingletonType(RuntimeShortsController,'SPVideoStudio.Phase23',1,0,'Shorts');qmlRegisterSingletonType(RuntimeTemplateController,'SPVideoStudio.Phase24',1,0,'Templates');qmlRegisterSingletonType(RuntimeAssetController,'SPVideoStudio.Phase25',1,0,'AssetLibrary')
    original=p24.bootstrap.build_container;p24.bootstrap.build_container=lambda:container
    try:return p24.bootstrap.run()
    finally:p24.bootstrap.build_container=original

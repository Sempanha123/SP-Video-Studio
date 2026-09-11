from __future__ import annotations
import shutil
from pathlib import Path
from uuid import uuid4
from domain.asset_errors import AssetMissing,AssetNotFound,AssetStorageError
from domain.asset_usage import AssetUsage
from domain.chroma_key import ChromaKeySettings
from domain.media import MediaAsset,MediaStatus,media_utc_now_iso
from storage.repositories.asset_repository import AssetRepository

class AssetUsageService:
    def __init__(self,assets:AssetRepository,projects,media_repository,visual_layer_service=None,logger=None):
        self.assets=assets;self.projects=projects;self.media=media_repository;self.visual=visual_layer_service;self.logger=logger
    def _asset(self,asset_id):
        a=self.assets.get(asset_id)
        if a is None:raise AssetNotFound('Asset could not be found.')
        return a
    def _project(self,project_id):
        p=self.projects.get_by_id(project_id)
        if p is None:raise AssetNotFound('Project could not be found.')
        return p
    def add_to_project(self,project_id:str,asset_id:str,usage_type:str='other')->MediaAsset:
        a=self._asset(asset_id);self._project(project_id);path=a.resolved_path(self.assets.library_root)
        if not path.is_file(): self.assets.set_status(a.id,'missing');raise AssetMissing('The reusable asset file could not be found.')
        for m in self.media.list_by_project(project_id):
            if str(m.metadata_json.get('globalAssetId',''))==a.id:
                self.assets.record_usage(AssetUsage(a.id,project_id,m.id,usage_type));return m
        meta={'globalAssetId':a.id,'globalAssetMode':'reference','globalAssetFingerprint':a.fingerprint,'globalAssetManaged':a.managed,'assetSubtype':a.subtype}
        if a.metadata.get('chromaReady'):meta['chromaReady']=True
        thumb=a.resolved_thumbnail(self.assets.library_root)
        m=MediaAsset(asset_id=str(uuid4()),project_id=project_id,media_type=a.type,name=a.name,original_path=str(path),project_path=str(path),thumbnail_path=str(thumb) if thumb and thumb.is_file() else None,duration_ms=a.duration_ms,width=a.width,height=a.height,fps=a.fps,codec=a.video_codec,audio_codec=a.audio_codec,sample_rate=a.sample_rate,channels=a.channels,file_size=a.file_size,mime_type=a.mime_type,extension=a.extension,created_at=a.created_at,imported_at=media_utc_now_iso(),status=MediaStatus.READY,metadata_json=meta)
        self.media.create(m);self.assets.record_usage(AssetUsage(a.id,project_id,m.id,usage_type));return m
    def make_project_copy(self,project_id:str,project_media_id:str)->MediaAsset:
        project=self._project(project_id);m=self.media.get_by_id(project_media_id)
        if m is None or m.project_id!=project_id:raise AssetNotFound('Project media could not be found.')
        aid=str(m.metadata_json.get('globalAssetId',''))
        if not aid:return m
        a=self._asset(aid);source=a.resolved_path(self.assets.library_root)
        if not source.is_file():raise AssetMissing('The reusable asset file could not be found.')
        folder={'video':'video','audio':'audio','image':'images'}[m.type];dest=Path(project.project_path)/'media'/folder/f'{m.id}{source.suffix.lower()}'
        dest.parent.mkdir(parents=True,exist_ok=True);tmp=dest.with_suffix(dest.suffix+'.partial');tmp.unlink(missing_ok=True)
        try:shutil.copy2(source,tmp);tmp.replace(dest)
        except Exception as exc:tmp.unlink(missing_ok=True);raise AssetStorageError('Could not create the project media copy.') from exc
        thumb=None
        source_thumb=a.resolved_thumbnail(self.assets.library_root)
        if source_thumb and source_thumb.is_file():
            thumb=Path(project.project_path)/'thumbnails'/f'{m.id}{source_thumb.suffix or ".jpg"}';thumb.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source_thumb,thumb)
        meta=dict(m.metadata_json);[meta.pop(k,None) for k in ('globalAssetId','globalAssetMode','globalAssetFingerprint','globalAssetManaged')];meta['localizedFromGlobalAssetId']=aid
        m.original_path=str(source);m.project_path=str(dest);m.thumbnail_path=str(thumb) if thumb else None;m.file_size=dest.stat().st_size;m.metadata_json=meta;m.status=MediaStatus.READY
        self.media.update(m);self.assets.remove_usage_for_media(m.id);return m
    def make_project_portable(self,project_id:str)->list[str]:
        ids=[]
        for m in list(self.media.list_by_project(project_id)):
            if m.metadata_json.get('globalAssetId'):self.make_project_copy(project_id,m.id);ids.append(m.id)
        return ids
    def reconcile_project(self,project_id:str)->int:
        count=0
        for m in self.media.list_by_project(project_id):
            aid=str(m.metadata_json.get('globalAssetId',''))
            if aid and self.assets.get(aid):self.assets.record_usage(AssetUsage(aid,project_id,m.id,str(m.metadata_json.get('assetUsageType','other'))));count+=1
        return count
    def attribution_summary(self,project_id:str)->list[dict]:
        seen=set();rows=[]
        for u in self.assets.project_usages(project_id):
            aid=str(u['asset_id'])
            if aid in seen:continue
            seen.add(aid);lic=self.assets.license(aid);a=self.assets.get(aid)
            if a and lic.attribution_required:rows.append({'assetId':aid,'name':a.name,'attributionText':lic.attribution_text,'sourceUrl':lic.source_url})
        return rows
    def add_visual_layer(self,project_id:str,scene_id:str,asset_id:str,*,role:str='broll',speaker_id:str='',apply_defaults:bool=True):
        if self.visual is None:raise AssetStorageError('Layered video service is unavailable.')
        a=self._asset(asset_id);m=self.add_to_project(project_id,asset_id,'presenter' if role in {'presenter','reporter','character'} else 'broll')
        layer=self.visual.add_media_layer(project_id,scene_id,m.id,role=role,speaker_id=speaker_id)
        if apply_defaults:
            preset=str(a.metadata.get('pipPosition','') or a.metadata.get('defaultPosition',''))
            if preset in {'top_left','top_right','bottom_left','bottom_right','center'}:
                try:self.visual.apply_pip_preset(project_id,scene_id,layer.id,preset)
                except Exception:pass
            if bool(a.metadata.get('chromaReady')) or a.subtype=='green_screen':
                settings=ChromaKeySettings(enabled=True,key_color=str(a.metadata.get('keyColor','#00FF00')),similarity=float(a.metadata.get('chromaSimilarity',.22)),blend=float(a.metadata.get('chromaBlend',.08)),spill_reduction=float(a.metadata.get('spillReduction',.0)),edge_softness=float(a.metadata.get('edgeSoftness',.0)))
                try:self.visual.set_chroma_key(project_id,scene_id,layer.id,settings)
                except TypeError:self.visual.set_chroma_key(project_id,scene_id,layer.id,settings.to_dict())
        return layer
    def template_resolution(self,project_id:str,asset_id:str)->str:return self.add_to_project(project_id,asset_id,'template').id

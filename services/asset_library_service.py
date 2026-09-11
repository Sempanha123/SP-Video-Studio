from __future__ import annotations
import shutil
from pathlib import Path
from domain.asset_collection import AssetCollection
from domain.asset_errors import AssetInUse,AssetNotFound,AssetPathUnsafe,AssetStorageError
from domain.asset_license import AssetLicense

class AssetLibraryService:
    def __init__(self,repository,search,importer,usage,relink,validation,logger=None):
        self.repository=repository;self.search_service=search;self.importer=importer;self.usage=usage;self.relink=relink;self.validation=validation;self.logger=logger
    @property
    def library_root(self):return self.repository.library_root
    def list_assets(self,**kwargs):return self.search_service.search(**kwargs)
    def get(self,asset_id):
        a=self.repository.get(asset_id)
        if a is None:raise AssetNotFound('Asset could not be found.')
        return a
    def details(self,asset_id):
        a=self.get(asset_id);d=a.to_dict();d.update({'resolvedPath':str(a.resolved_path(self.repository.library_root)),'tags':self.repository.tags(a.id),'collections':self.repository.asset_collections(a.id),'usageCount':self.repository.usage_count(a.id),'usage':self.repository.usages(a.id),'license':self.repository.license(a.id).to_dict()});return d
    def update(self,asset_id,*,name=None,subtype=None,notes=None,spoken_language=None,metadata=None):
        a=self.get(asset_id)
        if name is not None:a.name=str(name).strip() or a.name
        if subtype is not None:self.validation.validate_subtype(a.type,str(subtype));a.subtype=str(subtype)
        if notes is not None:a.notes=str(notes)
        if spoken_language is not None:a.spoken_language=str(spoken_language)
        if metadata is not None:a.metadata={**a.metadata,**dict(metadata)}
        return self.repository.update(a)
    def set_favorite(self,asset_id,value):a=self.get(asset_id);a.favorite=bool(value);return self.repository.update(a)
    def set_tags(self,asset_id,tags):self.get(asset_id);self.repository.set_tags(asset_id,list(tags));return self.repository.tags(asset_id)
    def create_collection(self,name,description=''):
        item=AssetCollection(str(name).strip(),str(description).strip());return self.repository.create_collection(item)
    def collections(self):return self.repository.collections()
    def set_collection(self,asset_id,collection_id,enabled):self.get(asset_id);self.repository.set_collection_membership(asset_id,collection_id,bool(enabled))
    def delete_collection(self,collection_id):self.repository.delete_collection(collection_id)
    def set_license(self,asset_id,**values):
        self.get(asset_id);current=self.repository.license(asset_id)
        for key in ('rights_status','source_url','license_name','notes','attribution_required','attribution_text'):
            if key in values:setattr(current,key,values[key])
        return self.repository.set_license(current)
    def delete_asset(self,asset_id,*,strategy='cancel'):
        a=self.get(asset_id);usages=self.repository.usages(a.id);keep_physical=False
        if usages:
            if strategy=='cancel':raise AssetInUse(f'This asset is used by {self.repository.usage_count(a.id)} projects.')
            if strategy=='project_copies':
                for u in list(usages):self.usage.make_project_copy(u['projectId'],u['projectMediaId'])
            elif strategy=='keep_file':
                keep_physical=True
                for u in list(usages):
                    m=self.usage.media.get_by_id(u['projectMediaId'])
                    if m:
                        meta=dict(m.metadata_json);[meta.pop(k,None) for k in ('globalAssetId','globalAssetMode','globalAssetFingerprint','globalAssetManaged')];meta['externalReference']=True;m.metadata_json=meta;self.usage.media.update(m)
                    self.repository.remove_usage_for_media(u['projectMediaId'])
            else:raise AssetInUse('Choose a safe removal option for an asset that is in use.')
        if a.managed and not keep_physical:
            p=self.validation.assert_managed_path(a.resolved_path(self.repository.library_root),self.repository.library_root)
            thumb=a.resolved_thumbnail(self.repository.library_root)
            if p.exists():p.unlink()
            if thumb and thumb.exists():self.validation.assert_managed_path(thumb,self.repository.library_root).unlink()
        # Referenced files are deliberately never removed from disk.
        self.repository.delete(a.id)
        if self.logger:self.logger.info('Global asset removed: %s managed=%s',a.id,a.managed)
    def storage_usage(self):
        rows={'total':0,'video':0,'audio':0,'image':0}
        for a in self.repository.list_all():
            if not a.managed:continue
            rows['total']+=a.file_size;rows[a.type]=rows.get(a.type,0)+a.file_size
        return rows
    def migrate_library(self,new_root:str|Path,*,mode='move'):
        old=self.repository.library_root;new=Path(new_root).expanduser().resolve()
        if new==old:return new
        new.mkdir(parents=True,exist_ok=True)
        if any(new.iterdir()): raise AssetStorageError('Choose an empty Asset Library destination.')
        try:
            if mode not in {'copy','move'}:raise AssetStorageError('Choose Move Managed Library or Copy Managed Library.')
            # Copy first so a failed migration leaves the authoritative old root intact.
            for child in old.iterdir():
                target=new/child.name
                if child.is_dir():shutil.copytree(child,target)
                else:shutil.copy2(child,target)
            self.repository.set_library_root(new)
            if mode=='move':
                for child in list(old.iterdir()):
                    if child.is_dir():shutil.rmtree(child)
                    else:child.unlink(missing_ok=True)
            if self.logger:self.logger.info('Asset library migrated: mode=%s',mode)
            return new
        except Exception as exc:
            if isinstance(exc,AssetStorageError):raise
            raise AssetStorageError('Could not migrate the Asset Library safely.') from exc
    def lightweight_startup_scan(self):return self.relink.refresh_statuses()

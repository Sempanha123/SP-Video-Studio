from __future__ import annotations
from pathlib import Path
from domain.asset_errors import AssetMissing,AssetNotFound,AssetRelinkMismatch
from services.asset_validation_service import AssetValidationService

class AssetRelinkService:
    def __init__(self,repository,import_service,media_repository,validation:AssetValidationService,logger=None):
        self.repository=repository;self.importer=import_service;self.media=media_repository;self.validation=validation;self.logger=logger
    def refresh_statuses(self)->dict[str,int]:
        result={'ready':0,'missing':0,'changed':0}
        for a in self.repository.list_all():
            p=a.resolved_path(self.repository.library_root)
            if not p.is_file():status='missing'
            else:
                st=p.stat();status='changed' if a.source_mtime_ns and (st.st_mtime_ns!=a.source_mtime_ns or st.st_size!=a.file_size) else 'ready'
            if a.status_code!=status:self.repository.set_status(a.id,status)
            result[status]=result.get(status,0)+1
        return result
    def relink(self,asset_id:str,new_path:str|Path,*,force:bool=False):
        a=self.repository.get(asset_id)
        if a is None:raise AssetNotFound('Asset could not be found.')
        if a.managed:raise AssetRelinkMismatch('Managed assets use Asset Library migration, not external relink.')
        p=Path(new_path).expanduser().resolve(strict=True);new_type=self.importer.media.classifier.classify(p)
        if not new_type:raise AssetRelinkMismatch('Replacement file is not a supported media file.')
        fp,kind=self.importer.fingerprint(p);duration=width=height=None
        if new_type in {'video','audio'}:
            probe=self.importer.media.prober.probe(p,expected_type=new_type);duration,width,height=probe.duration_ms,probe.width,probe.height
        elif new_type=='image':
            from PIL import Image,ImageOps
            with Image.open(p) as im:width,height=ImageOps.exif_transpose(im).size
        state=self.validation.relink_state(a,new_type,p.stat().st_size,fp,duration,width,height)
        if not state['compatible'] and not force:raise AssetRelinkMismatch(state['message'])
        a.file_path=str(p);a.file_size=p.stat().st_size;a.fingerprint=fp;a.fingerprint_kind=kind;a.source_mtime_ns=p.stat().st_mtime_ns;a.status='ready';self.repository.update(a)
        self._update_project_refs(a)
        if self.logger:self.logger.info('Global asset relinked: %s',a.id)
        return a,state
    def _update_project_refs(self,a):
        path=str(a.resolved_path(self.repository.library_root))
        for u in self.repository.usages(a.id):
            m=self.media.get_by_id(u['projectMediaId'])
            if not m:continue
            m.project_path=path;m.original_path=path;m.file_size=a.file_size;m.status='ready';m.metadata_json={**m.metadata_json,'globalAssetFingerprint':a.fingerprint};self.media.update(m)
    def detect_change(self,asset_id:str)->str:
        a=self.repository.get(asset_id)
        if a is None:raise AssetNotFound('Asset could not be found.')
        p=a.resolved_path(self.repository.library_root)
        if not p.is_file():self.repository.set_status(a.id,'missing');return 'missing'
        s=p.stat();status='changed' if (a.source_mtime_ns and (s.st_mtime_ns!=a.source_mtime_ns or s.st_size!=a.file_size)) else 'ready';self.repository.set_status(a.id,status);return status

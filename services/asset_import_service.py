from __future__ import annotations
import hashlib, mimetypes, os, shutil
from dataclasses import dataclass,field
from pathlib import Path
from uuid import uuid4
from PIL import Image,ImageOps
from domain.asset import Asset,AssetStatus
from domain.asset_errors import AssetDuplicate,AssetImportFailed,AssetUnsupportedFormat
from services.asset_validation_service import AssetValidationService
from storage.repositories.asset_repository import AssetRepository

@dataclass(slots=True)
class AssetImportSummary:
    imported:list[Asset]=field(default_factory=list); skipped:list[str]=field(default_factory=list); failed:list[dict]=field(default_factory=list); cancelled:bool=False

class AssetImportService:
    LARGE_HASH_THRESHOLD=256*1024*1024; CHUNK=4*1024*1024
    def __init__(self,repository:AssetRepository,media_service,validation:AssetValidationService,logger=None):
        self.repository=repository; self.media=media_service; self.validation=validation; self.logger=logger
    def fingerprint(self,path:Path)->tuple[str,str]:
        p=Path(path); size=p.stat().st_size; h=hashlib.sha256()
        if size<=self.LARGE_HASH_THRESHOLD:
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(self.CHUNK),b''):h.update(chunk)
            return h.hexdigest(),'sha256'
        with p.open('rb') as f:
            h.update(f.read(self.CHUNK));
            if size>self.CHUNK: f.seek(max(0,size-self.CHUNK));h.update(f.read(self.CHUNK))
        h.update(str(size).encode()); return h.hexdigest(),'partial_sha256'
    def import_file(self,source:str|Path,*,managed:bool=True,subtype:str='general',duplicate_policy:str='use_existing',name:str='',metadata:dict|None=None)->Asset:
        try:p=Path(source).expanduser().resolve(strict=True)
        except OSError as exc: raise AssetImportFailed('The selected file could not be found.') from exc
        if not p.is_file(): raise AssetImportFailed('The selected path is not a file.')
        asset_type=self.media.classifier.classify(p)
        if not asset_type: raise AssetUnsupportedFormat(f'Unsupported media format: {p.suffix.lower() or "(none)"}')
        self.validation.validate_type(p,asset_type); self.validation.validate_subtype(asset_type,subtype)
        fp,kind=self.fingerprint(p); duplicates=self.repository.find_fingerprint(fp,p.stat().st_size)
        if duplicates and duplicate_policy=='use_existing': return duplicates[0]
        if duplicates and duplicate_policy=='cancel': raise AssetDuplicate('This media already exists in your Asset Library.')
        aid=str(uuid4()); ext=p.suffix.lower(); root=self.repository.library_root; destination=None; copied=False
        relative=f'{asset_type}/{aid}{ext}' if managed else ''
        target=(root/relative) if managed else p
        thumb_rel=f'thumbnails/{aid}.jpg'; thumb=root/thumb_rel
        try:
            if managed:
                target.parent.mkdir(parents=True,exist_ok=True); staging=target.with_name(target.name+'.partial'); staging.unlink(missing_ok=True)
                shutil.copy2(p,staging); os.replace(staging,target); copied=True
            if asset_type in {'video','audio'}:
                probe=self.media.prober.probe(target,expected_type=asset_type); image_meta={}
            else:
                with Image.open(target) as img:
                    oriented=ImageOps.exif_transpose(img); w,h=oriented.size
                class Probe: pass
                probe=Probe(); probe.duration_ms=None; probe.width=w; probe.height=h; probe.fps=None; probe.codec=''; probe.audio_codec=''; probe.sample_rate=None; probe.channels=None
                image_meta={}
            thumbnail=''
            if asset_type in {'video','image'}:
                thumb.parent.mkdir(parents=True,exist_ok=True)
                try:
                    generated=self.media.thumbnails.generate(asset_type,target,thumb,duration_ms=probe.duration_ms)
                    if generated: thumbnail=thumb_rel
                except Exception:
                    thumbnail=''
            stat=p.stat(); meta=dict(metadata or {}); meta.update(image_meta); meta.setdefault('importedFrom',str(p)); meta.setdefault('originalFilename',p.name)
            a=Asset(asset_id=aid,name=name.strip() or p.name,asset_type=asset_type,subtype=subtype,file_path='' if managed else str(p),managed=managed,relative_path=relative,thumbnail_path=thumbnail,duration_ms=probe.duration_ms,width=probe.width,height=probe.height,fps=probe.fps,video_codec=getattr(probe,'codec','') or '',audio_codec=getattr(probe,'audio_codec','') or '',sample_rate=getattr(probe,'sample_rate',None),channels=getattr(probe,'channels',None),file_size=target.stat().st_size,mime_type=mimetypes.guess_type(p.name)[0] or '',extension=ext,fingerprint=fp,fingerprint_kind=kind,source_mtime_ns=stat.st_mtime_ns,original_filename=p.name,status=AssetStatus.READY,metadata=meta)
            self.repository.create(a)
            if self.logger:self.logger.info('Global asset imported: %s type=%s managed=%s',a.id,a.type,a.managed)
            return a
        except Exception as exc:
            if copied and target is not None: target.unlink(missing_ok=True)
            thumb.unlink(missing_ok=True)
            if isinstance(exc,(AssetDuplicate,AssetUnsupportedFormat,AssetImportFailed)): raise
            raise AssetImportFailed(f'Could not import {p.name}.') from exc
    def import_many(self,sources:list[str|Path],*,managed:bool=True,subtype:str='general',duplicate_policy:str='use_existing',cancellation=None,progress=None)->AssetImportSummary:
        summary=AssetImportSummary(); total=len(sources)
        for i,src in enumerate(sources,1):
            if cancellation is not None and getattr(cancellation,'is_cancelled',False): summary.cancelled=True;break
            try:
                before=self.repository.count(); a=self.import_file(src,managed=managed,subtype=subtype,duplicate_policy=duplicate_policy); after=self.repository.count()
                if after==before: summary.skipped.append(str(src))
                else: summary.imported.append(a)
            except Exception as exc: summary.failed.append({'path':str(src),'reason':str(exc)})
            if progress: progress(i,total,Path(src).name)
        return summary
    def scan_folder(self,folder:str|Path,*,recursive:bool=False,limit:int=10000)->list[Path]:
        root=Path(folder).expanduser().resolve(strict=True); out=[]
        iterator=root.rglob('*') if recursive else root.glob('*')
        for p in iterator:
            if len(out)>=limit: break
            if p.is_symlink() or not p.is_file(): continue
            if self.media.classifier.classify(p): out.append(p)
        return out

from __future__ import annotations
from pathlib import Path
from domain.asset import Asset, SUBTYPES
from domain.asset_errors import AssetPathUnsafe, AssetRelinkMismatch, AssetUnsupportedFormat

VIDEO_EXT={'.mp4','.mov','.mkv','.avi','.webm','.m4v'}
AUDIO_EXT={'.mp3','.wav','.m4a','.aac','.flac','.ogg','.opus'}
IMAGE_EXT={'.jpg','.jpeg','.png','.webp','.bmp'}
EXTENSIONS={'video':VIDEO_EXT,'audio':AUDIO_EXT,'image':IMAGE_EXT}

class AssetValidationService:
    def validate_type(self,path:Path,asset_type:str)->None:
        ext=Path(path).suffix.lower()
        if asset_type not in EXTENSIONS or ext not in EXTENSIONS[asset_type]:
            raise AssetUnsupportedFormat(f'Unsupported {asset_type} format: {ext or "(none)"}')
    def validate_subtype(self,asset_type:str,subtype:str)->None:
        if asset_type not in SUBTYPES or subtype not in SUBTYPES[asset_type]: raise ValueError('Unsupported asset subtype.')
    def assert_managed_path(self,path:Path,root:Path)->Path:
        p=Path(path).expanduser().resolve(); r=Path(root).expanduser().resolve()
        try:p.relative_to(r)
        except ValueError as exc: raise AssetPathUnsafe('Managed asset path is outside the Asset Library.') from exc
        return p
    def relink_state(self,asset:Asset,new_type:str,new_size:int,new_fingerprint:str='',duration_ms:int|None=None,width:int|None=None,height:int|None=None)->dict:
        if new_type!=asset.type: return {'state':'manual_review','compatible':False,'message':'Media type differs from the original asset.'}
        if asset.fingerprint and new_fingerprint and asset.fingerprint==new_fingerprint and int(asset.file_size)==int(new_size):
            return {'state':'exact_match','compatible':True,'message':'Exact Match'}
        dimensions_ok=(asset.width is None or width is None or asset.width==width) and (asset.height is None or height is None or asset.height==height)
        duration_ok=asset.duration_ms is None or duration_ms is None or abs(asset.duration_ms-duration_ms)<=max(1000,int((asset.duration_ms or 0)*.05))
        size_ratio=(min(asset.file_size,new_size)/max(asset.file_size,new_size)) if asset.file_size and new_size else 1.0
        if dimensions_ok and duration_ok and size_ratio>=.90: return {'state':'likely_match','compatible':True,'message':'Likely Match'}
        return {'state':'manual_review','compatible':False,'message':'Manual Review'}
    def require_relink_compatible(self,*args,**kwargs)->dict:
        result=self.relink_state(*args,**kwargs)
        if not result['compatible']: raise AssetRelinkMismatch(result['message'])
        return result

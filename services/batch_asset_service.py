from __future__ import annotations
import hashlib,random
from domain.batch_errors import BatchAssetMissing,BatchMappingError

class BatchAssetService:
    def __init__(self,repository):self.repository=repository
    def by_id(self,asset_id:str):
        asset=self.repository.get(str(asset_id))
        if asset is None:raise BatchAssetMissing(f'Asset ID not found: {asset_id}')
        if getattr(asset,'status_code',getattr(asset,'status',''))!='ready':raise BatchAssetMissing(f'Asset is not ready: {asset_id}')
        return asset
    def by_name(self,name:str):
        matches=[a for a in self.repository.list_all() if str(a.name).casefold()==str(name).casefold()]
        if not matches:raise BatchAssetMissing(f'Asset name not found: {name}')
        if len(matches)>1:raise BatchMappingError(f'Asset name is ambiguous: {name}')
        return self.by_id(matches[0].id)
    def collection(self,collection_id:str)->list:
        ids=self.repository.assets_in_collection(collection_id);items=[a for a in self.repository.list_all() if a.id in ids and getattr(a,'status_code',getattr(a,'status',''))=='ready']
        items.sort(key=lambda a:(str(a.name).casefold(),a.id))
        if not items:raise BatchAssetMissing('Asset collection has no ready items.')
        return items
    def choose(self,collection_id:str,*,strategy:str,row_index:int,item_key:str,seed:int)->object:
        items=self.collection(collection_id)
        if strategy=='first_available':return items[0]
        if strategy=='round_robin':return items[int(row_index)%len(items)]
        if strategy=='seeded_random':
            material=f'{seed}:{item_key}:{collection_id}'.encode('utf-8');derived=int.from_bytes(hashlib.sha256(material).digest()[:8],'big');return items[random.Random(derived).randrange(len(items))]
        raise BatchMappingError(f'Unsupported Asset collection strategy: {strategy}')
    def resolve_value(self,value,*,allow_name:bool=True):
        text=str(value or '')
        if not text:raise BatchAssetMissing('Asset assignment is empty.')
        try:return self.by_id(text)
        except BatchAssetMissing:
            if allow_name:return self.by_name(text)
            raise

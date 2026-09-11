from __future__ import annotations
import unicodedata
from domain.asset import Asset
from storage.repositories.asset_repository import AssetRepository

def norm(value:str)->str: return unicodedata.normalize('NFKC',str(value)).casefold()

class AssetSearchService:
    def __init__(self,repository:AssetRepository): self.repository=repository
    def search(self,*,query:str='',filter_id:str='all',sort:str='recent_added',collection_id:str='')->list[Asset]:
        items=self.repository.list_all(); q=norm(query.strip()); collection_ids=self.repository.assets_in_collection(collection_id) if collection_id else None
        out=[]
        for a in items:
            if collection_ids is not None and a.id not in collection_ids: continue
            tags=self.repository.tags(a.id); cols=self.repository.asset_collections(a.id)
            collection_names=[x['name'] for x in self.repository.collections() if x['id'] in cols]
            hay=' '.join([a.name,a.subtype,a.notes,*tags,*collection_names])
            if q and q not in norm(hay): continue
            if not self._matches(a,filter_id): continue
            out.append(a)
        if sort=='name': out.sort(key=lambda x:norm(x.name))
        elif sort=='recent_used': out.sort(key=lambda x:(x.last_used_at,x.created_at),reverse=True)
        elif sort=='duration': out.sort(key=lambda x:(x.duration_ms or -1),reverse=True)
        elif sort=='file_size': out.sort(key=lambda x:x.file_size,reverse=True)
        else: out.sort(key=lambda x:x.created_at,reverse=True)
        return out
    def _matches(self,a:Asset,f:str)->bool:
        f=(f or 'all').lower().replace('_','-')
        if f=='all': return True
        if f in {'video','image','audio'}: return a.type==f
        if f=='favorites': return a.favorite
        if f=='missing': return a.status_code=='missing'
        if f=='unused': return self.repository.usage_count(a.id)==0
        if f in {'green-screen','green_screen'}: return a.subtype=='green_screen' or bool(a.metadata.get('chromaReady'))
        aliases={'presenter':'presenter','reporter':'reporter','broll':'broll','b-roll':'broll','music':'music','sfx':'sfx','character':'character','background':'background','logo':'logo','overlay':'overlay_video'}
        return a.subtype==aliases.get(f,f)

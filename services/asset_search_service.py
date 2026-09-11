from __future__ import annotations
import unicodedata
from domain.asset import Asset
from storage.repositories.asset_repository import AssetRepository

def norm(value:str)->str:return unicodedata.normalize('NFKC',str(value)).casefold()

class AssetSearchService:
    def __init__(self,repository:AssetRepository):self.repository=repository

    def search(self,*,query:str='',filter_id:str='all',sort:str='recent_added',collection_id:str='')->list[Asset]:
        return [row['asset'] for row in self.search_rows(query=query,filter_id=filter_id,sort=sort,collection_id=collection_id)]

    def search_rows(self,*,query:str='',filter_id:str='all',sort:str='recent_added',collection_id:str='',limit:int=0,offset:int=0)->list[dict]:
        q=norm(query.strip());rows=self.repository.list_with_metadata();out=[]
        for row in rows:
            a=row['asset'];collections=row['collections'];collection_ids={x['id'] for x in collections}
            if collection_id and collection_id not in collection_ids:continue
            hay=' '.join([a.name,a.subtype,a.notes,*row['tags'],*[x['name'] for x in collections]])
            if q and q not in norm(hay):continue
            if not self._matches(a,filter_id,row['usageCount']):continue
            out.append(row)
        if sort=='name':out.sort(key=lambda x:norm(x['asset'].name))
        elif sort=='recent_used':out.sort(key=lambda x:(x['asset'].last_used_at,x['asset'].created_at),reverse=True)
        elif sort=='duration':out.sort(key=lambda x:(x['asset'].duration_ms or -1),reverse=True)
        elif sort=='file_size':out.sort(key=lambda x:x['asset'].file_size,reverse=True)
        else:out.sort(key=lambda x:x['asset'].created_at,reverse=True)
        if offset or limit:
            start=max(0,int(offset));end=start+int(limit) if limit>0 else None;out=out[start:end]
        return out

    def count(self,**kwargs)->int:
        kwargs=dict(kwargs);kwargs.pop('limit',None);kwargs.pop('offset',None)
        return len(self.search_rows(**kwargs))

    def _matches(self,a:Asset,f:str,usage_count:int=0)->bool:
        f=(f or 'all').lower().replace('_','-')
        if f=='all':return True
        if f in {'video','image','audio'}:return a.type==f
        if f=='favorites':return a.favorite
        if f=='missing':return a.status_code=='missing'
        if f=='unused':return int(usage_count)==0
        if f in {'green-screen','green_screen'}:return a.subtype=='green_screen' or bool(a.metadata.get('chromaReady'))
        aliases={'presenter':'presenter','reporter':'reporter','broll':'broll','b-roll':'broll','music':'music','sfx':'sfx','character':'character','background':'background','logo':'logo','overlay':'overlay_video'}
        return a.subtype==aliases.get(f,f)

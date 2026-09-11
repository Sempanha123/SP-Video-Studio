from __future__ import annotations
import hashlib,itertools,json
from typing import Any,Mapping
from domain.batch_variant import BatchVariantConfig
from domain.batch_errors import BatchVariantError

class BatchVariantService:
    WARNING_THRESHOLD=1000
    CONFIRM_THRESHOLD=5000
    def dimensions(self,config:BatchVariantConfig)->dict[str,list[str]]:
        raw=config.normalized();return {'language':raw['languages'],'voice':raw['voices'],'platform':raw['platforms'],'aspect_ratio':raw['aspectRatios'],'template_option':raw['templateOptions']}
    def expansion_count(self,row_count:int,config:BatchVariantConfig)->int:
        n=max(0,int(row_count))
        for values in self.dimensions(config).values():n*=max(1,len(values))
        return n
    def expand(self,rows:list[Mapping[str,Any]],config:BatchVariantConfig)->list[dict[str,Any]]:
        dims=self.dimensions(config);keys=list(dims);combos=list(itertools.product(*(dims[k] for k in keys)))
        out=[]
        for row_index,row in enumerate(rows):
            for values in combos:
                variant=dict(zip(keys,values));variant['source_language']=config.source_language or str(row.get('source_language') or row.get('language') or '')
                key=self.item_key(row_index,variant);out.append({'rowIndex':row_index,'input':dict(row),'variant':variant,'itemKey':key,'variantKey':self.variant_key(variant)})
        return out
    def item_key(self,row_index:int,variant:Mapping[str,Any])->str:
        canonical=json.dumps(dict(variant),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8');digest=hashlib.sha256(canonical).hexdigest()[:10]
        lang=str(variant.get('language') or 'source');platform=str(variant.get('platform') or 'default');return f'r{row_index+1:05d}-{lang}-{platform}-{digest}'
    def variant_key(self,variant:Mapping[str,Any])->str:
        return '|'.join(f'{k}={variant.get(k) or "default"}' for k in ('language','voice','platform','aspect_ratio','template_option'))
    def preview(self,row_count:int,config:BatchVariantConfig)->dict[str,Any]:
        count=self.expansion_count(row_count,config);return {'itemCount':count,'warning':count>=self.WARNING_THRESHOLD,'confirmationRequired':count>=self.CONFIRM_THRESHOLD}

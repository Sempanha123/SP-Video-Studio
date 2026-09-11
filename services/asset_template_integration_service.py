from __future__ import annotations
class AssetTemplateIntegrationService:
    def __init__(self,usage):self.usage=usage
    def resolve(self,project_id:str,value):
        if isinstance(value,dict) and value.get('globalAssetId'):return self.usage.template_resolution(project_id,str(value['globalAssetId']))
        if isinstance(value,str) and value.startswith('asset:'):return self.usage.template_resolution(project_id,value.split(':',1)[1])
        return value
    def resolve_map(self,project_id:str,resolutions:dict):return {k:self.resolve(project_id,v) for k,v in dict(resolutions or {}).items()}

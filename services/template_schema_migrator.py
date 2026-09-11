from __future__ import annotations
from copy import deepcopy
from domain.template_manifest import TEMPLATE_SCHEMA_VERSION
from domain.template_errors import TemplateVersionTooNew


class TemplateSchemaMigrator:
    current_version=TEMPLATE_SCHEMA_VERSION

    def migrate(self, raw: dict) -> dict:
        data=deepcopy(raw); version=int(data.get("schemaVersion",data.get("schema_version",1)) or 1)
        if version>self.current_version: raise TemplateVersionTooNew()
        while version<self.current_version:
            migration=getattr(self,f"_v{version}_to_v{version+1}",None)
            if migration is None: raise ValueError(f"No template schema migration from {version}.")
            data=migration(data); version+=1
        data["schemaVersion"]=self.current_version; return data

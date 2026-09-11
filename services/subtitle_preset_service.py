from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from domain.subtitle_preset import SubtitlePreset
from domain.subtitle_style import SubtitleStyle
from storage.repositories.subtitle_repository import SubtitleRepository


class SubtitlePresetService:
    def __init__(self, repository: SubtitleRepository, registry_path: Path | None = None) -> None:
        self.repository=repository
        self.registry_path=registry_path or Path(__file__).resolve().parents[1]/"resources"/"subtitles"/"presets.json"
        self._builtin=self._load_builtin()

    def _load_builtin(self) -> dict[str, SubtitlePreset]:
        data=json.loads(self.registry_path.read_text(encoding="utf-8"))
        version=int(data.get("subtitle_registry_version",1)); result={}
        for item in data.get("presets",[]):
            preset=SubtitlePreset(str(item["id"]),str(item["name"]),str(item.get("description","")),dict(item.get("style",{})),True,version)
            result[preset.preset_id]=preset
        return result

    def list_presets(self) -> list[dict[str,object]]:
        result=[{"id":p.preset_id,"name":p.name,"description":p.description,"style":dict(p.style),"builtin":True} for p in self._builtin.values()]
        result.extend(self.repository.user_presets())
        return result

    def style_from_preset(self, project_id: str, preset_id: str) -> SubtitleStyle:
        if preset_id in self._builtin:
            item=self._builtin[preset_id]; values=dict(item.style); metadata=dict(values.pop("metadata",{})); return SubtitleStyle(project_id=project_id,name=item.name,metadata={"presetId":preset_id,**metadata},**values)
        item=next((p for p in self.repository.user_presets() if p["id"]==preset_id),None)
        if not item: raise KeyError("Subtitle preset not found.")
        values=dict(item["style"]); values.pop("id",None); values.pop("project_id",None); values.pop("created_at",None); values.pop("updated_at",None); values.pop("style_id",None)
        metadata=dict(values.pop("metadata",{})); return SubtitleStyle(project_id=project_id,name=str(item["name"]),metadata={"presetId":preset_id,**metadata},**values)

    def save_user_preset(self,name:str,style:SubtitleStyle)->str:
        clean=name.strip()
        if not clean: raise ValueError("Preset name is required.")
        preset_id=f"user-{uuid4()}"
        data=style.to_dict(); [data.pop(key,None) for key in ("id","project_id","name","created_at","updated_at")]
        self.repository.save_user_preset(preset_id,clean,data); return preset_id

    def delete_user_preset(self,preset_id:str)->None:
        if preset_id in self._builtin: raise ValueError("Built-in subtitle presets cannot be deleted.")
        self.repository.delete_user_preset(preset_id)

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from domain.export_preset import EXPORT_PRESET_SCHEMA_VERSION, ExportPreset
from domain.export_profile import ExportProfile
from domain.export_request import ExportRequest
from domain.project import utc_now_iso
from storage.repositories.export_preset_repository import ExportPresetRepository


class ExportPresetNotFound(KeyError):
    pass


class ExportPresetService:
    def __init__(self, repository: ExportPresetRepository, registry_path: Path | None = None) -> None:
        self.repository=repository
        self.registry_path=registry_path or Path(__file__).resolve().parents[1]/"resources"/"export"/"presets.json"
        self._builtins=self._load_builtins()

    def _load_builtins(self) -> dict[str,ExportPreset]:
        data=json.loads(self.registry_path.read_text(encoding="utf-8"))
        if int(data.get("schema_version",0))!=EXPORT_PRESET_SCHEMA_VERSION:
            raise ValueError("Unsupported export preset registry version.")
        result={}
        for raw in data.get("presets",[]):
            preset=ExportPreset.from_dict(raw,builtin=True); result[preset.id]=preset
        if len(result)!=len(data.get("presets",[])):
            raise ValueError("Export preset IDs must be unique.")
        return result

    def list_all(self) -> list[ExportPreset]:
        return list(self._builtins.values())+self.repository.list_all()

    def get(self,preset_id:str)->ExportPreset:
        if preset_id in self._builtins:return self._builtins[preset_id]
        item=self.repository.get(preset_id)
        if item is None: raise ExportPresetNotFound("Export preset could not be found.")
        return item

    def create_custom(self,name:str,description:str,request:ExportRequest)->ExportPreset:
        item=ExportPreset(name=name.strip(),platform="custom",description=description.strip(),width=request.width,height=request.height,aspect_ratio=self.aspect_ratio(request.width,request.height),fps=request.fps,quality_profile=request.quality,subtitle_mode=request.subtitle_mode,metadata={"encoderPreference":request.encoder,"audioEnabled":request.audio_enabled,"audioQuality":request.audio_quality,"fitMode":request.fit_mode},builtin=False)
        item.validate(); return self.repository.create(item)

    def duplicate(self,preset_id:str,name:str|None=None)->ExportPreset:
        src=self.get(preset_id); clone=ExportPreset.from_dict(src.to_dict(),builtin=False); clone.preset_id=str(uuid4()); clone.name=(name or f"{src.name} Copy").strip(); clone.builtin=False; return self.repository.create(clone)

    def rename(self,preset_id:str,name:str)->ExportPreset:
        item=self.get(preset_id)
        if item.builtin: raise ValueError("Builtin export presets cannot be renamed.")
        item.name=name.strip(); return self.repository.update(item)

    def delete(self,preset_id:str)->None:
        if preset_id in self._builtins: raise ValueError("Builtin export presets cannot be deleted.")
        self.repository.delete(preset_id)

    def profile(self,project_id:str)->ExportProfile|None:return self.repository.get_profile(project_id)
    def save_profile(self,project_id:str,request:ExportRequest)->None:self.repository.save_profile(ExportProfile(project_id,request.preset_id,request.to_dict(),utc_now_iso()))

    @staticmethod
    def aspect_ratio(width:int,height:int)->str:
        if width==height:return "1:1"
        ratio=width/height
        return "9:16" if ratio<.8 else "16:9"

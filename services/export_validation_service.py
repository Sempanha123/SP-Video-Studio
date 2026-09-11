from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from domain.export_request import ExportRequest
from services.export_filename_service import ExportFilenameService
from services.render_validation_service import RenderIssue


@dataclass(frozen=True, slots=True)
class ExportSummary:
    expected_duration_ms: int
    estimated_size_bytes: int
    output_path: str
    managed_output: bool

    def to_dict(self)->dict:
        return {"durationMs":self.expected_duration_ms,"estimatedSizeBytes":self.estimated_size_bytes,"outputPath":self.output_path,"managedOutput":self.managed_output}


class ExportValidationService:
    def __init__(self, filename_service:ExportFilenameService) -> None:self.filename_service=filename_service

    def validate_folder(self,folder:str|Path,*,create:bool=True)->Path:
        target=Path(folder).expanduser()
        if target.exists() and not target.is_dir(): raise ValueError("The selected export path is not a folder.")
        if not target.exists():
            if not create: raise ValueError("The selected export folder does not exist.")
            target.mkdir(parents=True,exist_ok=True)
        if not os.access(target,os.W_OK): raise ValueError("The selected export folder cannot be written to.")
        probe=target/".sp-video-studio-export-test"
        try: probe.write_text("ok",encoding="utf-8"); probe.unlink(missing_ok=True)
        except OSError as exc: raise ValueError("The selected export folder cannot be written to.") from exc
        return target.resolve()

    def export_issues(self,request:ExportRequest,*,project_aspect_ratio:str,preset_max_duration_ms:int|None,expected_duration_ms:int)->list[RenderIssue]:
        request.validate(); issues=[]
        actual=self.aspect_ratio(request.width,request.height)
        if project_aspect_ratio and actual!=project_aspect_ratio:
            issues.append(RenderIssue("warning","export_aspect_mismatch","Export aspect ratio differs from the project. Fit/Fill will be used according to your export setting."))
        if preset_max_duration_ms and expected_duration_ms>preset_max_duration_ms:
            issues.append(RenderIssue("warning","preset_duration","This video is longer than this preset is typically used for."))
        return issues

    @staticmethod
    def aspect_ratio(width:int,height:int)->str:
        if width==height:return "1:1"
        return "9:16" if width/height<.8 else "16:9"

    @staticmethod
    def estimate_size(duration_ms:int,width:int,height:int,quality:str,audio_enabled:bool=True,audio_quality:str="high")->int:
        # A deliberately approximate display estimate; renderer remains authoritative.
        megapixels=max(.1,(width*height)/1_000_000)
        base_mbps={"fast":3.2,"balanced":5.5,"high":9.0}.get(quality,5.5)*max(.55,min(2.2,megapixels/2.0736))
        audio_mbps=0 if not audio_enabled else (.16 if audio_quality=="standard" else .224)
        seconds=max(0,duration_ms)/1000
        return int((base_mbps+audio_mbps)*1_000_000/8*seconds)

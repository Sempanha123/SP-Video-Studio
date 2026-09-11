from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class RenderJobStatus(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    PREPARING = "preparing"
    RENDERING = "rendering"
    FINALIZING = "finalizing"
    VALIDATING_OUTPUT = "validating_output"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class RenderJob:
    project_id: str
    preset: str = ""
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: str | RenderJobStatus = RenderJobStatus.QUEUED
    output_path: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    progress: float = 0.0
    expected_duration_ms: int = 0
    actual_duration_ms: int = 0
    settings: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    @property
    def id(self) -> str: return self.job_id
    @property
    def status_code(self) -> str: return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"projectId":self.project_id,"presetId":self.preset,"status":self.status_code,"outputPath":self.output_path or "","startedAt":self.started_at or "","completedAt":self.completed_at or "","progress":self.progress,"expectedDurationMs":self.expected_duration_ms,"actualDurationMs":self.actual_duration_ms,"settings":dict(self.settings),"errorMessage":self.error_message,"metadata":dict(self.metadata),"createdAt":self.created_at}

    @classmethod
    def from_record(cls, r: Mapping[str, Any]) -> "RenderJob":
        def load(name:str)->dict[str,Any]:
            try: value=json.loads(r[name] or "{}")
            except Exception: value={}
            return value if isinstance(value,dict) else {}
        return cls(job_id=str(r["id"]),project_id=str(r["project_id"]),preset=str(r["preset_id"] or ""),status=str(r["status"]),output_path=str(r["output_path"] or "") or None,started_at=str(r["started_at"]) if r["started_at"] else None,completed_at=str(r["completed_at"]) if r["completed_at"] else None,progress=float(r["progress"] or 0),expected_duration_ms=int(r["expected_duration_ms"] or 0),actual_duration_ms=int(r["actual_duration_ms"] or 0),settings=load("settings_json"),error_message=str(r["error_message"] or ""),metadata=load("metadata_json"),created_at=str(r["created_at"]))

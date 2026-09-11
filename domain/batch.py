from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso


class BatchStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    CANCELLED = "cancelled"
    FAILED = "failed"


_ALLOWED_TRANSITIONS = {
    BatchStatus.DRAFT.value: {BatchStatus.READY.value, BatchStatus.CANCELLED.value},
    BatchStatus.READY.value: {BatchStatus.RUNNING.value, BatchStatus.CANCELLED.value},
    BatchStatus.RUNNING.value: {BatchStatus.PAUSED.value, BatchStatus.COMPLETED.value, BatchStatus.COMPLETED_WITH_ERRORS.value, BatchStatus.CANCELLED.value, BatchStatus.FAILED.value},
    BatchStatus.PAUSED.value: {BatchStatus.RUNNING.value, BatchStatus.CANCELLED.value, BatchStatus.FAILED.value},
    BatchStatus.COMPLETED.value: set(), BatchStatus.COMPLETED_WITH_ERRORS.value: set(),
    BatchStatus.CANCELLED.value: set(), BatchStatus.FAILED.value: {BatchStatus.READY.value},
}


@dataclass(slots=True)
class Batch:
    name: str
    template_id: str
    output_directory: str
    input_source_type: str = "manual"
    input_source_path: str = ""
    status: str | BatchStatus = BatchStatus.DRAFT
    settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    template_snapshot: dict[str, Any] = field(default_factory=dict)
    input_snapshot: list[dict[str, Any]] = field(default_factory=list)
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    cancelled_items: int = 0
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    started_at: str = ""
    completed_at: str = ""
    batch_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str: return self.batch_id
    @property
    def status_code(self) -> str: return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.id or not self.name.strip(): raise ValueError("Batch name and ID are required.")
        if not self.template_id.strip(): raise ValueError("Batch template is required.")
        if not self.output_directory.strip(): raise ValueError("Batch output directory is required.")
        if self.status_code not in {x.value for x in BatchStatus}: raise ValueError("Unsupported Batch status.")
        for value in (self.total_items,self.completed_items,self.failed_items,self.cancelled_items):
            if int(value)<0: raise ValueError("Batch counters cannot be negative.")

    def transition(self, target: str | BatchStatus, *, force_reset: bool = False) -> None:
        target_code = target.value if isinstance(target,StrEnum) else str(target)
        if target_code == self.status_code: return
        if target_code not in {x.value for x in BatchStatus}: raise ValueError("Unsupported Batch status.")
        if not force_reset and target_code not in _ALLOWED_TRANSITIONS.get(self.status_code,set()):
            raise ValueError(f"Invalid Batch transition: {self.status_code} -> {target_code}")
        self.status=target_code; self.updated_at=utc_now_iso()
        if target_code==BatchStatus.RUNNING.value and not self.started_at:self.started_at=self.updated_at
        if target_code in {BatchStatus.COMPLETED.value,BatchStatus.COMPLETED_WITH_ERRORS.value,BatchStatus.CANCELLED.value}:self.completed_at=self.updated_at

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"name":self.name,"templateId":self.template_id,"status":self.status_code,"createdAt":self.created_at,"updatedAt":self.updated_at,"startedAt":self.started_at,"completedAt":self.completed_at,"inputSourceType":self.input_source_type,"inputSourcePath":self.input_source_path,"settings":dict(self.settings),"outputDirectory":self.output_directory,"totalItems":self.total_items,"completedItems":self.completed_items,"failedItems":self.failed_items,"cancelledItems":self.cancelled_items,"metadata":dict(self.metadata),"templateSnapshot":dict(self.template_snapshot),"inputSnapshot":[dict(x) for x in self.input_snapshot]}

    @classmethod
    def from_record(cls, r: Mapping[str,Any]) -> "Batch":
        import json
        def j(key, fallback):
            try:return json.loads(str(r[key] or ""))
            except Exception:return fallback
        return cls(batch_id=str(r["id"]),name=str(r["name"]),template_id=str(r["template_id"]),status=str(r["status"]),created_at=str(r["created_at"]),updated_at=str(r["updated_at"]),started_at=str(r["started_at"] or ""),completed_at=str(r["completed_at"] or ""),input_source_type=str(r["input_source_type"]),input_source_path=str(r["input_source_path"] or ""),settings=j("settings_json",{}),output_directory=str(r["output_directory"]),total_items=int(r["total_items"]),completed_items=int(r["completed_items"]),failed_items=int(r["failed_items"]),cancelled_items=int(r["cancelled_items"]),metadata=j("metadata_json",{}),template_snapshot=j("template_snapshot_json",{}),input_snapshot=j("input_snapshot_json",[]))

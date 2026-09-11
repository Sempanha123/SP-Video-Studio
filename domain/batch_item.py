from __future__ import annotations
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any,Mapping
from uuid import uuid4
from domain.project import utc_now_iso
from domain.batch_stage import BatchStage

class BatchItemStatus(StrEnum):
    PENDING="pending"; VALIDATING="validating"; PROJECT_SETUP="project_setup"; TRANSLATION="translation"; TTS="tts"; SUBTITLES="subtitles"; SCENE_SETUP="scene_setup"; RENDERING="rendering"; EXPORTING="exporting"; COMPLETED="completed"; FAILED="failed"; PAUSED="paused"; CANCELLED="cancelled"; SKIPPED="skipped"; NEEDS_REVIEW="needs_review"; INTERRUPTED="interrupted"; OUTPUT_MISSING="output_missing"

TERMINAL_ITEM_STATUSES={BatchItemStatus.COMPLETED.value,BatchItemStatus.CANCELLED.value,BatchItemStatus.SKIPPED.value}

@dataclass(slots=True)
class BatchItem:
    batch_id:str; row_index:int; item_key:str; variant_key:str; input_data:dict[str,Any]
    status:str|BatchItemStatus=BatchItemStatus.PENDING; current_stage:str|BatchStage=BatchStage.VALIDATE_INPUT
    progress:float=0.0; project_id:str=""; output_path:str=""; error_code:str=""; error_message:str=""; attempt_count:int=0
    resolved_data:dict[str,Any]=field(default_factory=dict); metadata:dict[str,Any]=field(default_factory=dict); fingerprint:str=""
    created_at:str=field(default_factory=utc_now_iso); updated_at:str=field(default_factory=utc_now_iso); started_at:str=""; completed_at:str=""; item_id:str=field(default_factory=lambda:str(uuid4()))
    @property
    def id(self):return self.item_id
    @property
    def status_code(self):return self.status.value if isinstance(self.status,StrEnum) else str(self.status)
    @property
    def stage_code(self):return self.current_stage.value if isinstance(self.current_stage,StrEnum) else str(self.current_stage)
    def validate(self):
        if not self.id or not self.batch_id or not self.item_key:raise ValueError("Batch item identity is required.")
        if self.row_index<0:raise ValueError("Batch row index cannot be negative.")
        if self.status_code not in {x.value for x in BatchItemStatus}:raise ValueError("Unsupported Batch item status.")
        if not 0<=float(self.progress)<=1:raise ValueError("Batch item progress must be between 0 and 1.")
    def set_status(self,status:str|BatchItemStatus):
        value=status.value if isinstance(status,StrEnum) else str(status)
        if self.status_code==BatchItemStatus.COMPLETED.value and value not in {BatchItemStatus.OUTPUT_MISSING.value}:raise ValueError("Completed Batch item must be reset before reprocessing.")
        if value not in {x.value for x in BatchItemStatus}:raise ValueError("Unsupported Batch item status.")
        self.status=value;self.updated_at=utc_now_iso()
        if value not in {BatchItemStatus.PENDING.value,BatchItemStatus.PAUSED.value} and not self.started_at:self.started_at=self.updated_at
        if value in TERMINAL_ITEM_STATUSES:self.completed_at=self.updated_at
    def to_dict(self):
        return {"id":self.id,"batchId":self.batch_id,"rowIndex":self.row_index,"itemKey":self.item_key,"status":self.status_code,"currentStage":self.stage_code,"progress":self.progress,"projectId":self.project_id,"variantKey":self.variant_key,"outputPath":self.output_path,"errorCode":self.error_code,"errorMessage":self.error_message,"attemptCount":self.attempt_count,"createdAt":self.created_at,"updatedAt":self.updated_at,"startedAt":self.started_at,"completedAt":self.completed_at,"inputData":dict(self.input_data),"resolvedData":dict(self.resolved_data),"metadata":dict(self.metadata),"fingerprint":self.fingerprint}
    @classmethod
    def from_record(cls,r:Mapping[str,Any]):
        import json
        def j(k):
            try:return json.loads(str(r[k] or "{}"))
            except Exception:return {}
        return cls(item_id=str(r["id"]),batch_id=str(r["batch_id"]),row_index=int(r["row_index"]),item_key=str(r["item_key"]),status=str(r["status"]),current_stage=str(r["current_stage"]),progress=float(r["progress"] or 0),project_id=str(r["project_id"] or ""),variant_key=str(r["variant_key"] or ""),output_path=str(r["output_path"] or ""),error_code=str(r["error_code"] or ""),error_message=str(r["error_message"] or ""),attempt_count=int(r["attempt_count"] or 0),created_at=str(r["created_at"]),updated_at=str(r["updated_at"]),started_at=str(r["started_at"] or ""),completed_at=str(r["completed_at"] or ""),input_data=j("input_data_json"),resolved_data=j("resolved_data_json"),metadata=j("metadata_json"),fingerprint=str(r["fingerprint"] or ""))

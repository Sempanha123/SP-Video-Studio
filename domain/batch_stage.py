from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class BatchStage(StrEnum):
    VALIDATE_INPUT = "validate_input"
    RESOLVE_TEMPLATE = "resolve_template"
    CREATE_PROJECT = "create_project"
    RESOLVE_LANGUAGE = "resolve_language"
    RESOLVE_ASSETS = "resolve_assets"
    RESOLVE_SPEAKERS = "resolve_speakers"
    PREPARE_SCRIPT = "prepare_script"
    TRANSLATE = "translate"
    GENERATE_TTS = "generate_tts"
    GENERATE_SUBTITLES = "generate_subtitles"
    PREPARE_SCENES = "prepare_scenes"
    RENDER = "render"
    EXPORT = "export"
    FINALIZE = "finalize"


STAGE_ORDER: tuple[BatchStage, ...] = tuple(BatchStage)
STAGE_INDEX = {stage.value: index for index, stage in enumerate(STAGE_ORDER)}
STAGE_WEIGHTS: dict[str, float] = {
    BatchStage.VALIDATE_INPUT.value: 0.02,
    BatchStage.RESOLVE_TEMPLATE.value: 0.02,
    BatchStage.CREATE_PROJECT.value: 0.04,
    BatchStage.RESOLVE_LANGUAGE.value: 0.02,
    BatchStage.RESOLVE_ASSETS.value: 0.02,
    BatchStage.RESOLVE_SPEAKERS.value: 0.02,
    BatchStage.PREPARE_SCRIPT.value: 0.04,
    BatchStage.TRANSLATE.value: 0.12,
    BatchStage.GENERATE_TTS.value: 0.20,
    BatchStage.GENERATE_SUBTITLES.value: 0.05,
    BatchStage.PREPARE_SCENES.value: 0.05,
    BatchStage.RENDER.value: 0.34,
    BatchStage.EXPORT.value: 0.05,
    BatchStage.FINALIZE.value: 0.01,
}


class BatchStageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    INVALIDATED = "invalidated"


@dataclass(slots=True)
class BatchStageState:
    item_id: str
    stage: str | BatchStage
    status: str | BatchStageStatus = BatchStageStatus.PENDING
    progress: float = 0.0
    started_at: str = ""
    completed_at: str = ""
    fingerprint: str = ""
    error_code: str = ""
    error_message: str = ""
    output_reference: str = ""
    attempt_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def stage_code(self) -> str:
        return self.stage.value if isinstance(self.stage, StrEnum) else str(self.stage)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if self.stage_code not in STAGE_INDEX:
            raise ValueError("Unknown Batch stage.")
        if self.status_code not in {x.value for x in BatchStageStatus}:
            raise ValueError("Unknown Batch stage status.")
        if not 0.0 <= float(self.progress) <= 1.0:
            raise ValueError("Stage progress must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "itemId": self.item_id,
            "stage": self.stage_code,
            "status": self.status_code,
            "progress": float(self.progress),
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "fingerprint": self.fingerprint,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "outputReference": self.output_reference,
            "attemptCount": int(self.attempt_count),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "BatchStageState":
        import json
        try:
            metadata = json.loads(str(record["metadata_json"] or "{}"))
        except Exception:
            metadata = {}
        return cls(
            item_id=str(record["item_id"]), stage=str(record["stage"]), status=str(record["status"]),
            progress=float(record["progress"] or 0), started_at=str(record["started_at"] or ""),
            completed_at=str(record["completed_at"] or ""), fingerprint=str(record["fingerprint"] or ""),
            error_code=str(record["error_code"] or ""), error_message=str(record["error_message"] or ""),
            output_reference=str(record["output_reference"] or ""), attempt_count=int(record["attempt_count"] or 0),
            metadata=metadata if isinstance(metadata, dict) else {},
        )

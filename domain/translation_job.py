from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class TranslationJobState(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    LOADING_MODEL = "loading_model"
    TRANSLATING = "translating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TranslationJob:
    translation_id: str
    project_id: str
    state: str | TranslationJobState = TranslationJobState.QUEUED
    completed_segments: int = 0
    total_segments: int = 0
    job_id: str = field(default_factory=lambda: str(uuid4()))

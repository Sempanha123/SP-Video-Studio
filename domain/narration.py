from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class NarrationJobState(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    LOADING_MODEL = "loading_model"
    GENERATING = "generating"
    COMBINING = "combining"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TTSChunk:
    text: str
    order: int
    section_id: str | None = None
    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NarrationProgress:
    state: str | NarrationJobState
    current: int = 0
    total: int = 0
    message: str = ""

    @property
    def ratio(self) -> float:
        if self.total <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current / self.total))

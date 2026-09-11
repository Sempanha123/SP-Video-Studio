from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class JobState(StrEnum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class JobInfo:
    name: str
    state: JobState = JobState.QUEUED
    progress: float = 0.0
    job_id: str = field(default_factory=lambda: str(uuid4()))
    error: str | None = None


class WorkerTask(ABC):
    @abstractmethod
    def run(self) -> object:
        raise NotImplementedError

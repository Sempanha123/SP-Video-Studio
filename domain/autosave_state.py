from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import time
from typing import Iterable


class AutosaveStatus(StrEnum):
    CLEAN = "clean"
    DIRTY = "dirty"
    SCHEDULED = "scheduled"
    SAVING = "saving"
    SAVED = "saved"
    FAILED = "failed"


@dataclass(slots=True)
class ProjectAutosaveState:
    project_id: str
    project_revision: int = 0
    saved_revision: int = 0
    status: str | AutosaveStatus = AutosaveStatus.CLEAN
    last_modified_at: float = 0.0
    last_saved_at: float = 0.0
    scheduled_at: float | None = None
    saving_revision: int = 0
    dirty_topics: set[str] = field(default_factory=set)
    failure_message: str = ""

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    @property
    def dirty(self) -> bool:
        return self.project_revision > self.saved_revision or bool(self.dirty_topics)

    def mark_dirty(self, topics: Iterable[str] = (), *, now: float | None = None, delay_seconds: float = 1.5) -> int:
        stamp = time() if now is None else float(now)
        self.project_revision += 1
        self.last_modified_at = stamp
        self.dirty_topics.update(str(x) for x in topics if str(x))
        self.failure_message = ""
        if delay_seconds <= 0:
            self.status = AutosaveStatus.DIRTY
            self.scheduled_at = stamp
        else:
            self.status = AutosaveStatus.SCHEDULED
            self.scheduled_at = stamp + float(delay_seconds)
        return self.project_revision

    def begin_save(self, *, now: float | None = None) -> int:
        if not self.dirty:
            self.status = AutosaveStatus.SAVED if self.saved_revision else AutosaveStatus.CLEAN
            self.scheduled_at = None
            return self.saved_revision
        self.saving_revision = self.project_revision
        self.status = AutosaveStatus.SAVING
        self.scheduled_at = None
        return self.saving_revision

    def complete_save(self, revision: int, *, now: float | None = None) -> None:
        stamp = time() if now is None else float(now)
        revision = int(revision)
        if revision > self.saved_revision:
            self.saved_revision = revision
            self.last_saved_at = stamp
        self.saving_revision = 0
        self.failure_message = ""
        if self.project_revision > self.saved_revision:
            self.status = AutosaveStatus.DIRTY
        else:
            self.status = AutosaveStatus.SAVED
            self.dirty_topics.clear()
            self.scheduled_at = None

    def fail_save(self, message: str) -> None:
        self.saving_revision = 0
        self.failure_message = str(message or "Your latest changes could not be saved.")
        self.status = AutosaveStatus.FAILED

    def due(self, now: float) -> bool:
        return self.dirty and self.scheduled_at is not None and float(now) >= float(self.scheduled_at)

    def to_dict(self) -> dict[str, object]:
        return {
            "projectId": self.project_id,
            "projectRevision": self.project_revision,
            "savedRevision": self.saved_revision,
            "status": self.status_code,
            "lastModifiedAt": self.last_modified_at,
            "lastSavedAt": self.last_saved_at,
            "scheduledAt": self.scheduled_at,
            "savingRevision": self.saving_revision,
            "dirtyTopics": sorted(self.dirty_topics),
            "failureMessage": self.failure_message,
        }

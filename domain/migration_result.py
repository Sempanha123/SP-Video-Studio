from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class MigrationStatus(StrEnum):
    CURRENT = "current"
    MIGRATED = "migrated"
    FAILED = "failed"
    UNSUPPORTED_NEWER = "unsupported_newer"
    RECOVERED = "recovered"


@dataclass(frozen=True, slots=True)
class MigrationWarning:
    code: str
    message: str


@dataclass(slots=True)
class MigrationResult:
    status: str | MigrationStatus
    from_version: int
    to_version: int
    applied: list[str] = field(default_factory=list)
    warnings: list[MigrationWarning] = field(default_factory=list)
    backup_path: Path | None = None
    details: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return str(self.status) in {
            MigrationStatus.CURRENT.value,
            MigrationStatus.MIGRATED.value,
            MigrationStatus.RECOVERED.value,
        }

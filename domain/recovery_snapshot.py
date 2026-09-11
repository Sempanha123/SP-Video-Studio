from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class RecoverySnapshotType(StrEnum):
    PERIODIC = "periodic"
    PRE_RENDER = "pre_render"
    PRE_EXPORT = "pre_export"
    PRE_BATCH = "pre_batch"
    PRE_CLOSE = "pre_close"
    CRASH_RECOVERY = "crash_recovery"
    PRE_RESTORE_BACKUP = "pre_restore_backup"


class RecoverySnapshotStatus(StrEnum):
    VALID = "valid"
    CORRUPT = "corrupt"
    UNSUPPORTED = "unsupported"
    DISCARDED = "discarded"


@dataclass(slots=True)
class RecoverySnapshot:
    project_id: str
    session_id: str
    project_revision: int
    created_at: str
    reason: str
    snapshot_type: str | RecoverySnapshotType
    path: str
    size: int
    checksum: str
    status: str | RecoverySnapshotStatus = RecoverySnapshotStatus.VALID
    metadata: dict[str, Any] = field(default_factory=dict)
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str: return self.snapshot_id
    @property
    def type_code(self) -> str: return self.snapshot_type.value if isinstance(self.snapshot_type, StrEnum) else str(self.snapshot_type)
    @property
    def status_code(self) -> str: return self.status.value if isinstance(self.status, StrEnum) else str(self.status)
    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"projectId":self.project_id,"sessionId":self.session_id,"projectRevision":self.project_revision,
                "createdAt":self.created_at,"reason":self.reason,"snapshotType":self.type_code,"status":self.status_code,
                "path":self.path,"size":self.size,"checksum":self.checksum,"metadata":dict(self.metadata)}

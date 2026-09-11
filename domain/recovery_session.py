from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

@dataclass(slots=True)
class RecoverySession:
    started_at: str
    app_version: str
    session_id: str = field(default_factory=lambda: str(uuid4()))
    closed_at: str = ""
    clean_shutdown: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self):
        return {"sessionId":self.session_id,"startedAt":self.started_at,"closedAt":self.closed_at,"cleanShutdown":self.clean_shutdown,"appVersion":self.app_version,"metadata":dict(self.metadata)}

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class DiagnosticStatus(StrEnum):
    READY = "ready"
    WARNING = "warning"
    FAILED = "failed"
    NOT_AVAILABLE = "not_available"
    NOT_CONFIGURED = "not_configured"
    CHECKING = "checking"


@dataclass(slots=True)
class DiagnosticResult:
    id: str
    category: str
    name: str
    status: str = DiagnosticStatus.CHECKING.value
    summary: str = ""
    details: str = ""
    recommendation: str = ""
    technical_details: str = ""
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_technical: bool = True) -> dict[str, Any]:
        result = {
            "id": self.id,
            "category": self.category,
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "recommendation": self.recommendation,
            "checkedAt": self.checked_at,
            "durationMs": self.duration_ms,
            "metadata": dict(self.metadata),
        }
        if include_technical:
            result["technicalDetails"] = self.technical_details
        return result

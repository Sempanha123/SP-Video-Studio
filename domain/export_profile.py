from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.project import utc_now_iso


@dataclass(slots=True)
class ExportProfile:
    project_id: str
    last_preset_id: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {"projectId": self.project_id, "lastPresetId": self.last_preset_id, "settings": dict(self.settings), "updatedAt": self.updated_at}

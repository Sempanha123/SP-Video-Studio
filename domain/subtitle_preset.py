from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SubtitlePreset:
    preset_id: str
    name: str
    description: str
    style: dict[str, Any] = field(default_factory=dict)
    builtin: bool = True
    registry_version: int = 1

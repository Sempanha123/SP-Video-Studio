from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from domain.project import utc_now_iso


class DubMixMode(StrEnum):
    REPLACE = "replace"
    MIX = "mix"
    DUCK = "duck"
    CUSTOM = "custom"


@dataclass(slots=True)
class DubMixSettings:
    project_id: str
    mode: str | DubMixMode = DubMixMode.DUCK
    original_volume: float = 0.25
    dub_volume: float = 1.0
    duck_normal_volume: float = 0.25
    duck_under_volume: float = 0.12
    duck_fade_ms: int = 120
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def mode_code(self) -> str:
        return self.mode.value if isinstance(self.mode, StrEnum) else str(self.mode)

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("Project ID is required.")
        if self.mode_code not in {item.value for item in DubMixMode}:
            raise ValueError("Unsupported dub mix mode.")
        for value in (self.original_volume, self.dub_volume, self.duck_normal_volume, self.duck_under_volume):
            if not 0.0 <= float(value) <= 2.0:
                raise ValueError("Audio volume must be between 0 and 2.")
        if self.duck_fade_ms < 0 or self.duck_fade_ms > 5000:
            raise ValueError("Ducking fade is out of range.")

    def to_dict(self) -> dict[str, Any]:
        return {"projectId": self.project_id, "mode": self.mode_code,
                "originalVolume": self.original_volume, "dubVolume": self.dub_volume,
                "duckNormalVolume": self.duck_normal_volume, "duckUnderVolume": self.duck_under_volume,
                "duckFadeMs": self.duck_fade_ms, "metadata": dict(self.metadata), "updatedAt": self.updated_at}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "DubMixSettings":
        try: metadata = json.loads(str(row["metadata_json"] or "{}"))
        except (TypeError, json.JSONDecodeError): metadata = {}
        return cls(project_id=str(row["project_id"]), mode=str(row["mode"]),
                   original_volume=float(row["original_volume"]), dub_volume=float(row["dub_volume"]),
                   duck_normal_volume=float(row["duck_normal_volume"]), duck_under_volume=float(row["duck_under_volume"]),
                   duck_fade_ms=int(row["duck_fade_ms"]), metadata=metadata if isinstance(metadata,dict) else {},
                   updated_at=str(row["updated_at"]))

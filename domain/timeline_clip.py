from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TimelineClip:
    clip_id: str
    track_id: str
    source_type: str
    source_id: str
    start_ms: int
    duration_ms: int
    source_in_ms: int = 0
    source_out_ms: int | None = None
    enabled: bool = True
    locked: bool = False
    muted: bool = False
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str: return self.clip_id
    @property
    def end_ms(self) -> int: return self.start_ms + self.duration_ms

    def validate(self) -> None:
        if not self.clip_id or not self.track_id or not self.source_id: raise ValueError("Timeline clip identity is incomplete.")
        if self.start_ms < 0: raise ValueError("Timeline clip start cannot be negative.")
        if self.duration_ms <= 0: raise ValueError("Timeline clip duration must be positive.")
        if self.source_in_ms < 0: raise ValueError("Timeline source-in cannot be negative.")
        if self.source_out_ms is not None and self.source_out_ms <= self.source_in_ms: raise ValueError("Timeline source-out must be after source-in.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"id":self.id,"trackId":self.track_id,"sourceType":self.source_type,"sourceId":self.source_id,"startMs":self.start_ms,"endMs":self.end_ms,"durationMs":self.duration_ms,"sourceInMs":self.source_in_ms,"sourceOutMs":self.source_out_ms if self.source_out_ms is not None else -1,"enabled":self.enabled,"locked":self.locked,"muted":self.muted,"label":self.label,"metadata":dict(self.metadata)}

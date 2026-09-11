from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class TimelineSelection:
    clip_id: str = ""
    track_id: str = ""
    source_type: str = ""
    source_id: str = ""

    @property
    def empty(self) -> bool: return not self.clip_id

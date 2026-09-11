from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4


class TimelineTrackType(StrEnum):
    OVERLAY = "overlay"
    VIDEO = "video"
    BROLL = "broll"
    SUBTITLE = "subtitle"
    VOICE = "voice"
    SOURCE_AUDIO = "source_audio"
    MUSIC = "music"
    SFX = "sfx"


DEFAULT_TRACKS: tuple[tuple[str, str], ...] = (
    (TimelineTrackType.OVERLAY.value, "Overlays"),
    (TimelineTrackType.VIDEO.value, "Video"),
    (TimelineTrackType.SUBTITLE.value, "Subtitles"),
    (TimelineTrackType.VOICE.value, "Voice"),
    (TimelineTrackType.SOURCE_AUDIO.value, "Source Audio"),
    (TimelineTrackType.MUSIC.value, "Music"),
    (TimelineTrackType.SFX.value, "SFX"),
    (TimelineTrackType.BROLL.value, "B-roll"),
)


@dataclass(slots=True)
class TimelineTrack:
    project_id: str
    track_type: str | TimelineTrackType
    name: str
    order: int
    visible: bool = True
    muted: bool = False
    locked: bool = False
    height: int = 64
    track_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str: return self.track_id
    @property
    def type_code(self) -> str: return self.track_type.value if isinstance(self.track_type, StrEnum) else str(self.track_type)

    def validate(self) -> None:
        if not self.project_id: raise ValueError("Timeline track requires a project.")
        if self.type_code not in {item.value for item in TimelineTrackType}: raise ValueError("Unsupported timeline track type.")
        if not self.name.strip(): raise ValueError("Timeline track name is required.")
        if self.order < 0: raise ValueError("Timeline track order cannot be negative.")
        self.height = max(36, min(180, int(self.height)))

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"id":self.id,"projectId":self.project_id,"type":self.type_code,"name":self.name,"order":self.order,"visible":self.visible,"muted":self.muted,"locked":self.locked,"height":self.height,"metadata":dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "TimelineTrack":
        try: metadata=json.loads(row["metadata_json"] or "{}")
        except Exception: metadata={}
        return cls(track_id=str(row["id"]),project_id=str(row["project_id"]),track_type=str(row["track_type"]),name=str(row["name"]),order=int(row["track_order"]),visible=bool(row["visible"]),muted=bool(row["muted"]),locked=bool(row["locked"]),height=int(row["height"]),metadata=metadata if isinstance(metadata,dict) else {})

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class Timeline:
    project_id: str
    duration_ms: int = 0
    zoom_level: float = 80.0
    playhead_ms: int = 0
    scroll_position: float = 0.0
    snap_enabled: bool = True
    snap_threshold_px: float = 8.0
    active_track_id: str = ""
    selected_clip_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("Timeline requires a project.")
        self.duration_ms = max(0, int(self.duration_ms))
        self.zoom_level = max(10.0, min(800.0, float(self.zoom_level)))
        self.playhead_ms = max(0, min(int(self.playhead_ms), self.duration_ms if self.duration_ms else int(self.playhead_ms)))
        self.scroll_position = max(0.0, float(self.scroll_position))
        self.snap_threshold_px = max(1.0, min(40.0, float(self.snap_threshold_px)))

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "projectId": self.project_id,
            "durationMs": self.duration_ms,
            "pixelsPerSecond": self.zoom_level,
            "playheadMs": self.playhead_ms,
            "scrollPosition": self.scroll_position,
            "snapEnabled": self.snap_enabled,
            "snapThresholdPx": self.snap_threshold_px,
            "activeTrackId": self.active_track_id,
            "selectedClipId": self.selected_clip_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "Timeline":
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except Exception:
            metadata = {}
        return cls(
            project_id=str(row["project_id"]),
            zoom_level=float(row["zoom_level"]),
            playhead_ms=int(row["playhead_ms"]),
            scroll_position=float(row["scroll_position"]),
            snap_enabled=bool(row["snap_enabled"]),
            snap_threshold_px=float(row["snap_threshold_px"]),
            active_track_id=str(row["active_track_id"] or ""),
            selected_clip_id=str(row["selected_clip_id"] or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
        )

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso
from domain.scene_audio import SceneAudioSettings
from domain.scene_transition import SceneTransition


class SceneStatus(StrEnum):
    READY = "ready"
    INCOMPLETE = "incomplete"
    MISSING_ASSET = "missing_asset"
    DISABLED = "disabled"


class SceneSourceStatus(StrEnum):
    CURRENT = "current"
    CHANGED = "source_changed"
    MISSING = "source_missing"


FIT_MODES = {"fit", "fill", "stretch"}


@dataclass(slots=True)
class Scene:
    project_id: str = ""
    order: int = 0
    name: str = ""
    duration_ms: int = 5000
    enabled: bool = True
    primary_media_id: str = ""
    background_media_id: str = ""
    narration_audio_id: str = ""
    subtitle_track_id: str = ""
    script_section_id: str = ""
    transcript_segment_id: str = ""
    translation_segment_id: str = ""
    source_hash: str = ""
    source_status: str | SceneSourceStatus = SceneSourceStatus.CURRENT
    fit_mode: str = "fill"
    source_start_ms: int = 0
    source_end_ms: int | None = None
    background_color: str = "#10131A"
    status: str | SceneStatus = SceneStatus.INCOMPLETE
    scene_id: str = field(default_factory=lambda: str(uuid4()))
    transition_in: SceneTransition = field(default_factory=SceneTransition)
    transition_out: SceneTransition = field(default_factory=SceneTransition)
    audio: SceneAudioSettings = field(default_factory=SceneAudioSettings)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Phase-0 compatibility aliases; production persistence uses the fields above.
    index: int | None = None
    start_time: float = 0.0
    narration: str = ""
    media: list[str] = field(default_factory=list)
    overlays: list[dict[str, object]] = field(default_factory=list)
    subtitle_settings: dict[str, object] = field(default_factory=dict)
    audio_settings: dict[str, object] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if self.index is not None:
            self.order = int(self.index)
        if not self.name:
            self.name = f"Scene {self.order + 1}"

    @property
    def id(self) -> str: return self.scene_id
    @property
    def status_code(self) -> str: return self.status.value if isinstance(self.status, StrEnum) else str(self.status)
    @property
    def source_status_code(self) -> str: return self.source_status.value if isinstance(self.source_status, StrEnum) else str(self.source_status)

    def validate(self) -> None:
        if not self.project_id: raise ValueError("Scene requires a project.")
        if self.order < 0: raise ValueError("Scene order cannot be negative.")
        if not self.name.strip(): raise ValueError("Scene name is required.")
        if self.duration_ms <= 0: raise ValueError("Scene duration must be greater than zero.")
        if self.fit_mode not in FIT_MODES: raise ValueError("Unsupported media fit mode.")
        if self.source_start_ms < 0: raise ValueError("Video start cannot be negative.")
        if self.source_end_ms is not None and self.source_end_ms <= self.source_start_ms: raise ValueError("Video end must be after video start.")
        self.transition_in.validate(); self.transition_out.validate(); self.audio.validate()

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"projectId":self.project_id,"order":self.order,"name":self.name,"durationMs":self.duration_ms,"enabled":self.enabled,"primaryMediaId":self.primary_media_id,"backgroundMediaId":self.background_media_id,"narrationAudioId":self.narration_audio_id,"subtitleTrackId":self.subtitle_track_id,"scriptSectionId":self.script_section_id,"transcriptSegmentId":self.transcript_segment_id,"translationSegmentId":self.translation_segment_id,"sourceHash":self.source_hash,"sourceStatus":self.source_status_code,"fitMode":self.fit_mode,"sourceStartMs":self.source_start_ms,"sourceEndMs":self.source_end_ms if self.source_end_ms is not None else -1,"backgroundColor":self.background_color,"status":self.status_code,"transitionIn":self.transition_in.to_dict(),"transitionOut":self.transition_out.to_dict(),"audio":self.audio.to_dict(),"metadata":dict(self.metadata),"createdAt":self.created_at,"updatedAt":self.updated_at}

    @classmethod
    def from_record(cls, r: Mapping[str, Any]) -> "Scene":
        def decode(name:str):
            try: value=json.loads(r[name] or "{}")
            except Exception: value={}
            return value if isinstance(value,dict) else {}
        return cls(scene_id=str(r["id"]),project_id=str(r["project_id"]),order=int(r["scene_order"]),name=str(r["name"]),duration_ms=int(r["duration_ms"]),enabled=bool(r["enabled"]),primary_media_id=str(r["primary_media_id"] or ""),background_media_id=str(r["background_media_id"] or ""),narration_audio_id=str(r["narration_audio_id"] or ""),subtitle_track_id=str(r["subtitle_track_id"] or ""),script_section_id=str(r["script_section_id"] or ""),transcript_segment_id=str(r["transcript_segment_id"] or ""),translation_segment_id=str(r["translation_segment_id"] or ""),source_hash=str(r["source_hash"] or ""),source_status=str(r["source_status"] or "current"),fit_mode=str(r["fit_mode"] or "fill"),source_start_ms=int(r["source_start_ms"] or 0),source_end_ms=int(r["source_end_ms"]) if r["source_end_ms"] is not None else None,background_color=str(r["background_color"] or "#10131A"),status=str(r["status"]),transition_in=SceneTransition.from_dict(decode("transition_in_json")),transition_out=SceneTransition.from_dict(decode("transition_out_json")),audio=SceneAudioSettings.from_dict(decode("audio_json")),metadata=decode("metadata_json"),created_at=str(r["created_at"]),updated_at=str(r["updated_at"]))

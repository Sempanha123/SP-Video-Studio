from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4


@dataclass(slots=True)
class DirectorScenePlan:
    plan_id: str
    order: int
    title: str
    purpose: str
    target_duration_ms: int
    visual_type: str = "mixed_media"
    visual_description: str = "Use relevant project media or a supporting visual."
    overlay_recommendation: str = ""
    voice_style: str = ""
    subtitle_style: str = "clean"
    transition: str = "cut"
    notes: str = ""
    script_section_id: str = ""
    locked: bool = False
    user_modified: bool = False
    scene_plan_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.scene_plan_id

    def validate(self) -> None:
        if self.order < 0:
            raise ValueError("Scene plan order cannot be negative.")
        if self.target_duration_ms <= 0:
            raise ValueError("Scene plan duration must be greater than zero.")
        if not self.title.strip():
            raise ValueError("Scene plan title is required.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "planId": self.plan_id,
            "order": self.order,
            "title": self.title,
            "purpose": self.purpose,
            "targetDurationMs": self.target_duration_ms,
            "scriptSectionId": self.script_section_id,
            "visualType": self.visual_type,
            "visualDescription": self.visual_description,
            "overlayRecommendation": self.overlay_recommendation,
            "voiceStyle": self.voice_style,
            "subtitleStyle": self.subtitle_style,
            "transition": self.transition,
            "notes": self.notes,
            "locked": self.locked,
            "userModified": self.user_modified,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any], metadata: dict[str, Any] | None = None) -> "DirectorScenePlan":
        return cls(
            scene_plan_id=str(record["id"]),
            plan_id=str(record["plan_id"]),
            order=int(record["scene_order"]),
            title=str(record["title"]),
            purpose=str(record["purpose"] or ""),
            target_duration_ms=int(record["target_duration_ms"]),
            script_section_id=str(record["script_section_id"] or ""),
            visual_type=str(record["visual_type"] or "mixed_media"),
            visual_description=str(record["visual_description"] or ""),
            overlay_recommendation=str(record["overlay_recommendation"] or ""),
            voice_style=str(record["voice_style"] or ""),
            subtitle_style=str(record["subtitle_style"] or "clean"),
            transition=str(record["transition"] or "cut"),
            notes=str(record["notes"] or ""),
            locked=bool(record["locked"]),
            user_modified=bool(record["user_modified"]),
            metadata=dict(metadata or {}),
        )

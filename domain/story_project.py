from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from domain.project import SUPPORTED_LANGUAGES, utc_now_iso

STORY_TYPES = {
    "short_story", "documentary_story", "educational_story", "motivational_story",
    "mystery", "drama", "adventure", "biography_style", "explainer_story", "custom",
}
STORY_TONES = {"warm", "calm", "dramatic", "inspirational", "serious", "friendly", "suspenseful", "educational", "neutral"}
STORY_AUDIENCES = {"general", "young_audience", "adult", "professional", "educational"}
STORY_PACES = {"slow", "balanced", "fast"}
STORY_STATUSES = {"draft", "review", "ready", "outdated"}


def story_input_fingerprint(*, title: str, idea: str, story_type: str, tone: str, audience: str,
                            target_duration_ms: int, language: str, pace: str) -> str:
    payload = {
        "title": title.strip(), "idea": idea.strip(), "story_type": story_type, "tone": tone,
        "audience": audience, "target_duration_ms": int(target_duration_ms), "language": language, "pace": pace,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(slots=True)
class StoryProjectMetadata:
    project_id: str
    title: str = ""
    idea: str = ""
    story_type: str = "short_story"
    language: str = "en"
    target_duration_ms: int = 60_000
    audience: str = "general"
    tone: str = "warm"
    pace: str = "balanced"
    status: str = "draft"
    narrator_voice_id: str = ""
    notes: str = ""
    source_fingerprint: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.project_id: raise ValueError("Project ID is required.")
        if self.story_type not in STORY_TYPES: raise ValueError("Unsupported Story type.")
        if self.language not in SUPPORTED_LANGUAGES: raise ValueError("Story Studio supports English and Khmer.")
        if self.target_duration_ms <= 0: raise ValueError("Target duration must be positive.")
        if self.audience not in STORY_AUDIENCES: raise ValueError("Unsupported Story audience.")
        if self.tone not in STORY_TONES: raise ValueError("Unsupported Story tone.")
        if self.pace not in STORY_PACES: raise ValueError("Unsupported Story pace.")
        if self.status not in STORY_STATUSES: raise ValueError("Unsupported Story status.")

    def planning_fingerprint(self) -> str:
        return story_input_fingerprint(title=self.title, idea=self.idea, story_type=self.story_type, tone=self.tone,
                                       audience=self.audience, target_duration_ms=self.target_duration_ms,
                                       language=self.language, pace=self.pace)

    def to_dict(self) -> dict[str, Any]:
        return {"projectId": self.project_id, "title": self.title, "idea": self.idea, "storyType": self.story_type,
                "language": self.language, "targetDurationMs": self.target_duration_ms, "audience": self.audience,
                "tone": self.tone, "pace": self.pace, "status": self.status, "narratorVoiceId": self.narrator_voice_id,
                "notes": self.notes, "sourceFingerprint": self.source_fingerprint,
                "createdAt": self.created_at, "updatedAt": self.updated_at, "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "StoryProjectMetadata":
        return cls(project_id=str(row["project_id"]), title=str(row["title"] or ""), idea=str(row["idea"] or ""),
                   story_type=str(row["story_type"] or "short_story"), language=str(row["language"] or "en"),
                   target_duration_ms=int(row["target_duration_ms"] or 60_000), audience=str(row["audience"] or "general"),
                   tone=str(row["tone"] or "warm"), pace=str(row["pace"] or "balanced"), status=str(row["status"] or "draft"),
                   narrator_voice_id=str(row["narrator_voice_id"] or ""), notes=str(row["notes"] or ""),
                   source_fingerprint=str(row["source_fingerprint"] or ""), created_at=str(row["created_at"]),
                   updated_at=str(row["updated_at"]), metadata=json.loads(str(row["metadata_json"] or "{}")))

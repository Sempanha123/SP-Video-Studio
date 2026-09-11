from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.language import supported_language_codes
from domain.project import utc_now_iso


class SpeakerRole(StrEnum):
    NARRATOR = "narrator"
    REPORTER = "reporter"
    HOST = "host"
    INTERVIEWER = "interviewer"
    INTERVIEW_GUEST = "interview_guest"
    CHARACTER = "character"
    EXPERT = "expert"
    SPEAKER = "speaker"
    CUSTOM = "custom"


@dataclass(slots=True)
class SpeakerProfile:
    project_id: str
    name: str
    role: str | SpeakerRole = SpeakerRole.SPEAKER
    voice_id: str = ""
    language: str = "en"
    description: str = ""
    avatar: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    speaker_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str:
        return self.speaker_id

    @property
    def role_code(self) -> str:
        return self.role.value if isinstance(self.role, StrEnum) else str(self.role)

    def validate(self) -> None:
        if not self.project_id or not self.speaker_id:
            raise ValueError("Speaker identity and project are required.")
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Speaker name is required.")
        if self.role_code not in {item.value for item in SpeakerRole}:
            raise ValueError("Unsupported speaker role.")
        if self.language not in supported_language_codes():
            raise ValueError("Unsupported speaker language.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "projectId": self.project_id,
            "name": self.name,
            "role": self.role_code,
            "roleName": self.role_code.replace("_", " ").title(),
            "voiceId": self.voice_id,
            "language": self.language,
            "description": self.description,
            "avatar": self.avatar,
            "metadata": dict(self.metadata),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "SpeakerProfile":
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except Exception:
            metadata = {}
        return cls(
            speaker_id=str(row["id"]), project_id=str(row["project_id"]), name=str(row["name"]),
            role=str(row["role"]), voice_id=str(row["voice_id"] or ""), language=str(row["language"]),
            description=str(row["description"] or ""), avatar=str(row["avatar"] or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
            created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
        )

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Any
from uuid import uuid4

from domain.language import supported_language_codes

SUPPORTED_LANGUAGES = frozenset(supported_language_codes())
SUPPORTED_ASPECT_RATIOS = {"9:16", "16:9", "1:1"}
SUPPORTED_FPS = {24, 25, 30, 50, 60}
PROJECT_VERSION = 1


class ProjectWorkflow(StrEnum):
    NEWS = "news"
    STORY = "story"
    TRANSLATE = "translate"
    VIDEO = "video"
    SHORTS = "shorts"
    BATCH = "batch"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_value(value: str | StrEnum) -> str:
    return value.value if isinstance(value, StrEnum) else str(value)


@dataclass(slots=True)
class Project:
    title: str
    workflow: str | ProjectWorkflow
    language: str = "en"
    aspect_ratio: str = "16:9"
    fps: int = 30
    project_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_opened_at: str | None = None
    thumbnail_path: str | None = None
    status: str | ProjectStatus = ProjectStatus.DRAFT
    project_path: str = ""
    version: int = PROJECT_VERSION
    template: str | None = None
    settings: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.project_id

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id, "id": self.project_id, "title": self.title,
            "workflow": _enum_value(self.workflow), "language": self.language,
            "aspect_ratio": self.aspect_ratio, "fps": self.fps, "created_at": self.created_at,
            "updated_at": self.updated_at, "last_opened_at": self.last_opened_at,
            "thumbnail_path": self.thumbnail_path, "status": _enum_value(self.status),
            "project_path": self.project_path, "version": self.version, "template": self.template,
            "settings": dict(self.settings),
        }

    def to_metadata(self) -> dict[str, object]:
        return {
            "version": self.version, "id": self.project_id, "title": self.title,
            "workflow": _enum_value(self.workflow), "language": self.language,
            "aspect_ratio": self.aspect_ratio, "fps": self.fps, "created_at": self.created_at,
            "updated_at": self.updated_at, "last_opened_at": self.last_opened_at,
            "thumbnail_path": self.thumbnail_path, "status": _enum_value(self.status),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Project":
        return cls(
            project_id=str(record["id"]), title=str(record["title"]), workflow=str(record["workflow"]),
            language=str(record["language"]), aspect_ratio=str(record["aspect_ratio"]), fps=int(record["fps"]),
            created_at=str(record["created_at"]), updated_at=str(record["updated_at"]),
            last_opened_at=record["last_opened_at"], thumbnail_path=record["thumbnail_path"],
            status=str(record["status"]), project_path=str(record["project_path"]), version=int(record["version"]),
        )

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any], project_path: str | Path = "") -> "Project":
        required = {"version", "id", "title", "workflow", "language", "aspect_ratio", "fps", "created_at", "updated_at"}
        missing = required.difference(metadata)
        if missing:
            raise ValueError(f"Project metadata is missing required fields: {', '.join(sorted(missing))}")
        return cls(
            project_id=str(metadata["id"]), title=str(metadata["title"]), workflow=str(metadata["workflow"]),
            language=str(metadata["language"]), aspect_ratio=str(metadata["aspect_ratio"]), fps=int(metadata["fps"]),
            created_at=str(metadata["created_at"]), updated_at=str(metadata["updated_at"]),
            last_opened_at=metadata.get("last_opened_at"), thumbnail_path=metadata.get("thumbnail_path"),
            status=str(metadata.get("status", ProjectStatus.DRAFT.value)), project_path=str(project_path), version=int(metadata["version"]),
        )

    def validate(self) -> None:
        title = self.title.strip()
        if not title:
            raise ValueError("Project name is required.")
        if _enum_value(self.workflow) not in {item.value for item in ProjectWorkflow}:
            raise ValueError("Unsupported project workflow.")
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported project language.")
        if self.aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            raise ValueError("Unsupported aspect ratio.")
        if self.fps not in SUPPORTED_FPS:
            raise ValueError("Unsupported FPS value.")
        if _enum_value(self.status) not in {item.value for item in ProjectStatus}:
            raise ValueError("Unsupported project status.")
        if self.version != PROJECT_VERSION:
            raise ValueError("Unsupported project version.")

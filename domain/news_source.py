from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class NewsSourceType(StrEnum):
    URL = "url"
    MANUAL = "manual"
    LOCAL = "local"


class NewsSourceStatus(StrEnum):
    PENDING = "pending"
    FETCHING = "fetching"
    READY = "ready"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"
    REMOVED = "removed"


@dataclass(slots=True)
class NewsSource:
    project_id: str
    source_type: str | NewsSourceType
    title: str = ""
    url: str = ""
    publisher: str = ""
    author: str = ""
    published_at: str | None = None
    accessed_at: str | None = None
    language: str = "auto"
    status: str | NewsSourceStatus = NewsSourceStatus.PENDING
    source_path: str = ""
    category: str = "other"
    notes: str = ""
    latest_snapshot_id: str | None = None
    source_updated: bool = False
    source_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.source_id

    @property
    def type_code(self) -> str:
        return self.source_type.value if isinstance(self.source_type, StrEnum) else str(self.source_type)

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.project_id or not self.source_id:
            raise ValueError("Source ownership is required.")
        if self.type_code not in {item.value for item in NewsSourceType}:
            raise ValueError("Unsupported source type.")
        if self.status_code not in {item.value for item in NewsSourceStatus}:
            raise ValueError("Unsupported source status.")
        if self.language not in {"auto", "en", "km"}:
            raise ValueError("Unsupported source language.")
        if self.type_code == "url" and not self.url:
            raise ValueError("URL source requires a URL.")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.source_id, "projectId": self.project_id, "type": self.type_code,
            "title": self.title, "url": self.url, "publisher": self.publisher, "author": self.author,
            "publishedAt": self.published_at or "", "accessedAt": self.accessed_at or "",
            "language": self.language, "status": self.status_code, "sourcePath": self.source_path,
            "category": self.category, "notes": self.notes, "latestSnapshotId": self.latest_snapshot_id or "",
            "sourceUpdated": self.source_updated, "createdAt": self.created_at, "updatedAt": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsSource":
        return cls(
            source_id=str(row["id"]), project_id=str(row["project_id"]), source_type=str(row["source_type"]),
            title=str(row["title"] or ""), url=str(row["url"] or ""), publisher=str(row["publisher"] or ""),
            author=str(row["author"] or ""), published_at=row["published_at"], accessed_at=row["accessed_at"],
            language=str(row["language"] or "auto"), status=str(row["status"] or "pending"),
            source_path=str(row["source_path"] or ""), category=str(row["category"] or "other"),
            notes=str(row["notes"] or ""), latest_snapshot_id=row["latest_snapshot_id"],
            source_updated=bool(row["source_updated"]), created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
            metadata=json.loads(str(row["metadata_json"] or "{}")),
        )


@dataclass(slots=True)
class NewsSourceSnapshot:
    source_id: str
    content_text: str
    content_hash: str
    title: str = ""
    author: str = ""
    published_at: str | None = None
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    retrieved_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.snapshot_id

    def to_dict(self) -> dict[str, object]:
        return {"id": self.snapshot_id, "sourceId": self.source_id, "retrievedAt": self.retrieved_at,
                "contentHash": self.content_hash, "title": self.title, "author": self.author,
                "publishedAt": self.published_at or "", "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsSourceSnapshot":
        return cls(snapshot_id=str(row["id"]), source_id=str(row["source_id"]), retrieved_at=str(row["retrieved_at"]),
                   content_text=str(row["content_text"] or ""), content_hash=str(row["content_hash"]),
                   title=str(row["title"] or ""), author=str(row["author"] or ""), published_at=row["published_at"],
                   metadata=json.loads(str(row["metadata_json"] or "{}")))

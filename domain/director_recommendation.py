from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4


@dataclass(slots=True)
class DirectorRecommendation:
    category: str
    title: str
    value: Any
    reason: str
    recommendation_id: str = field(default_factory=lambda: str(uuid4()))
    source: str = "deterministic"
    confidence: float | None = None
    user_modified: bool = False
    locked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.recommendation_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "value": self.value,
            "reason": self.reason,
            "source": self.source,
            "confidence": self.confidence,
            "userModified": self.user_modified,
            "locked": self.locked,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DirectorRecommendation":
        return cls(
            recommendation_id=str(value.get("id") or uuid4()),
            category=str(value.get("category") or "technical"),
            title=str(value.get("title") or "Recommendation"),
            value=value.get("value"),
            reason=str(value.get("reason") or ""),
            source=str(value.get("source") or "deterministic"),
            confidence=float(value["confidence"]) if value.get("confidence") is not None else None,
            user_modified=bool(value.get("userModified", value.get("user_modified", False))),
            locked=bool(value.get("locked", False)),
            metadata=dict(value.get("metadata") or {}),
        )

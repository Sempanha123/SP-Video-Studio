from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class NewsClaimStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNSUPPORTED = "unsupported"
    CONFLICTING = "conflicting"


@dataclass(slots=True)
class NewsClaim:
    project_id: str
    text: str
    claim_type: str = "fact"
    status: str | NewsClaimStatus = NewsClaimStatus.CANDIDATE
    importance: str = "supporting"
    uncertainty: str = "reported"
    user_modified: bool = False
    locked: bool = False
    notes: str = ""
    quote_text: str = ""
    speaker: str = ""
    quote_kind: str = ""
    original_quote: str = ""
    claim_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.claim_id

    @property
    def status_code(self) -> str:
        return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def validate(self) -> None:
        if not self.project_id or not self.claim_id or not self.text.strip():
            raise ValueError("Claim text and ownership are required.")
        if self.status_code not in {item.value for item in NewsClaimStatus}:
            raise ValueError("Unsupported claim status.")
        if self.importance not in {"primary", "supporting", "background"}:
            raise ValueError("Unsupported claim importance.")
        if self.uncertainty not in {"confirmed", "reported", "estimated", "alleged", "uncertain"}:
            raise ValueError("Unsupported uncertainty wording.")

    def to_dict(self) -> dict[str, object]:
        return {"id": self.claim_id, "projectId": self.project_id, "text": self.text, "type": self.claim_type,
                "status": self.status_code, "importance": self.importance, "uncertainty": self.uncertainty,
                "userModified": self.user_modified, "locked": self.locked, "notes": self.notes,
                "quoteText": self.quote_text, "speaker": self.speaker, "quoteKind": self.quote_kind,
                "originalQuote": self.original_quote, "createdAt": self.created_at, "updatedAt": self.updated_at,
                "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsClaim":
        return cls(claim_id=str(row["id"]), project_id=str(row["project_id"]), text=str(row["text"]),
                   claim_type=str(row["claim_type"] or "fact"), status=str(row["status"] or "candidate"),
                   importance=str(row["importance"] or "supporting"), uncertainty=str(row["uncertainty"] or "reported"),
                   user_modified=bool(row["user_modified"]), locked=bool(row["locked"]), notes=str(row["notes"] or ""),
                   quote_text=str(row["quote_text"] or ""), speaker=str(row["speaker"] or ""), quote_kind=str(row["quote_kind"] or ""),
                   original_quote=str(row["original_quote"] or ""), created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
                   metadata=json.loads(str(row["metadata_json"] or "{}")))


@dataclass(slots=True)
class NewsEvidence:
    claim_id: str
    source_id: str
    snapshot_id: str
    evidence_text: str
    source_start_offset: int = -1
    source_end_offset: int = -1
    evidence_type: str = "support"
    evidence_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.evidence_id

    def to_dict(self) -> dict[str, object]:
        return {"id": self.evidence_id, "claimId": self.claim_id, "sourceId": self.source_id,
                "snapshotId": self.snapshot_id, "evidenceText": self.evidence_text,
                "startOffset": self.source_start_offset, "endOffset": self.source_end_offset,
                "type": self.evidence_type, "createdAt": self.created_at, "metadata": dict(self.metadata)}

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> "NewsEvidence":
        return cls(evidence_id=str(row["id"]), claim_id=str(row["claim_id"]), source_id=str(row["source_id"]),
                   snapshot_id=str(row["snapshot_id"]), evidence_text=str(row["evidence_text"]),
                   source_start_offset=int(row["source_start_offset"]), source_end_offset=int(row["source_end_offset"]),
                   evidence_type=str(row["evidence_type"] or "support"), created_at=str(row["created_at"]),
                   metadata=json.loads(str(row["metadata_json"] or "{}")))

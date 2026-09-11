from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


class DubAudioOutputStatus(StrEnum):
    BUILDING = "building"
    READY = "ready"
    OUTDATED = "outdated"
    FAILED = "failed"


@dataclass(slots=True)
class DubAudioOutput:
    project_id: str
    source_media_id: str
    target_language: str
    file_path: str
    duration_ms: int
    fingerprint: str
    output_type: str = "final_mix"
    voice_profile_id: str = ""
    status: str | DubAudioOutputStatus = DubAudioOutputStatus.READY
    settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    output_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def id(self) -> str: return self.output_id
    @property
    def status_code(self) -> str: return self.status.value if isinstance(self.status, StrEnum) else str(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"projectId":self.project_id,"sourceMediaId":self.source_media_id,
                "targetLanguage":self.target_language,"voiceProfileId":self.voice_profile_id,"filePath":self.file_path,
                "durationMs":self.duration_ms,"fingerprint":self.fingerprint,"outputType":self.output_type,
                "status":self.status_code,"settings":dict(self.settings),"metadata":dict(self.metadata),"createdAt":self.created_at}

    @classmethod
    def from_record(cls,row:Mapping[str,Any])->"DubAudioOutput":
        def load(name:str)->dict[str,Any]:
            try:
                value=json.loads(str(row[name] or "{}")); return value if isinstance(value,dict) else {}
            except (TypeError,json.JSONDecodeError): return {}
        return cls(output_id=str(row["id"]),project_id=str(row["project_id"]),source_media_id=str(row["source_media_id"] or ""),
                   target_language=str(row["target_language"]),voice_profile_id=str(row["voice_profile_id"] or ""),
                   file_path=str(row["file_path"]),duration_ms=int(row["duration_ms"] or 0),fingerprint=str(row["fingerprint"] or ""),
                   output_type=str(row["output_type"]),status=str(row["status"]),settings=load("settings_json"),metadata=load("metadata_json"),created_at=str(row["created_at"]))

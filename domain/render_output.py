from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from domain.project import utc_now_iso


@dataclass(slots=True)
class RenderOutput:
    project_id: str
    render_job_id: str
    file_path: str
    width: int
    height: int
    fps: float
    duration_ms: int
    video_codec: str
    audio_codec: str = ""
    file_size: int = 0
    thumbnail_path: str = ""
    output_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str: return self.output_id

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"projectId":self.project_id,"renderJobId":self.render_job_id,"filePath":self.file_path,"width":self.width,"height":self.height,"fps":self.fps,"durationMs":self.duration_ms,"videoCodec":self.video_codec,"audioCodec":self.audio_codec,"fileSize":self.file_size,"thumbnailPath":self.thumbnail_path,"createdAt":self.created_at,"metadata":dict(self.metadata)}

    @classmethod
    def from_record(cls, r: Mapping[str, Any]) -> "RenderOutput":
        try: meta=json.loads(r["metadata_json"] or "{}")
        except Exception: meta={}
        return cls(output_id=str(r["id"]),project_id=str(r["project_id"]),render_job_id=str(r["render_job_id"]),file_path=str(r["file_path"]),width=int(r["width"]),height=int(r["height"]),fps=float(r["fps"]),duration_ms=int(r["duration_ms"]),video_codec=str(r["video_codec"]),audio_codec=str(r["audio_codec"] or ""),file_size=int(r["file_size"] or 0),thumbnail_path=str(r["thumbnail_path"] or ""),created_at=str(r["created_at"]),metadata=meta if isinstance(meta,dict) else {})

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SupportBundle:
    path: Path
    files: list[str] = field(default_factory=list)
    created_at: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "files": list(self.files),
            "createdAt": self.created_at,
            "sizeBytes": self.size_bytes,
        }

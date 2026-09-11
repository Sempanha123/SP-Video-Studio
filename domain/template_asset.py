from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Mapping

ALLOWED_TEMPLATE_ASSET_EXTENSIONS=frozenset({".png",".jpg",".jpeg",".webp",".wav",".mp3",".json",".txt",".md",".mp4",".mov"})
EXECUTABLE_TEMPLATE_EXTENSIONS=frozenset({".exe",".bat",".ps1",".cmd",".js",".py",".com",".scr",".msi",".dll",".sh"})


def is_safe_relative_template_path(value: str) -> bool:
    text=str(value or "").replace("\\","/")
    if not text or text.startswith("/") or ":" in text.split("/")[0]: return False
    parts=PurePosixPath(text).parts
    return all(part not in {"", ".", ".."} for part in parts)


@dataclass(slots=True)
class TemplateAsset:
    relative_path: str
    sha256: str
    size: int
    asset_type: str = "asset"
    optional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not is_safe_relative_template_path(self.relative_path): raise ValueError("Template asset path is unsafe.")
        suffix=PurePosixPath(self.relative_path).suffix.lower()
        if suffix in EXECUTABLE_TEMPLATE_EXTENSIONS: raise ValueError("Executable files are not allowed in templates.")
        if suffix not in ALLOWED_TEMPLATE_ASSET_EXTENSIONS: raise ValueError(f"Unsupported template asset type: {suffix or '(none)'}")
        if self.size<0: raise ValueError("Template asset size cannot be negative.")
        if self.sha256 and (len(self.sha256)!=64 or any(c not in "0123456789abcdefABCDEF" for c in self.sha256)): raise ValueError("Template asset checksum is invalid.")

    def to_dict(self) -> dict[str, Any]:
        self.validate(); return {"path":self.relative_path,"sha256":self.sha256,"size":self.size,"type":self.asset_type,"optional":self.optional,"metadata":dict(self.metadata)}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "TemplateAsset":
        item=cls(str(raw.get("path") or ""),str(raw.get("sha256") or ""),int(raw.get("size") or 0),str(raw.get("type") or "asset"),bool(raw.get("optional",False)),dict(raw.get("metadata") or {})); item.validate(); return item

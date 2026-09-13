from __future__ import annotations

import re
from pathlib import Path

from services.safe_path_service import UnsafeManagedPath, safe_copy_destination


class ExportInvalidFilename(ValueError):
    pass


class ExportOutputConflict(FileExistsError):
    pass


_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", "CLOCK$", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class ExportFilenameService:
    def sanitize(self, filename: str, *, extension: str = ".mp4") -> str:
        raw = (filename or "").strip()
        if not raw:
            raise ExportInvalidFilename("Export filename is required.")
        # Output names are names, not paths. Reject traversal/absolute/UNC/ADS
        # instead of silently reducing them to a basename.
        windows = raw.replace("/", "\\")
        if raw in {".", ".."} or "/" in raw or "\\" in raw or windows.startswith("\\\\"):
            raise ExportInvalidFilename("Export filename cannot contain a path.")
        if len(windows) >= 2 and windows[0].isalpha() and windows[1] == ":":
            raise ExportInvalidFilename("Export filename cannot contain an absolute drive path.")
        if "\x00" in raw or ":" in raw:
            raise ExportInvalidFilename("Export filename contains unsafe characters.")
        name = Path(raw).name
        # Strip only the extension this method owns. Dots inside user text are
        # ordinary filename data and must not truncate later Unicode text.
        stem = name[:-len(extension)] if extension and name.lower().endswith(extension.lower()) else name
        stem = _INVALID.sub("_", stem).rstrip(" .")
        if stem in {"", ".", ".."}:
            raise ExportInvalidFilename("Export filename is invalid.")
        if stem.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
            raise ExportInvalidFilename("Export filename uses a reserved Windows device name.")
        return f"{stem}{extension}"

    def resolve(self, folder: str | Path, filename: str, policy: str = "keep_both") -> Path:
        root = Path(folder).expanduser().resolve()
        clean = self.sanitize(filename)
        try:
            target = safe_copy_destination(root, clean)
        except UnsafeManagedPath as exc:
            raise ExportInvalidFilename("Export destination is unsafe.") from exc
        if not target.exists():
            return target
        if policy == "replace":
            return target
        if policy == "cancel":
            raise ExportOutputConflict("A file with this name already exists.")
        if policy != "keep_both":
            raise ValueError("Unsupported file-conflict behavior.")
        for index in range(2, 10000):
            candidate = target.with_name(f"{target.stem}_{index}{target.suffix}")
            if not candidate.exists():
                return candidate
        raise ExportOutputConflict("Could not choose a unique export filename.")

    @staticmethod
    def is_managed(project_path: str | Path, output_path: str | Path) -> bool:
        project = Path(project_path).resolve()
        target = Path(output_path).resolve()
        roots = ((project / "renders").resolve(), (project / "exports").resolve())
        return any(target == root or root in target.parents for root in roots)

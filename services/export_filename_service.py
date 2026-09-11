from __future__ import annotations

import re
from pathlib import Path


class ExportInvalidFilename(ValueError):
    pass


class ExportOutputConflict(FileExistsError):
    pass


_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class ExportFilenameService:
    def sanitize(self, filename: str, *, extension: str = ".mp4") -> str:
        raw=(filename or "").strip()
        if not raw:
            raise ExportInvalidFilename("Export filename is required.")
        name=Path(raw).name
        stem=Path(name).stem if Path(name).suffix else name
        stem=_INVALID.sub("_",stem).rstrip(" .")
        if stem in {"", ".", ".."}:
            raise ExportInvalidFilename("Export filename is invalid.")
        # Windows reserved DOS device names are unsafe even with an extension.
        if stem.upper() in {"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}:
            stem=f"_{stem}"
        return f"{stem}{extension}"

    def resolve(self, folder: str | Path, filename: str, policy: str = "keep_both") -> Path:
        root=Path(folder).expanduser(); clean=self.sanitize(filename); target=root/clean
        if not target.exists(): return target
        if policy=="replace": return target
        if policy=="cancel": raise ExportOutputConflict("A file with this name already exists.")
        if policy!="keep_both": raise ValueError("Unsupported file-conflict behavior.")
        for index in range(2,10000):
            candidate=target.with_name(f"{target.stem}_{index}{target.suffix}")
            if not candidate.exists(): return candidate
        raise ExportOutputConflict("Could not choose a unique export filename.")

    @staticmethod
    def is_managed(project_path: str | Path, output_path: str | Path) -> bool:
        project=Path(project_path).resolve(); target=Path(output_path).resolve()
        roots=((project/"renders").resolve(),(project/"exports").resolve())
        return any(target==root or root in target.parents for root in roots)

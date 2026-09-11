from __future__ import annotations

import shutil
from pathlib import Path


class RenderTempManager:
    def __init__(self, project_path: str|Path, job_id: str) -> None:
        self.project_path=Path(project_path).resolve(); self.root=(self.project_path/"cache"/"render"/job_id).resolve()

    def prepare(self)->Path:
        self.root.mkdir(parents=True,exist_ok=True); return self.root

    def cleanup(self)->None:
        guard=(self.project_path/"cache"/"render").resolve()
        if self.root==guard or guard not in self.root.parents: raise RuntimeError("Unsafe render temp cleanup path.")
        shutil.rmtree(self.root,ignore_errors=True)

    @staticmethod
    def cleanup_stale(project_path:str|Path)->None:
        root=(Path(project_path).resolve()/"cache"/"render").resolve()
        if not root.is_dir(): return
        for child in root.iterdir():
            if child.is_dir(): shutil.rmtree(child,ignore_errors=True)

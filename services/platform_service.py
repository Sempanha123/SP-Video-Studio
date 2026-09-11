from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def reveal_in_folder(path: str | Path) -> None:
    target = Path(path)
    if sys.platform.startswith("win"):
        if target.exists() and target.is_file():
            subprocess.Popen(["explorer", "/select,", str(target)], shell=False)
        else:
            subprocess.Popen(["explorer", str(target.parent if target.suffix else target)], shell=False)
        return
    if sys.platform == "darwin":
        command = ["open", "-R", str(target)] if target.exists() else ["open", str(target.parent)]
        subprocess.Popen(command, shell=False)
        return
    folder = target if target.is_dir() else target.parent
    subprocess.Popen(["xdg-open", str(folder)], shell=False)

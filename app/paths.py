from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import APP_DATA_DIR_NAME


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    models: Path
    cache: Path
    temp: Path
    logs: Path
    settings: Path
    downloads: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        root = base / APP_DATA_DIR_NAME
        return cls(
            root=root,
            models=root / "models",
            cache=root / "cache",
            temp=root / "temp",
            logs=root / "logs",
            settings=root / "settings",
            downloads=root / "downloads",
        )

    def ensure(self) -> None:
        for directory in (
            self.root,
            self.models,
            self.cache,
            self.temp,
            self.logs,
            self.settings,
            self.downloads,
        ):
            directory.mkdir(parents=True, exist_ok=True)

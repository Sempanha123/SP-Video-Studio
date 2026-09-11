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

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    @property
    def voices(self) -> Path:
        return self.root / "voices"

    @property
    def templates(self) -> Path:
        return self.root / "templates"

    @property
    def assets(self) -> Path:
        return self.root / "assets"

    @property
    def recovery(self) -> Path:
        return self.root / "recovery"

    @property
    def database(self) -> Path:
        return self.data / "app.db"

    @property
    def default_projects_root(self) -> Path:
        return Path.home() / "Documents" / "SP Video Studio" / "Projects"

    def ensure(self) -> None:
        for directory in (
            self.root,
            self.models,
            self.cache,
            self.temp,
            self.logs,
            self.settings,
            self.downloads,
            self.exports,
            self.voices,
            self.templates,
            self.assets,
            self.recovery,
            self.data,
        ):
            directory.mkdir(parents=True, exist_ok=True)

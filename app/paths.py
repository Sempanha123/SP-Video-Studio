from __future__ import annotations

import os
import json
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
        default_cache = root / "cache"
        cache = default_cache
        # Phase 29 cache location is persisted separately so AppPaths remains the
        # single source used by existing media/render code after restart. A
        # malformed/tampered preference falls back to the safe managed default.
        try:
            settings_file = root / "settings" / "phase29_storage.json"
            data = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.is_file() else {}
            raw = str(data.get("cacheRoot") or "").strip() if isinstance(data, dict) else ""
            if raw:
                candidate = Path(raw).expanduser()
                resolved = candidate.resolve(strict=False)
                anchor = Path(resolved.anchor).resolve(strict=False) if resolved.anchor else None
                source_root = Path(__file__).resolve().parents[1]
                app_root = root.resolve(strict=False)
                unsafe_source = resolved == source_root or source_root in resolved.parents
                unsafe_system = False
                if os.name == "nt":
                    lowered = str(resolved).casefold().rstrip("\\/")
                    candidates = [os.environ.get("WINDIR"), os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
                    banned = [str(Path(item).resolve(strict=False)).casefold().rstrip("\\/") for item in candidates if item]
                    unsafe_system = any(lowered == item or lowered.startswith(item + "\\") for item in banned)
                if candidate.is_absolute() and resolved != app_root and (anchor is None or resolved != anchor) and not unsafe_source and not unsafe_system:
                    cache = resolved
        except (OSError, ValueError, json.JSONDecodeError):
            cache = default_cache
        return cls(
            root=root,
            models=root / "models",
            cache=cache,
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

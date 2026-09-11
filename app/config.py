from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    app_name: str = "SP Video Studio"
    theme: str = "system"
    locale: str = "en"
    log_level: str = "INFO"
    project_root: Path | None = None

from __future__ import annotations

import json
from pathlib import Path


class DiagnosticsPreferencesService:
    VERSION = 1
    VALID_SEVERITIES = {"all", "error", "warning", "info", "debug"}

    def __init__(self, settings_root: str | Path) -> None:
        self.path = Path(settings_root) / "phase36_diagnostics.json"
        self._data = self._load()

    @property
    def log_severity(self) -> str:
        value = str(self._data.get("logSeverity", "error")).lower()
        return value if value in self.VALID_SEVERITIES else "error"

    @property
    def log_limit(self) -> int:
        return max(50, min(2000, int(self._data.get("logLimit", 400) or 400)))

    def set_log_severity(self, value: str) -> None:
        value = str(value or "all").lower()
        if value not in self.VALID_SEVERITIES:
            raise ValueError("Unsupported log severity filter.")
        self._data["logSeverity"] = value
        self._save()

    def set_log_limit(self, value: int) -> None:
        self._data["logLimit"] = max(50, min(2000, int(value)))
        self._save()

    def _load(self) -> dict[str, object]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({"version": self.VERSION, **self._data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)

from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.json_writer import atomic_write_json, read_json


class SettingsRepository:
    """Versioned JSON settings persistence. Business validation lives in SettingsService."""

    def __init__(self, settings_file: Path) -> None:
        self.settings_file = Path(settings_file)

    def exists(self) -> bool:
        return self.settings_file.exists()

    def load(self) -> dict[str, Any] | None:
        if not self.exists():
            return None
        return read_json(self.settings_file)

    def save(self, payload: dict[str, Any]) -> None:
        atomic_write_json(self.settings_file, payload)

    def quarantine_invalid(self) -> Path | None:
        if not self.exists():
            return None
        candidate = self.settings_file.with_suffix(self.settings_file.suffix + ".invalid")
        index = 1
        while candidate.exists():
            candidate = self.settings_file.with_suffix(
                self.settings_file.suffix + f".invalid-{index}"
            )
            index += 1
        self.settings_file.replace(candidate)
        return candidate

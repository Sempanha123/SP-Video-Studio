from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock

from app.constants import APP_VERSION
from domain.update_state import UpdateState, UpdateStateCode


class UpdateStateService:
    def __init__(self, settings_root: Path, *, channel: str = "stable") -> None:
        self.path = Path(settings_root) / "updates.json"
        self._lock = RLock()
        self._state = self._load(channel)

    @property
    def current(self) -> UpdateState:
        return self._state

    def set_automatic_check(self, enabled: bool) -> UpdateState:
        self._state.automatic_check = bool(enabled)
        self.save()
        return self._state

    def update(self, **changes) -> UpdateState:
        for key, value in changes.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self.save()
        return self._state

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(self._state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self.path)

    def _load(self, channel: str) -> UpdateState:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            payload = {}
        state = UpdateState(
            current_version=APP_VERSION,
            channel="stable",
            automatic_check=bool(payload.get("automatic_check", True)),
            last_check_at=str(payload.get("last_check_at") or ""),
            last_error=str(payload.get("last_error") or "")[:500],
            last_installed_version=str(payload.get("last_installed_version") or ""),
        )
        # Transient download/install state is intentionally not resumed after a crash.
        state.state = UpdateStateCode.IDLE.value
        return state

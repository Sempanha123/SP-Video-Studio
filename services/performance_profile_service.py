from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from domain.performance import PerformanceProfile, PreviewPolicy, PreviewQuality

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


class PerformanceProfileService:
    VERSION = 1

    def __init__(self, settings_root: str | Path):
        self.path = Path(settings_root) / "phase31_performance.json"
        self._data = self._load()

    @property
    def profile(self) -> str:
        return str(self._data.get("profile", PerformanceProfile.AUTO.value))

    @property
    def preview_quality(self) -> str:
        return str(self._data.get("previewQuality", PreviewQuality.AUTO.value))

    @property
    def worker_limit(self) -> int:
        raw = int(self._data.get("workerLimit", 0) or 0)
        if raw > 0:
            return max(1, min(16, raw))
        return self.recommended_workers()

    def set_profile(self, value: str) -> None:
        value = str(value or "auto")
        if value not in {x.value for x in PerformanceProfile}:
            raise ValueError("Unsupported performance profile.")
        self._data["profile"] = value
        self._save()

    def set_preview_quality(self, value: str) -> None:
        value = str(value or "auto")
        if value not in {x.value for x in PreviewQuality}:
            raise ValueError("Unsupported preview quality.")
        self._data["previewQuality"] = value
        self._save()

    def set_worker_limit(self, value: int) -> None:
        self._data["workerLimit"] = max(0, min(16, int(value)))
        self._save()

    def effective_profile(self) -> str:
        if self.profile != PerformanceProfile.AUTO.value:
            return self.profile
        available = self._available_ram()
        cpus = max(1, os.cpu_count() or 1)
        if available and available < 6 * 1024**3:
            return PerformanceProfile.LOW_MEMORY.value
        if cpus <= 4:
            return PerformanceProfile.LOW_MEMORY.value
        return PerformanceProfile.BALANCED.value

    def recommended_workers(self) -> int:
        profile = self.effective_profile()
        cpus = max(1, os.cpu_count() or 1)
        if profile == PerformanceProfile.LOW_MEMORY.value:
            return 2
        if profile == PerformanceProfile.MAXIMUM_QUALITY.value:
            return min(6, max(2, cpus // 2))
        return min(4, max(2, cpus // 2))

    def preview_policy(self, *, active_layers: int = 1, source_height: int = 1080) -> PreviewPolicy:
        mode = self.preview_quality
        profile = self.effective_profile()
        if mode == PreviewQuality.QUALITY.value:
            return PreviewPolicy(mode, min(1080, max(720, source_height)), True, "high", 4)
        if mode == PreviewQuality.PERFORMANCE.value or profile == PerformanceProfile.LOW_MEMORY.value:
            return PreviewPolicy(mode, min(540, max(360, source_height)), active_layers <= 2, "low", 2)
        # Auto: complex layered scenes get a lighter temporary preview only.
        if active_layers >= 4 or source_height > 1440:
            return PreviewPolicy("auto", 540, False, "low", 2)
        return PreviewPolicy("auto", min(720, max(360, source_height)), True, "medium", 3)

    def _available_ram(self) -> int:
        try:
            return int(psutil.virtual_memory().available) if psutil else 0
        except Exception:
            return 0

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"version": self.VERSION, **self._data}, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

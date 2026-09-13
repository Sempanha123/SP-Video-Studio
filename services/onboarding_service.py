from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domain.onboarding import ONBOARDING_STEPS, ONBOARDING_VERSION, OnboardingState, OnboardingStatus
from services.first_run_service import FirstRunService


class OnboardingError(RuntimeError):
    pass


class OnboardingService:
    """Small persisted first-run state layered over existing settings/readiness/model/project services."""

    def __init__(
        self,
        paths,
        settings_service,
        project_service,
        language_service,
        readiness_service,
        model_service=None,
        performance_service=None,
        disk_monitor=None,
        logger=None,
    ) -> None:
        self.paths = paths
        self.settings = settings_service
        self.projects = project_service
        self.languages = language_service
        self.readiness = readiness_service
        self.models = model_service
        self.performance = performance_service
        self.disk_monitor = disk_monitor
        self.logger = logger
        self.path = Path(paths.settings) / "phase35_onboarding.json"
        self.first_run = FirstRunService(settings_service, project_service, paths.default_projects_root)
        self._state = self._load_or_initialize()

    @property
    def state(self) -> OnboardingState:
        return self._state

    @property
    def should_show(self) -> bool:
        return self._state.status in {OnboardingStatus.NOT_STARTED.value, OnboardingStatus.IN_PROGRESS.value}

    def begin(self, *, restart: bool = False) -> OnboardingState:
        if restart:
            self._state.current_step = 0
        self._state.status = OnboardingStatus.IN_PROGRESS.value
        return self._save()

    def set_step(self, index: int) -> OnboardingState:
        self._state.status = OnboardingStatus.IN_PROGRESS.value
        self._state.current_step = max(0, min(int(index), len(ONBOARDING_STEPS) - 1))
        return self._save()

    def next_step(self) -> OnboardingState:
        return self.set_step(self._state.current_step + 1)

    def previous_step(self) -> OnboardingState:
        return self.set_step(self._state.current_step - 1)

    def skip(self) -> OnboardingState:
        self._state.status = OnboardingStatus.SKIPPED.value
        self._state.current_step = len(ONBOARDING_STEPS) - 1
        return self._save()

    def complete(self, first_project_id: str = "") -> OnboardingState:
        self._state.status = OnboardingStatus.COMPLETED.value
        self._state.current_step = len(ONBOARDING_STEPS) - 1
        if first_project_id:
            self._state.first_project_id = str(first_project_id)
        return self._save()

    def reopen(self) -> OnboardingState:
        # Review/change settings only. Existing projects/assets/models are never reset here.
        self._state.status = OnboardingStatus.IN_PROGRESS.value
        self._state.current_step = 0
        return self._save()

    def set_content_language(self, code: str) -> OnboardingState:
        code = str(code or "").strip()
        self.languages.get(code)
        self._state.default_project_language = code
        return self._save()

    def set_theme(self, theme: str) -> None:
        self.settings.update(theme=str(theme or "system"))

    def set_reduce_motion(self, enabled: bool) -> None:
        self.settings.update(reduce_motion="on" if bool(enabled) else "system")

    def set_large_text(self, enabled: bool) -> None:
        self.settings.update(interface_text_size="large" if bool(enabled) else "default")

    def set_performance_profile(self, profile: str) -> None:
        value = str(profile or "auto")
        self.settings.update(performance_profile=value)
        if self.performance is not None:
            try:
                self.performance.set_profile(value)
            except Exception:
                if self.logger:
                    self.logger.info("Phase 31 performance profile sync unavailable", exc_info=True)

    def validate_project_folder(self, value: str | Path) -> dict[str, Any]:
        try:
            target = self.settings.validate_directory(value, create=True)
            resolved = target.resolve(strict=False)
            anchor = Path(resolved.anchor).resolve(strict=False) if resolved.anchor else None
            if anchor is not None and resolved == anchor:
                raise OnboardingError("Choose a folder inside a drive, not the drive root itself.")
            if self.disk_monitor is not None:
                status = self.disk_monitor.check(resolved, label="Projects")
                free_bytes = int(status.free_bytes)
                disk_state = str(getattr(status.state, "value", status.state))
            else:
                usage = shutil.disk_usage(resolved)
                free_bytes = int(usage.free)
                disk_state = "normal"
            return {
                "valid": True,
                "path": str(resolved),
                "freeBytes": free_bytes,
                "freeGb": round(float(free_bytes) / 1024**3, 1),
                "diskState": disk_state,
                "message": f"{float(free_bytes) / 1024**3:.1f} GB available",
            }
        except Exception as exc:
            return {"valid": False, "path": str(value or ""), "freeBytes": 0, "freeGb": 0.0, "message": str(exc) or "This folder cannot be used for projects."}

    def set_project_folder(self, value: str | Path) -> dict[str, Any]:
        check = self.validate_project_folder(value)
        if not check["valid"]:
            return check
        settings = self.settings.set_project_folder(str(check["path"]))
        self.projects.set_project_root(Path(settings.default_projects_folder))
        return check

    def readiness_snapshot(self) -> dict[str, Any]:
        try:
            data = self.readiness.detect().to_dict()
        except Exception as exc:
            if self.logger:
                self.logger.exception("Onboarding readiness check failed")
            return {"overallStatus": "unknown", "warnings": [str(exc) or "System readiness could not be checked."]}
        data["cpuModeMessage"] = (
            "GPU acceleration available."
            if data.get("gpuStatus") == "ready"
            else "CPU mode available. AI features may run more slowly, but video editing still works."
        )
        data["renderingMessage"] = (
            "FFmpeg ready."
            if data.get("ffmpegAvailable")
            else "Rendering is unavailable until FFmpeg is configured. You can still enter the editor and work manually."
        )
        return data

    def model_snapshot(self) -> list[dict[str, Any]]:
        if self.models is None:
            return []
        try:
            rows = self.models.refresh()
        except Exception:
            if self.logger:
                self.logger.info("Model discovery unavailable during onboarding", exc_info=True)
            return []
        result = []
        for row in rows:
            item = dict(row)
            item["onboardingStatus"] = "Installed" if bool(item.get("installed")) else ("Model Required" if item.get("compatibility") not in {"unsupported", "incompatible"} else "Unsupported on Current Setup")
            result.append(item)
        return result

    def mark_continue_without_ai(self) -> OnboardingState:
        self._state.continue_without_ai = True
        return self._save()

    def record_first_project(self, project_id: str) -> OnboardingState:
        self._state.first_project_id = str(project_id or "")
        return self._save()

    def dismiss_tip(self, tip_id: str) -> OnboardingState:
        value = str(tip_id or "").strip()
        if value and value not in self._state.dismissed_tips:
            self._state.dismissed_tips.append(value)
        return self._save()

    def should_show_tip(self, tip_id: str) -> bool:
        return str(tip_id or "") not in self._state.dismissed_tips

    def languages_for_setup(self) -> list[dict[str, Any]]:
        rows = self.languages.list_languages("")
        preferred = {"en": 0, "km": 1, "th": 2, "vi": 3}
        return sorted(rows, key=lambda row: (preferred.get(str(row.get("code", "")), 100), str(row.get("displayName") or row.get("name") or "")))

    def summary(self) -> dict[str, Any]:
        ready = self.readiness_snapshot()
        return {
            "projectsFolder": self.settings.current.default_projects_folder,
            "contentLanguage": self._state.default_project_language,
            "theme": self.settings.current.theme,
            "ffmpeg": "Ready" if ready.get("ffmpegAvailable") else "Needs Setup",
            "voiceAI": "Installed" if ready.get("voxcpmStatus") == "installed" else "Not installed",
            "speechRecognition": "Installed" if ready.get("whisperStatus") == "installed" else "Not installed",
        }

    def _load_or_initialize(self) -> OnboardingState:
        if self.path.is_file():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                state = OnboardingState.from_dict(payload if isinstance(payload, dict) else {})
                if state.onboarding_version < ONBOARDING_VERSION:
                    state.onboarding_version = ONBOARDING_VERSION
                    self._state = state
                    return self._save()
                return state
            except Exception:
                if self.logger:
                    self.logger.exception("Invalid onboarding state; preserving it and recreating safely")
                try:
                    self.path.replace(self.path.with_suffix(".invalid.json"))
                except OSError:
                    pass
        self._state = self.first_run.initial_state()
        return self._save()

    def _save(self) -> OnboardingState:
        self._state.onboarding_version = ONBOARDING_VERSION
        self._state.updated_at = datetime.now(timezone.utc).isoformat()
        self._state.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)
        return self._state

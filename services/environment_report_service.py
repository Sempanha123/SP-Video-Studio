from __future__ import annotations

import importlib.metadata
import platform
from typing import Any

from services.log_redaction_service import LogRedactionService


class EnvironmentReportService:
    def __init__(self, paths, settings_service, redaction: LogRedactionService, database=None, model_service=None) -> None:
        self.paths = paths
        self.settings_service = settings_service
        self.redaction = redaction
        self.database = database
        self.model_service = model_service

    def app_version(self) -> str:
        try:
            return importlib.metadata.version("sp-video-studio")
        except importlib.metadata.PackageNotFoundError:
            return "0.1.0"

    def system_summary(self) -> dict[str, Any]:
        return {
            "appVersion": self.app_version(),
            "os": platform.system() or "Unknown",
            "osVersion": platform.release() or platform.version() or "Unknown",
            "architecture": platform.machine() or "Unknown",
            "python": platform.python_version(),
        }

    def settings_summary(self) -> dict[str, Any]:
        s = self.settings_service.current
        # Deliberate allow-list: never serialize the raw settings payload into a bundle.
        result = {
            "language": getattr(s, "language", "en"),
            "theme": getattr(s, "theme", "system"),
            "performanceProfile": getattr(s, "performance_profile", "auto"),
            "defaultFps": getattr(s, "default_fps", 30),
            "defaultAspectRatio": getattr(s, "default_aspect_ratio", "16:9"),
            "ffmpegMode": getattr(s, "ffmpeg_mode", "auto"),
            "projectsFolder": getattr(s, "default_projects_folder", ""),
            "reduceMotion": getattr(s, "reduce_motion", "system"),
            "interfaceTextSize": getattr(s, "interface_text_size", "default"),
        }
        return self.redaction.redact_value(result)

    def database_summary(self) -> dict[str, Any]:
        if self.database is None:
            return {"available": False, "schemaVersion": 0}
        try:
            return {"available": True, "schemaVersion": int(self.database.current_version())}
        except Exception as exc:
            return {"available": False, "schemaVersion": 0, "error": self.redaction.redact_text(str(exc))}

    def model_summary(self) -> list[dict[str, Any]]:
        service = self.model_service
        if service is None:
            return []
        rows: list[dict[str, Any]] = []
        for model in service.registry.list_all():
            installation = service.repository.get(model.model_id)
            install_path = service.install_path(model)
            rows.append({
                "id": model.model_id,
                "family": model.family,
                "purpose": model.purpose_code,
                "version": model.version,
                "installed": bool(getattr(installation, "installed", False)),
                "status": str(getattr(installation, "status", "not_installed")),
                "verified": str(getattr(installation, "verification_status", "unknown")),
                "path": self.redaction.sanitize_paths(str(install_path)),
            })
        return rows

    def build(self) -> dict[str, Any]:
        return self.redaction.redact_value({
            "system": self.system_summary(),
            "settings": self.settings_summary(),
            "database": self.database_summary(),
            "models": self.model_summary(),
        })

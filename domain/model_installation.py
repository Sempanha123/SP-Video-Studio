from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from domain.project import utc_now_iso


MODEL_MANIFEST_SCHEMA_VERSION = 1


class ModelInstallStatus(StrEnum):
    NOT_INSTALLED = "not_installed"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    INSTALLING = "installing"
    VERIFYING = "verifying"
    INSTALLED = "installed"
    REPAIR_REQUIRED = "repair_required"
    FAILED = "failed"
    REMOVING = "removing"


class VerificationStatus(StrEnum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass(slots=True)
class ModelInstallation:
    model_id: str
    installed: bool = False
    status: str | ModelInstallStatus = ModelInstallStatus.NOT_INSTALLED
    install_path: str = ""
    installed_version: str = ""
    downloaded_bytes: int = 0
    total_bytes: int = 0
    installed_at: str | None = None
    verified_at: str | None = None
    verification_status: str | VerificationStatus = VerificationStatus.UNKNOWN
    error_message: str = ""
    is_loaded: bool = False
    in_use_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def status_code(self) -> str:
        return str(self.status)

    @property
    def verification_code(self) -> str:
        return str(self.verification_status)

    @property
    def progress(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return max(0.0, min(1.0, self.downloaded_bytes / self.total_bytes))

    def to_record(self) -> tuple[object, ...]:
        return (
            self.model_id,
            1 if self.installed else 0,
            self.status_code,
            self.install_path,
            self.installed_version,
            int(self.downloaded_bytes),
            int(self.total_bytes),
            self.installed_at,
            self.verified_at,
            self.verification_code,
            self.error_message,
            1 if self.is_loaded else 0,
            int(self.in_use_count),
            json.dumps(self.metadata, ensure_ascii=False, sort_keys=True),
            self.updated_at,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "ModelInstallation":
        try:
            metadata = json.loads(record["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return cls(
            model_id=str(record["model_id"]),
            installed=bool(record["installed"]),
            status=str(record["status"]),
            install_path=str(record["install_path"] or ""),
            installed_version=str(record["installed_version"] or ""),
            downloaded_bytes=int(record["downloaded_bytes"] or 0),
            total_bytes=int(record["total_bytes"] or 0),
            installed_at=record["installed_at"],
            verified_at=record["verified_at"],
            verification_status=str(record["verification_status"] or VerificationStatus.UNKNOWN),
            error_message=str(record["error_message"] or ""),
            is_loaded=bool(record["is_loaded"]),
            in_use_count=int(record["in_use_count"] or 0),
            metadata=dict(metadata) if isinstance(metadata, dict) else {},
            updated_at=str(record["updated_at"] or utc_now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelId": self.model_id,
            "installed": self.installed,
            "status": self.status_code,
            "installPath": self.install_path,
            "installedVersion": self.installed_version,
            "downloadedBytes": self.downloaded_bytes,
            "totalBytes": self.total_bytes,
            "progress": self.progress,
            "installedAt": self.installed_at or "",
            "verifiedAt": self.verified_at or "",
            "verificationStatus": self.verification_code,
            "errorMessage": self.error_message,
            "isLoaded": self.is_loaded,
            "inUseCount": self.in_use_count,
            "metadata": dict(self.metadata),
            "updatedAt": self.updated_at,
        }

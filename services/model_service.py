from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Callable

from domain.ai_model import AIModel, ModelCompatibility
from domain.model_installation import ModelInstallation, ModelInstallStatus, VerificationStatus
from domain.project import utc_now_iso
from domain.system_readiness import SystemReadiness, format_bytes
from engines.model_registry import ModelRegistry
from engines.model_sources import DownloadCancelled
from services.model_compatibility_service import ModelCompatibilityService
from services.model_download_service import ModelDownloadProgress, ModelDownloadService, ModelDownloadError
from services.model_verification_service import ModelVerificationService
from services.platform_service import reveal_in_folder
from storage.repositories.model_repository import ModelRepository
from workers.cancellation import CancellationToken


class ModelError(RuntimeError):
    user_message = "MMO Video Studio could not complete this model action."


class ModelDiskSpaceError(ModelError):
    user_message = "Not enough disk space to install this model."


class ModelBusyError(ModelError):
    user_message = "This model is currently in use and cannot be removed."


class ModelService:
    """Application-facing local AI model manager. No inference occurs here."""

    def __init__(
        self,
        registry: ModelRegistry,
        repository: ModelRepository,
        download_service: ModelDownloadService,
        verification_service: ModelVerificationService,
        compatibility_service: ModelCompatibilityService,
        model_root: Path,
        logger: logging.Logger | None = None,
    ) -> None:
        self.registry = registry
        self.repository = repository
        self.download_service = download_service
        self.verification_service = verification_service
        self.compatibility_service = compatibility_service
        self.model_root = Path(model_root)
        self.logger = logger or logging.getLogger("sp_video_studio.models")
        self._runtime: dict[str, ModelInstallation] = {}

    def refresh(self, readiness: SystemReadiness | None = None) -> list[dict[str, object]]:
        self.model_root.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, object]] = []
        for model in self.registry.list_all():
            installation = self._refresh_one(model)
            self._runtime[model.model_id] = installation
            assessment = self.compatibility_service.assess(model, readiness)
            results.append(self._view(model, installation, assessment.status, assessment.summary, assessment.warnings, readiness))
        return results

    def install(
        self,
        model_id: str,
        cancellation: CancellationToken,
        progress_callback: Callable[[ModelDownloadProgress], None] | None = None,
    ) -> ModelInstallation:
        model = self.registry.get(model_id)
        self._ensure_disk_space(model)
        current = self.repository.get(model_id) or ModelInstallation(model_id=model_id)
        current.installed = False
        current.status = ModelInstallStatus.DOWNLOADING
        current.install_path = str(self.install_path(model))
        current.installed_version = ""
        current.downloaded_bytes = 0
        current.total_bytes = model.download_size_bytes
        current.error_message = ""
        self.repository.upsert(current)
        self._runtime[model_id] = current
        self.logger.info("Model download started: %s", model_id)
        try:
            final_path = self.download_service.install(model, cancellation, progress_callback)
        except DownloadCancelled:
            current.status = ModelInstallStatus.PAUSED
            current.error_message = "Download paused. Partial files can be resumed."
            self.repository.upsert(current)
            self.logger.info("Model download cancelled: %s", model_id)
            raise
        except Exception as exc:
            current.status = ModelInstallStatus.FAILED
            current.error_message = _friendly_download_error(exc)
            self.repository.upsert(current)
            self.logger.exception("Model installation failed: %s", model_id)
            raise ModelError(current.error_message) from exc

        verification = self.verification_service.verify(model, final_path)
        if not verification.valid:
            current.status = ModelInstallStatus.REPAIR_REQUIRED
            current.install_path = str(final_path)
            current.error_message = "; ".join(verification.errors[:3])
            current.verification_status = VerificationStatus.FAILED
            self.repository.upsert(current)
            raise ModelError("The model was downloaded but verification failed. Repair is required.")
        now = utc_now_iso()
        current.installed = True
        current.status = ModelInstallStatus.INSTALLED
        current.install_path = str(final_path)
        current.installed_version = model.version
        current.downloaded_bytes = _directory_size(final_path)
        current.total_bytes = current.downloaded_bytes
        current.installed_at = current.installed_at or now
        current.verified_at = now
        current.verification_status = VerificationStatus.VERIFIED
        current.error_message = ""
        current.metadata["source_identifier"] = model.source_identifier
        self.repository.upsert(current)
        self._runtime[model_id] = current
        self.logger.info("Model download completed and verified: %s", model_id)
        return current

    def verify(self, model_id: str) -> ModelInstallation:
        model = self.registry.get(model_id)
        current = self.repository.get(model_id) or ModelInstallation(model_id=model_id)
        path = self.install_path(model)
        current.status = ModelInstallStatus.VERIFYING
        self.repository.upsert(current)
        self.logger.info("Model verification started: %s", model_id)
        result = self.verification_service.verify(model, path)
        now = utc_now_iso()
        current.install_path = str(path)
        current.verified_at = now
        if result.valid:
            current.installed = True
            current.status = ModelInstallStatus.INSTALLED
            current.installed_version = model.version
            current.verification_status = VerificationStatus.VERIFIED
            current.error_message = ""
            current.installed_at = current.installed_at or now
        else:
            current.installed = False
            current.status = ModelInstallStatus.REPAIR_REQUIRED if path.exists() else ModelInstallStatus.NOT_INSTALLED
            current.verification_status = VerificationStatus.FAILED
            current.error_message = "; ".join(result.errors[:3])
        self.repository.upsert(current)
        self._runtime[model_id] = current
        self.logger.info("Model verification %s: %s", "completed" if result.valid else "failed", model_id)
        return current

    def repair(
        self,
        model_id: str,
        cancellation: CancellationToken,
        progress_callback: Callable[[ModelDownloadProgress], None] | None = None,
    ) -> ModelInstallation:
        self.logger.info("Model repair started: %s", model_id)
        return self.install(model_id, cancellation, progress_callback)

    def remove(self, model_id: str) -> None:
        model = self.registry.get(model_id)
        current = self.repository.get(model_id)
        if current and (current.is_loaded or current.in_use_count > 0):
            raise ModelBusyError()
        target = self.install_path(model)
        self._assert_safe_managed_model_path(model, target)
        partial = self.download_service.partial_path(model_id)
        if partial.exists():
            self.download_service.remove_partial(model_id)
        if target.exists():
            shutil.rmtree(target)
        self.repository.remove(model_id)
        self._runtime.pop(model_id, None)
        self.logger.info("Model removed: %s", model_id)

    def open_folder(self, model_id: str) -> None:
        model = self.registry.get(model_id)
        target = self.install_path(model)
        self._assert_safe_managed_model_path(model, target)
        target.mkdir(parents=True, exist_ok=True)
        reveal_in_folder(target)

    def remove_partial(self, model_id: str) -> None:
        self.registry.get(model_id)
        self.download_service.remove_partial(model_id)
        current = self.repository.get(model_id)
        if current and current.status in {ModelInstallStatus.PAUSED, ModelInstallStatus.FAILED, ModelInstallStatus.DOWNLOADING}:
            current.status = ModelInstallStatus.NOT_INSTALLED
            current.downloaded_bytes = 0
            current.error_message = ""
            self.repository.upsert(current)

    def install_path(self, model: AIModel) -> Path:
        root = self.model_root.resolve()
        target = (self.model_root / model.install_relative_path).resolve()
        if target == root or root not in target.parents:
            raise ModelError("Unsafe model installation path.")
        return target

    def family_status(self, family: str) -> str:
        states: list[str] = []
        for model in self.registry.list_family(family):
            installation = self.repository.get(model.model_id)
            path = self.install_path(model)
            if installation and installation.status == ModelInstallStatus.INSTALLED and path.is_dir() and (path / "model_manifest.json").is_file():
                states.append("installed")
            elif installation and installation.status == ModelInstallStatus.REPAIR_REQUIRED:
                states.append("repair-required")
            elif path.exists():
                states.append("repair-required")
            else:
                states.append("not-installed")
        if "installed" in states:
            return "installed"
        if "repair-required" in states:
            return "repair-required"
        return "not-installed"

    def total_storage_bytes(self) -> int:
        return sum(_directory_size(self.install_path(model)) for model in self.registry.list_all())

    def _refresh_one(self, model: AIModel) -> ModelInstallation:
        current = self.repository.get(model.model_id) or ModelInstallation(model_id=model.model_id)
        final_path = self.install_path(model)
        partial_path = self.download_service.partial_path(model.model_id)
        if final_path.exists():
            verification = self.verification_service.verify(model, final_path)
            current.install_path = str(final_path)
            if verification.valid:
                current.installed = True
                current.status = ModelInstallStatus.INSTALLED
                current.installed_version = model.version
                current.verification_status = VerificationStatus.VERIFIED
                current.error_message = ""
                current.installed_at = current.installed_at or utc_now_iso()
                current.verified_at = current.verified_at or utc_now_iso()
            else:
                current.installed = False
                current.status = ModelInstallStatus.REPAIR_REQUIRED
                current.verification_status = VerificationStatus.FAILED
                current.error_message = "; ".join(verification.errors[:3])
            self.repository.upsert(current)
            return current
        if partial_path.exists() and any(partial_path.rglob("*")):
            current.installed = False
            current.status = ModelInstallStatus.PAUSED
            current.error_message = "Download interrupted. Resume, restart, or remove the partial download."
            current.downloaded_bytes = _directory_size(partial_path)
            current.total_bytes = max(current.total_bytes, model.download_size_bytes)
            self.repository.upsert(current)
            return current
        if current.status != ModelInstallStatus.NOT_INSTALLED or current.installed:
            current.installed = False
            current.status = ModelInstallStatus.NOT_INSTALLED
            current.install_path = str(final_path)
            current.verification_status = VerificationStatus.UNKNOWN
            current.error_message = ""
            self.repository.upsert(current)
        return current

    def _view(
        self,
        model: AIModel,
        installation: ModelInstallation,
        compatibility: ModelCompatibility,
        compatibility_summary: str,
        compatibility_warnings: tuple[str, ...],
        readiness: SystemReadiness | None,
    ) -> dict[str, object]:
        payload = model.to_dict()
        payload.update(installation.to_dict())
        payload["statusDisplay"] = installation.status_code.replace("_", " ").title()
        payload["downloadSizeDisplay"] = format_bytes(model.download_size_bytes)
        payload["diskSizeDisplay"] = format_bytes(model.disk_size_bytes)
        payload["downloadedDisplay"] = format_bytes(installation.downloaded_bytes)
        payload["totalDisplay"] = format_bytes(installation.total_bytes or model.download_size_bytes)
        payload["diskUsageBytes"] = _directory_size(self.install_path(model))
        payload["diskUsageDisplay"] = format_bytes(int(payload["diskUsageBytes"]))
        payload["compatibility"] = str(compatibility)
        payload["compatibilityDisplay"] = compatibility_summary
        payload["compatibilityWarnings"] = list(compatibility_warnings)
        payload["recommended"] = self._is_recommended(model, readiness)
        return payload

    def _is_recommended(self, model: AIModel, readiness: SystemReadiness | None) -> bool:
        if model.family == "voxcpm2":
            return True
        if model.family != "faster-whisper" or readiness is None:
            return model.model_id == "whisper-small"
        ram = readiness.ram_total or 0
        gpu = readiness.gpu_memory_total or 0
        gib = 1024**3
        if ram >= 16 * gib and readiness.cuda_status == "available" and gpu >= 6 * gib:
            return model.model_id == "whisper-large-v3"
        if ram >= 12 * gib:
            return model.model_id == "whisper-medium"
        return model.model_id == "whisper-small"

    def _ensure_disk_space(self, model: AIModel) -> None:
        self.model_root.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(self.model_root)
        required = int(max(model.download_size_bytes, model.disk_size_bytes) * 1.20)
        if usage.free < required:
            raise ModelDiskSpaceError(
                f"Not enough disk space. {format_bytes(required)} required; {format_bytes(usage.free)} available."
            )

    def _assert_safe_managed_model_path(self, model: AIModel, target: Path) -> None:
        expected = self.install_path(model)
        root = self.model_root.resolve()
        resolved = target.resolve()
        if resolved != expected or resolved == root or root not in resolved.parents:
            raise ModelError("Refusing to remove a path outside the managed model directory.")
        if resolved == Path(resolved.anchor):
            raise ModelError("Refusing to remove a drive root.")


def _directory_size(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _friendly_download_error(exc: Exception) -> str:
    text = str(exc).strip()
    if isinstance(exc, ModelDownloadError):
        return text or "Model installation failed."
    return text or "Model installation failed."

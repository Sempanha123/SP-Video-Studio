from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Callable

from app.constants import APP_VERSION
from domain.update_manifest import UpdateManifest, compare_versions
from domain.update_state import UpdateStateCode
from services.update_download_service import UpdateDownloadCancelled, UpdateDownloadError, UpdateDownloadService
from services.update_manifest_service import UpdateCheckError, UpdateManifestService
from services.update_state_service import UpdateStateService
from services.update_validation_service import UpdateValidationError, UpdateValidationService


class UpdateBlockedError(RuntimeError):
    pass


class UpdateInstallError(RuntimeError):
    pass


class UpdateService:
    OFFLINE_MESSAGE = "Could not check for updates."

    def __init__(
        self,
        state: UpdateStateService,
        manifests: UpdateManifestService,
        downloads: UpdateDownloadService,
        validation: UpdateValidationService,
        staging_root: Path,
        *,
        active_work_provider: Callable[[], list[str]] | None = None,
        flush_callback: Callable[[], bool] | None = None,
        launcher: Callable[[list[str]], object] | None = None,
        logger=None,
    ) -> None:
        self.state_service = state
        self.manifests = manifests
        self.downloads = downloads
        self.validation = validation
        self.staging_root = Path(staging_root)
        self.active_work_provider = active_work_provider or (lambda: [])
        self.flush_callback = flush_callback or (lambda: True)
        self.launcher = launcher or self._launch
        self.logger = logger
        self.manifest: UpdateManifest | None = None
        self.pending_marker = self.staging_root / "pending-update.json"

    @property
    def state(self):
        return self.state_service.current

    def check(self) -> UpdateManifest | None:
        self.state_service.update(state=UpdateStateCode.CHECKING.value, last_error="", progress=0.0)
        try:
            manifest = self.manifests.fetch()
        except UpdateCheckError as exc:
            self.state_service.update(
                state=UpdateStateCode.ERROR.value,
                last_check_at=self._now(),
                last_error=self._safe_error(exc, offline=True),
            )
            return None
        self.manifest = manifest
        comparison = compare_versions(manifest.version, APP_VERSION)
        if comparison > 0:
            self.state_service.update(
                state=UpdateStateCode.AVAILABLE.value,
                available_version=manifest.version,
                last_check_at=self._now(),
                last_error="",
                installer_validated=False,
                staged_installer="",
            )
            return manifest
        # Same and older manifests never trigger an automatic downgrade path.
        self.state_service.update(
            state=UpdateStateCode.UP_TO_DATE.value,
            available_version="",
            last_check_at=self._now(),
            last_error="",
            installer_validated=False,
            staged_installer="",
        )
        return None

    def download(self, *, cancellation=None, progress=None) -> Path:
        manifest = self._require_manifest()
        self.state_service.update(state=UpdateStateCode.DOWNLOADING.value, progress=0.0, last_error="")
        def report(value: float) -> None:
            self.state_service.update(progress=float(value))
            if progress:
                progress(float(value))
        try:
            path = self.downloads.download(manifest, cancellation=cancellation, progress=report)
            self.state_service.update(state=UpdateStateCode.VALIDATING.value)
            self.validation.validate(path, manifest)
        except (UpdateDownloadCancelled, UpdateDownloadError, UpdateValidationError) as exc:
            # Any failed/altered installer is removed before returning control to editing.
            try:
                if 'path' in locals():
                    Path(path).unlink(missing_ok=True)
            finally:
                self.state_service.update(
                    state=UpdateStateCode.AVAILABLE.value if isinstance(exc, UpdateDownloadCancelled) else UpdateStateCode.ERROR.value,
                    progress=0.0,
                    staged_installer="",
                    installer_validated=False,
                    last_error=self._safe_error(exc),
                )
            raise
        self.state_service.update(
            state=UpdateStateCode.READY.value,
            progress=1.0,
            staged_installer=str(path),
            installer_validated=True,
            last_error="",
        )
        return path

    def active_work(self) -> list[str]:
        try:
            return [str(item) for item in self.active_work_provider() if str(item)]
        except Exception:
            return ["background work"]

    def install_ready_update(self) -> Path:
        manifest = self._require_manifest()
        if self.state.state != UpdateStateCode.READY.value or not self.state.installer_validated:
            raise UpdateInstallError("The update installer has not been validated")
        active = self.active_work()
        if active:
            raise UpdateBlockedError("Finish or pause active work before installing the update: " + ", ".join(active))
        path = Path(self.state.staged_installer)
        # Revalidate immediately before execution so a staged installer cannot be replaced after download.
        self.validation.validate(path, manifest)
        if self.flush_callback() is False:
            raise UpdateBlockedError("Your latest changes could not be saved. The update was not started.")
        self.staging_root.mkdir(parents=True, exist_ok=True)
        marker = {
            "fromVersion": APP_VERSION,
            "toVersion": manifest.version,
            "createdAt": self._now(),
            "installer": path.name,
        }
        self._atomic_json(self.pending_marker, marker)
        try:
            self.state_service.update(state=UpdateStateCode.INSTALLING.value, last_error="")
            self.launcher([str(path)])
        except Exception as exc:
            self.pending_marker.unlink(missing_ok=True)
            self.state_service.update(state=UpdateStateCode.READY.value, last_error=self._safe_error(exc))
            raise UpdateInstallError("The validated installer could not be launched") from exc
        return path

    def finalize_post_update(self) -> dict | None:
        if not self.pending_marker.is_file():
            return None
        try:
            marker = json.loads(self.pending_marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.pending_marker.unlink(missing_ok=True)
            return None
        target = str(marker.get("toVersion") or "")
        # Called after normal startup DB migrations have completed. Only finalize if this binary is the intended/newer version.
        try:
            updated = compare_versions(APP_VERSION, str(marker.get("fromVersion") or "0.0.0")) > 0
            target_ok = not target or compare_versions(APP_VERSION, target) >= 0
        except Exception:
            updated = target_ok = False
        if not (updated and target_ok):
            return None
        completed = self.staging_root / "last-update.json"
        marker["completedAt"] = self._now()
        marker["installedVersion"] = APP_VERSION
        self._atomic_json(completed, marker)
        self.pending_marker.unlink(missing_ok=True)
        self.state_service.update(last_installed_version=APP_VERSION, state=UpdateStateCode.IDLE.value)
        return marker

    def cleanup_stale(self, *, older_than_days: int = 14) -> int:
        if self.state.state in {UpdateStateCode.DOWNLOADING.value, UpdateStateCode.VALIDATING.value, UpdateStateCode.INSTALLING.value}:
            return 0
        self.staging_root.mkdir(parents=True, exist_ok=True)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(older_than_days)))
        removed = 0
        keep = {self.pending_marker.name, "last-update.json"}
        for path in self.staging_root.iterdir():
            if path.name in keep or not path.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if mtime < cutoff:
                    path.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                continue
        return removed

    def set_automatic_check(self, enabled: bool) -> None:
        self.state_service.set_automatic_check(enabled)

    def _require_manifest(self) -> UpdateManifest:
        if self.manifest is None or compare_versions(self.manifest.version, APP_VERSION) <= 0:
            raise UpdateInstallError("No newer validated update manifest is available")
        return self.manifest

    @staticmethod
    def _launch(args: list[str]):
        return subprocess.Popen(args, shell=False, close_fds=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _safe_error(cls, exc: Exception, *, offline: bool = False) -> str:
        if offline or str(exc).strip() == cls.OFFLINE_MESSAGE:
            return cls.OFFLINE_MESSAGE
        text = str(exc).replace("\r", " ").replace("\n", " ").strip()
        return text[:500] or exc.__class__.__name__

    @staticmethod
    def _atomic_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)

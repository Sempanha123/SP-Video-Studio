from __future__ import annotations

"""Phase 42 secure update layer over Phase 40 packaging + Phase 38 migrations."""

from pathlib import Path
import app.phase31_runtime as p31
from app.update_config import (
    EXPECTED_UPDATE_SIGNER_SUBJECT,
    UPDATE_CHANNEL,
    UPDATE_HTTP_TIMEOUT_SECONDS,
    UPDATE_MANIFEST_URL,
    UPDATE_MAX_MANIFEST_BYTES,
    UPDATE_STALE_AFTER_DAYS,
)
from app.paths import AppPaths
from services.update_download_service import UpdateDownloadService
from services.update_manifest_service import UpdateManifestService
from services.update_service import UpdateService
from services.update_state_service import UpdateStateService
from services.update_validation_service import UpdateValidationService
from ui.controllers.update_controller import UpdateController


def _resolve_optional(container, cls):
    try:
        return container.resolve(cls)
    except Exception:
        return None


def _active_work_provider(container, paths: AppPaths):
    def active() -> list[str]:
        rows: list[str] = []
        try:
            from workers.worker_pool import WorkerPool
            pool = container.resolve(WorkerPool)
            stats = pool.stats()
            # Any unrelated worker means render/model/background work may still be mutating state.
            if int(stats.get("active", 0)) or int(stats.get("pending", 0)):
                rows.append("background work")
        except Exception:
            pass
        # App DB migration crash/in-progress marker. Project migration markers remain protected
        # by the Phase 38 service and project-open path.
        for marker in (
            paths.data / "migration_in_progress.json",
            paths.data / "migration_state.json",
        ):
            if marker.is_file():
                rows.append("migration")
                break
        try:
            from app import phase26_runtime as p26
            scheduler = _resolve_optional(container, p26.BatchScheduler)
            if scheduler is not None:
                for name in ("running", "is_running", "active"):
                    value = getattr(scheduler, name, None)
                    value = value() if callable(value) else value
                    if bool(value):
                        rows.append("Batch")
                        break
        except Exception:
            pass
        return list(dict.fromkeys(rows))
    return active


def _flush_callback(container):
    try:
        from services.autosave_service import AutosaveService
        from services.recovery_snapshot_service import RecoverySnapshotService
        from services.recovery_service import RecoveryService
        autosave = container.resolve(AutosaveService)
        snapshots = container.resolve(RecoverySnapshotService)
        recovery = container.resolve(RecoveryService)
    except Exception:
        return lambda: True

    def flush() -> bool:
        dirty = list(autosave.dirty_projects())
        session_id = str(getattr(getattr(recovery, "session", None), "session_id", "") or "")
        for project_id in dirty:
            if not session_id:
                break
            try:
                snapshots.create(
                    project_id,
                    session_id,
                    snapshot_type="pre_update",
                    reason="Recovery point before application update",
                )
            except Exception:
                # Snapshot failure does not hide an autosave failure; flush_all remains authoritative.
                pass
        return bool(autosave.flush_all(reason="application_update"))
    return flush



def _wire_update_storage_cleanup(container, service: UpdateService, staging: Path) -> None:
    """Extend the existing Phase 29 cleanup service for Update Temp without a second cleanup system."""
    try:
        from domain.cache_entry import CacheEntry
        from domain.storage_category import StorageCategory
        from services.cleanup_service import CleanupService
        cleanup = container.resolve(CleanupService)
    except Exception:
        return
    if getattr(cleanup, "_phase42_update_temp", False):
        return
    original_entries = cleanup._entries_for
    original_active = cleanup.active_checker
    managed_root = Path(staging).resolve(strict=False)

    def entries_for(category, *, project_id: str):
        if category != StorageCategory.UPDATE_TEMP:
            return original_entries(category, project_id=project_id)
        rows = []
        if not managed_root.is_dir():
            return rows
        for path in managed_root.iterdir():
            if not path.is_file() or path.is_symlink() or path.name in {"pending-update.json", "last-update.json"}:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            rows.append(CacheEntry(
                path=path,
                category=StorageCategory.UPDATE_TEMP,
                size_bytes=int(stat.st_size),
                regeneratable=True,
                origin="update_staging",
                metadata={"managedRoot": str(managed_root)},
            ))
        return rows

    def active_checker(path, entry):
        if entry.category == StorageCategory.UPDATE_TEMP:
            return service.state.state in {
                "downloading", "validating", "ready", "installing"
            } or service.pending_marker.is_file()
        return original_active(path, entry)

    cleanup._entries_for = entries_for
    cleanup.active_checker = active_checker
    cleanup._phase42_update_temp = True

def _install_overlay_engine(logger):
    try:
        import PySide6.QtQml as QtQml
        from PySide6.QtCore import QUrl
    except ImportError:
        return None
    original = QtQml.QQmlApplicationEngine
    host = Path(__file__).resolve().parents[1] / "ui" / "qml" / "updates" / "UpdateHost.qml"
    class Phase42Engine(original):
        def load(self, url):
            super().load(url)
            try:
                roots = self.rootObjects()
                if not roots:
                    return
                component = QtQml.QQmlComponent(self, QUrl.fromLocalFile(str(host)))
                obj = component.create(self.rootContext())
                if obj is None:
                    if logger: logger.warning("Phase 42 update host failed: %s", component.errors())
                    return
                root = roots[0]
                content = root.property("contentItem")
                if content is not None and hasattr(obj, "setParentItem"):
                    obj.setParentItem(content)
                obj.setParent(root)
                self._phase42_update_host = obj
            except Exception:
                if logger: logger.exception("Could not mount Phase 42 update UI")
    QtQml.QQmlApplicationEngine = Phase42Engine
    return QtQml, original


def run(base_runner=None) -> int:
    if base_runner is None:
        from app.phase38_runtime import run as base_runner
    try:
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return base_runner()

    original_install = p31._install
    installed = {"done": False}
    engine_patch = {"value": None}

    def install(container):
        result = original_install(container)
        if installed["done"]:
            return result
        try:
            paths = container.resolve(AppPaths)
        except Exception:
            paths = AppPaths.discover(); paths.ensure()
        logger = container.resolve("logger")
        staging = paths.root / "updates"
        state = UpdateStateService(paths.settings, channel=UPDATE_CHANNEL)
        manifests = UpdateManifestService(
            UPDATE_MANIFEST_URL,
            timeout=UPDATE_HTTP_TIMEOUT_SECONDS,
            max_bytes=UPDATE_MAX_MANIFEST_BYTES,
        )
        downloads = UpdateDownloadService(staging, timeout=max(UPDATE_HTTP_TIMEOUT_SECONDS, 30.0))
        validation = UpdateValidationService(staging, expected_signer_subject=EXPECTED_UPDATE_SIGNER_SUBJECT)
        service = UpdateService(
            state, manifests, downloads, validation, staging,
            active_work_provider=_active_work_provider(container, paths),
            flush_callback=_flush_callback(container),
            logger=logger,
        )
        try:
            from workers.worker_pool import WorkerPool
            pool = container.resolve(WorkerPool)
        except Exception:
            pool = None
        for cls, value in (
            (UpdateStateService, state),
            (UpdateManifestService, manifests),
            (UpdateDownloadService, downloads),
            (UpdateValidationService, validation),
            (UpdateService, service),
        ):
            try: container.register_instance(cls, value)
            except Exception: pass
        _wire_update_storage_cleanup(container, service, staging)
        service.cleanup_stale(older_than_days=UPDATE_STALE_AFTER_DAYS)
        service.finalize_post_update()

        class RuntimeUpdateController(UpdateController):
            def __init__(self, parent=None):
                super().__init__(
                    service,
                    pool,
                    quit_callback=lambda: QCoreApplication.quit(),
                    configured=bool(UPDATE_MANIFEST_URL),
                    parent=parent,
                )
        qmlRegisterSingletonType(RuntimeUpdateController, "SPVideoStudio.Updates", 1, 0, "Updates")
        engine_patch["value"] = _install_overlay_engine(logger)
        installed["done"] = True
        return result

    p31._install = install
    try:
        return base_runner()
    finally:
        p31._install = original_install
        patch = engine_patch["value"]
        if patch:
            patch[0].QQmlApplicationEngine = patch[1]

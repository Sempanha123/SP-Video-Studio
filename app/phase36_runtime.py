from __future__ import annotations

"""Phase 36 diagnostics/support layer over the completed Phase 35 runtime."""

import app.phase31_runtime as p31
from app.phase35_runtime import run as run_phase35
from media.ffmpeg_locator import FFmpegLocator
from services.diagnostics_preferences_service import DiagnosticsPreferencesService
from services.diagnostics_service import DiagnosticsService
from services.environment_report_service import EnvironmentReportService
from services.log_redaction_service import LogRedactionService
from services.support_bundle_service import SupportBundleService
from ui.controllers.diagnostics_controller import DiagnosticsController


def _optional(container, cls):
    try:
        return container.resolve(cls)
    except Exception:
        return None


def run() -> int:
    try:
        from PySide6.QtCore import Property, Signal, Slot
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return run_phase35()

    import ui.controllers.render_controller as render_module
    BaseRenderController = render_module.RenderController

    class DiagnosticRenderController(BaseRenderController):
        diagnosticAvailable = Signal(str)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._last_failure_technical = ""

        @Property(str, notify=BaseRenderController.stateChanged)
        def lastFailureTechnical(self) -> str:
            return self._last_failure_technical

        @Slot(object)
        def _apply_failure(self, exc) -> None:
            self._last_failure_technical = str(exc or "")
            super()._apply_failure(exc)
            if self._last_failure_technical:
                self.diagnosticAvailable.emit(self._last_failure_technical)

        @Slot(object)
        def _apply_result(self, item) -> None:
            self._last_failure_technical = ""
            super()._apply_result(item)

    from services.disk_monitor_service import DiskMonitorService
    from services.model_service import ModelService
    from services.project_integrity_service import ProjectIntegrityService
    from services.project_service import ProjectService
    from services.settings_service import SettingsService
    from services.system_readiness_service import SystemReadinessService
    from storage.database import SQLiteDatabase
    from workers.worker_pool import WorkerPool

    try:
        from services.asset_library_service import AssetLibraryService
    except ImportError:
        AssetLibraryService = None
    try:
        from services.template_service import TemplateService
    except ImportError:
        TemplateService = None
    try:
        from services.batch_service import BatchService
    except ImportError:
        BatchService = None
    try:
        from services.recovery_service import RecoveryService
    except ImportError:
        RecoveryService = None

    original_install = p31._install
    registered = {"done": False}

    def install(container):
        result = original_install(container)
        if registered["done"]:
            return result
        settings = container.resolve(SettingsService)
        paths = settings.paths
        logger = container.resolve("logger")
        workers = container.resolve(WorkerPool)
        redaction = LogRedactionService()
        preferences = DiagnosticsPreferencesService(paths.settings)
        project_service = _optional(container, ProjectService)
        database = _optional(container, SQLiteDatabase)
        if database is None and project_service is not None:
            database = getattr(getattr(project_service, "repository", None), "database", None)
        integrity = _optional(container, ProjectIntegrityService)
        if integrity is None and database is not None:
            integrity = ProjectIntegrityService(database, logger)
        models = _optional(container, ModelService)
        environment = EnvironmentReportService(paths, settings, redaction, database=database, model_service=models)
        diagnostics = DiagnosticsService(
            paths,
            settings,
            readiness_service=_optional(container, SystemReadinessService),
            ffmpeg_locator=_optional(container, FFmpegLocator),
            database=database,
            model_service=models,
            disk_monitor=_optional(container, DiskMonitorService),
            project_service=project_service,
            project_integrity_service=integrity,
            asset_service=_optional(container, AssetLibraryService) if AssetLibraryService else None,
            template_service=_optional(container, TemplateService) if TemplateService else None,
            batch_service=_optional(container, BatchService) if BatchService else None,
            recovery_service=_optional(container, RecoveryService) if RecoveryService else None,
            redaction=redaction,
            logger=logger,
        )
        bundles = SupportBundleService(paths, environment, diagnostics, redaction, logger=logger)
        for cls, value in (
            (LogRedactionService, redaction),
            (DiagnosticsPreferencesService, preferences),
            (EnvironmentReportService, environment),
            (DiagnosticsService, diagnostics),
            (SupportBundleService, bundles),
        ):
            try:
                container.register_instance(cls, value)
            except Exception:
                pass

        class RuntimeDiagnosticsController(DiagnosticsController):
            def __init__(self, parent=None):
                super().__init__(diagnostics, bundles, preferences, workers, logger, parent)

        qmlRegisterSingletonType(
            RuntimeDiagnosticsController,
            "SPVideoStudio.Diagnostics",
            1,
            0,
            "Diagnostics",
        )
        registered["done"] = True
        return result

    p31._install = install
    render_module.RenderController = DiagnosticRenderController
    try:
        return run_phase35()
    finally:
        p31._install = original_install
        render_module.RenderController = BaseRenderController

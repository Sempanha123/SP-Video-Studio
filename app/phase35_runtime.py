from __future__ import annotations

"""Phase 35 first-run/onboarding layer over the completed Phase 34 runtime."""

import app.phase31_runtime as p31
from app.phase34_runtime import run as run_phase34
from services.language_service import LanguageService
from services.disk_monitor_service import DiskMonitorService
from services.model_service import ModelService
from services.onboarding_service import OnboardingService
from services.performance_profile_service import PerformanceProfileService
from services.project_service import ProjectService
from services.settings_service import SettingsService
from services.system_readiness_service import SystemReadinessService
from ui.controllers.onboarding_controller import OnboardingController
from workers.worker_pool import WorkerPool


def run() -> int:
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return run_phase34()

    original_install = p31._install
    registered = {"done": False}

    def install(container):
        result = original_install(container)
        if registered["done"]:
            return result
        settings = container.resolve(SettingsService)
        paths = settings.paths
        projects = container.resolve(ProjectService)
        languages = container.resolve(LanguageService)
        readiness = container.resolve(SystemReadinessService)
        logger = container.resolve("logger")
        try:model_service = container.resolve(ModelService)
        except Exception:model_service = None
        try:performance = container.resolve(PerformanceProfileService)
        except Exception:performance = None
        try:disk_monitor = container.resolve(DiskMonitorService)
        except Exception:disk_monitor = None
        try:workers = container.resolve(WorkerPool)
        except Exception:workers = None
        onboarding = OnboardingService(paths, settings, projects, languages, readiness, model_service=model_service, performance_service=performance, disk_monitor=disk_monitor, logger=logger)
        try:container.register_instance(OnboardingService, onboarding)
        except Exception:pass

        class RuntimeOnboardingController(OnboardingController):
            def __init__(self, parent=None):
                super().__init__(onboarding, worker_pool=workers, logger=logger, parent=parent)

        qmlRegisterSingletonType(RuntimeOnboardingController, "SPVideoStudio.Onboarding", 1, 0, "Onboarding")
        registered["done"] = True
        return result

    p31._install = install
    try:
        return run_phase34()
    finally:
        p31._install = original_install

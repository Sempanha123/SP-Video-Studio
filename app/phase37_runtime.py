from __future__ import annotations

"""Phase 37 security/privacy hardening layer over completed Phase 36."""

import app.phase31_runtime as p31
from app.phase36_runtime import run as run_phase36
from services.log_redaction_service import LogRedactionService
from services.privacy_service import PrivacyService
from services.security_event_service import SecurityEventService
from ui.controllers.privacy_controller import PrivacyController


def run() -> int:
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return run_phase36()

    original_install = p31._install
    registered = {"done": False}

    def install(container):
        result = original_install(container)
        if registered["done"]:
            return result
        logger = container.resolve("logger")
        try:
            redaction = container.resolve(LogRedactionService)
        except Exception:
            redaction = LogRedactionService()
        security = SecurityEventService(logger, redaction)
        privacy = PrivacyService()
        for cls, value in ((SecurityEventService, security), (PrivacyService, privacy)):
            try:
                container.register_instance(cls, value)
            except Exception:
                pass

        # Retrofit the safe event sink into existing shared services when present;
        # no duplicate News/Template service is created.
        for module_name, class_name in (
            ("services.news_source_fetch_service", "NewsSourceFetchService"),
            ("services.template_package_service", "TemplatePackageService"),
        ):
            try:
                module = __import__(module_name, fromlist=[class_name])
                service_type = getattr(module, class_name)
                existing = container.resolve(service_type)
                if hasattr(existing, "security_events"):
                    existing.security_events = security
            except Exception:
                pass

        class RuntimePrivacyController(PrivacyController):
            def __init__(self, parent=None):
                super().__init__(privacy, parent)

        qmlRegisterSingletonType(RuntimePrivacyController, "SPVideoStudio.Privacy", 1, 0, "Privacy")
        registered["done"] = True
        return result

    p31._install = install
    try:
        return run_phase36()
    finally:
        p31._install = original_install

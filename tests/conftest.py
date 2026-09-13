from __future__ import annotations

from tests.qa_support.reporting import pytest_session_summary as _write_session_summary


def pytest_configure(config):
    markers = {
        "fast": "normal developer test profile; no external model dependency",
        "e2e": "deterministic end-to-end workflow test",
        "real_engine_optional": "optional installed real-engine smoke test",
        "packaging_smoke": "packaging/import/resource smoke test",
        "qml_smoke": "QML compile/instantiate smoke test when Qt tooling is available",
        "performance": "non-flaky scale sanity test",
        "fault_injection": "controlled failure-path test",
        "security": "security regression test",
        "migration": "migration regression test",
        "windows": "Windows-specific acceptance test",
    }
    for name, description in markers.items():
        config.addinivalue_line("markers", f"{name}: {description}")


def pytest_collection_modifyitems(items):
    for item in items:
        name = str(getattr(item, "path", "")).replace("\\", "/")
        if name.endswith("test_phase37_security.py"):
            item.add_marker("security"); item.add_marker("integration")
        elif name.endswith("test_phase38_migrations.py"):
            item.add_marker("migration"); item.add_marker("integration")


def pytest_sessionfinish(session, exitstatus):
    _write_session_summary(session.config, exitstatus)

from __future__ import annotations

"""Phase 40 packaging runtime over the completed Phase 38/39 application runtime."""

import ctypes
import logging
import os
import sys
from pathlib import Path

from app.constants import APP_VERSION
from app.logging_setup import configure_logging
from app.paths import AppPaths
from app.runtime_paths import is_packaged, resource_path
from app.phase38_runtime import run as run_phase38


_APP_MUTEX_NAME = r"Local\MMOVideoStudio.AppInstance.38CE0934A2D44D9B9499AEA7F28FC0EB"
_APP_MUTEX_HANDLE = None


def _install_windows_app_mutex() -> None:
    """Keep an installer-visible per-session mutex alive for the application lifetime."""
    global _APP_MUTEX_HANDLE
    if os.name != "nt" or _APP_MUTEX_HANDLE:
        return
    try:
        kernel32 = ctypes.windll.kernel32
        create_mutex = kernel32.CreateMutexW
        create_mutex.restype = ctypes.c_void_p
        create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
        handle = create_mutex(None, False, _APP_MUTEX_NAME)
        if handle:
            _APP_MUTEX_HANDLE = handle
    except Exception:
        # Restart Manager/file-lock handling remains as a fallback; never block startup.
        logging.getLogger("sp_video_studio.packaging").warning(
            "Could not create Windows application mutex", exc_info=True
        )


def _install_fatal_exception_logging() -> None:
    previous = sys.excepthook
    try:
        paths = AppPaths.discover()
        paths.ensure()
        logger = configure_logging(paths.logs)
    except Exception:
        return

    def hook(exc_type, exc, tb):
        try:
            logger.critical("Unhandled packaged application exception", exc_info=(exc_type, exc, tb))
        except Exception:
            pass
        if not is_packaged():
            previous(exc_type, exc, tb)

    sys.excepthook = hook


def _inject_default_window_icon() -> None:
    if not is_packaged() or "-qwindowicon" in sys.argv:
        return
    icon = resource_path("resources", "icons", "app.ico")
    if icon.is_file():
        # Qt consumes this standard argument when QGuiApplication is constructed.
        sys.argv[1:1] = ["-qwindowicon", str(icon)]


def _self_check_argument() -> Path | None:
    try:
        index = sys.argv.index("--phase40-self-check")
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        return Path.cwd() / "phase40-self-check.json"
    return Path(sys.argv[index + 1])


def run() -> int:
    if "--version" in sys.argv:
        print(APP_VERSION)
        return 0
    self_check = _self_check_argument()
    if self_check is not None:
        from app.packaging_self_check import run_packaging_self_check
        return run_packaging_self_check(self_check)
    _install_windows_app_mutex()
    _install_fatal_exception_logging()
    _inject_default_window_icon()
    return run_phase38()

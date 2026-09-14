from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping

from .constants import APP_DATA_DIR_NAME, PRODUCT_NAME

_EXPECTED_EXECUTABLE_NAMES = {
    "mmo video studio.exe",
    "mmo-video-studio.exe",
    "mmo_video_studio.exe",
}


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_packaged(*, executable: str | Path | None = None, frozen: bool | None = None) -> bool:
    """Return whether code is running from a frozen/compiled application bundle.

    Nuitka standalone builds do not require a source checkout. The executable-name
    check is intentionally narrow and is only a fallback for builds where the
    implementation-specific ``__compiled__`` marker is unavailable.
    """
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False) or "__compiled__" in globals())
    if frozen:
        return True
    exe = Path(executable or sys.executable)
    return os.name == "nt" and exe.name.casefold() in _EXPECTED_EXECUTABLE_NAMES


def application_root(*, executable: str | Path | None = None, packaged: bool | None = None) -> Path:
    packaged = is_packaged(executable=executable) if packaged is None else bool(packaged)
    if packaged:
        return Path(executable or sys.executable).resolve().parent
    return source_root()


def resource_path(*parts: str, executable: str | Path | None = None, packaged: bool | None = None) -> Path:
    return application_root(executable=executable, packaged=packaged).joinpath(*parts)


def bundled_tool_path(
    tool: str,
    *,
    executable: str | Path | None = None,
    packaged: bool | None = None,
) -> Path | None:
    """Resolve a bundled media tool only from the controlled application ``bin`` directory."""
    packaged = is_packaged(executable=executable) if packaged is None else bool(packaged)
    if not packaged:
        return None
    suffix = ".exe" if os.name == "nt" or str(executable or "").lower().endswith(".exe") else ""
    name = tool if tool.lower().endswith(suffix.lower()) and suffix else f"{tool}{suffix}"
    candidate = application_root(executable=executable, packaged=True) / "bin" / name
    return candidate if candidate.is_file() else None


def local_appdata_root(
    *,
    environ: Mapping[str, str] | None = None,
    home: str | Path | None = None,
    platform_name: str | None = None,
) -> Path:
    """Return the managed writable application-data root without touching the filesystem."""
    env = os.environ if environ is None else environ
    platform_name = os.name if platform_name is None else platform_name
    home_path = Path.home() if home is None else Path(home)
    if platform_name == "nt":
        base = Path(env.get("LOCALAPPDATA") or (home_path / "AppData" / "Local"))
    else:
        base = Path(env.get("XDG_DATA_HOME") or (home_path / ".local" / "share"))
    return base / APP_DATA_DIR_NAME


def packaging_identity() -> dict[str, str]:
    return {
        "productName": PRODUCT_NAME,
        "bundleRoot": str(application_root()),
        "sourceRoot": str(source_root()),
        "packaged": str(is_packaged()).lower(),
    }

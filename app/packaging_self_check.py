from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from app.constants import APP_VERSION, PRODUCT_NAME
from app.paths import AppPaths
from app.runtime_paths import application_root, is_packaged, resource_path
from media.ffmpeg_locator import FFmpegLocator


def _run(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout, shell=False)


def run_packaging_self_check(report_path: str | Path) -> int:
    """Run a no-source-checkout backend smoke and write a machine-readable report.

    The Windows verifier supplies an isolated LOCALAPPDATA before invoking this mode.
    It intentionally does not automate visual QML interactions; those are covered by
    the Phase 39 source E2E suite plus the Phase 40 Windows manual acceptance matrix.
    """
    report = Path(report_path)
    paths = AppPaths.discover()
    paths.ensure()
    root = application_root()
    required = {
        "qmlMain": resource_path("ui", "qml", "Main.qml"),
        "languages": resource_path("resources", "languages.json"),
        "appIcon": resource_path("resources", "icons", "app.ico"),
        "thirdPartyNotice": resource_path("licenses", "THIRD_PARTY_NOTICES.md"),
    }
    resources = {name: path.is_file() for name, path in required.items()}
    locator = FFmpegLocator(timeout_seconds=8.0)
    ffmpeg, ffprobe = locator.discover()
    render_ok = False
    probe_ok = False
    output = paths.temp / "phase40-packaging-smoke.mp4"
    output.unlink(missing_ok=True)
    if ffmpeg.available and ffmpeg.path:
        done = _run([
            ffmpeg.path, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=96x64:r=10:d=0.4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(output),
        ])
        render_ok = done.returncode == 0 and output.is_file() and output.stat().st_size > 0
    if render_ok and ffprobe.available and ffprobe.path:
        done = _run([ffprobe.path, "-v", "error", "-show_entries", "format=format_name", "-of", "default=nw=1:nk=1", str(output)])
        probe_ok = done.returncode == 0 and "mp4" in (done.stdout or "").lower()
    payload: dict[str, Any] = {
        "productName": PRODUCT_NAME,
        "appVersion": APP_VERSION,
        "packaged": is_packaged(),
        "bundleRoot": str(root),
        "dataRoot": str(paths.root),
        "resources": resources,
        "ffmpeg": {"available": ffmpeg.available, "path": ffmpeg.path or "", "version": ffmpeg.version or ""},
        "ffprobe": {"available": ffprobe.available, "path": ffprobe.path or "", "version": ffprobe.version or ""},
        "libx264Render": render_ok,
        "ffprobeMp4": probe_ok,
    }
    payload["ok"] = bool(all(resources.values()) and ffmpeg.available and ffprobe.available and render_ok and probe_ok)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.unlink(missing_ok=True)
    return 0 if payload["ok"] else 1

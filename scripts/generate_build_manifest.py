from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.constants import APP_VERSION, ORGANIZATION_NAME, PRODUCT_NAME


def _version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _git_commit(repo: Path) -> str:
    env = os.environ.get("MMOVS_COMMIT_SHA") or os.environ.get("GITHUB_SHA")
    if env:
        return env.strip()
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True,
            timeout=5, check=False, shell=False,
        )
        if done.returncode == 0:
            return done.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _ffmpeg_version(ffmpeg: Path) -> str:
    try:
        done = subprocess.run([str(ffmpeg), "-version"], capture_output=True, text=True, timeout=8, check=False, shell=False)
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    line = (done.stdout or done.stderr or "").splitlines()
    return line[0].strip() if line else "unavailable"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", required=True)
    parser.add_argument("--mode", choices=["Development", "Release", "Debug"], required=True)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--ffmpeg-source-file", default="")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    dist = Path(args.dist).resolve()
    ffmpeg = dist / "bin" / "ffmpeg.exe"
    source_note = ""
    if args.ffmpeg_source_file:
        try:
            source_note = Path(args.ffmpeg_source_file).read_text(encoding="utf-8").strip()[:2000]
        except OSError:
            source_note = ""
    manifest = {
        "schemaVersion": 1,
        "productName": PRODUCT_NAME,
        "organization": ORGANIZATION_NAME,
        "appVersion": APP_VERSION,
        "commit": _git_commit(repo),
        "buildTimeUtc": datetime.now(timezone.utc).isoformat(),
        "buildMode": args.mode,
        "target": "Windows 11 x64",
        "architecture": platform.machine() or "unknown",
        "pythonVersion": platform.python_version(),
        "pythonImplementation": platform.python_implementation(),
        "PySide6Version": _version("PySide6"),
        "NuitkaVersion": _version("Nuitka"),
        "ffmpegVersion": _ffmpeg_version(ffmpeg),
        "ffmpegSource": source_note,
        "layout": "standalone-one-folder",
        "modelsBundled": False,
        "runtimeDataRoot": "%LOCALAPPDATA%/MMOVideoStudio",
        "console": args.mode != "Release",
    }
    (dist / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

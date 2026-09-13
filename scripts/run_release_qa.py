from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROFILES = {
    "FAST": "not integration and not e2e and not real_engine_optional and not voxcpm and not faster_whisper and not translation and not packaging_smoke and not qml_smoke and not performance and not fault_injection",
    "INTEGRATION": "(integration or performance or fault_injection or security or migration) and not e2e and not real_engine_optional and not voxcpm and not faster_whisper and not translation",
    "E2E": "e2e",
    "REAL_ENGINE_OPTIONAL": "real_engine_optional or voxcpm or faster_whisper or translation",
    "PACKAGING_SMOKE": "packaging_smoke",
    "RELEASE": "not real_engine_optional and not voxcpm and not faster_whisper and not translation",
}


def command_for(profile: str, report_dir: Path, extra: list[str]) -> list[str]:
    profile = profile.upper()
    if profile not in PROFILES:
        raise KeyError(profile)
    command = [sys.executable, "-m", "pytest", "-m", PROFILES[profile], "-ra"]
    if profile == "RELEASE":
        command += [f"--junitxml={report_dir / 'junit.xml'}"]
    command += extra
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run MMO Video Studio Phase 39 QA profiles.")
    parser.add_argument("profile", nargs="?", default="FAST", choices=sorted(PROFILES))
    parser.add_argument("--report-dir", default="test-results")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    report_dir = (root / args.report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["SPVS_QA_REPORT_DIR"] = str(report_dir)
    env["SPVS_QA_PROFILE"] = args.profile
    # Qt tests should not require a visible desktop in CI.
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    command = command_for(args.profile, report_dir, list(args.pytest_args))
    print(f"[Phase39 QA] profile={args.profile} cwd={root}")
    return subprocess.run(command, cwd=root, env=env, shell=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

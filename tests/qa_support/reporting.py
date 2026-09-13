from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _count(stats: dict[str, list[Any]], *keys: str) -> int:
    return sum(len(stats.get(key, [])) for key in keys)


def build_summary(stats: dict[str, list[Any]], exit_status: int, profile: str) -> dict[str, Any]:
    failed_reports = stats.get("failed", [])
    failed = sorted({str(getattr(item, "nodeid", "")) for item in failed_reports if getattr(item, "nodeid", "")})
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "exitStatus": int(exit_status),
        "counts": {
            "passed": _count(stats, "passed"),
            "failed": _count(stats, "failed"),
            "skipped": _count(stats, "skipped"),
            "xfailed": _count(stats, "xfailed"),
            "xpassed": _count(stats, "xpassed"),
            "errors": _count(stats, "error", "errors"),
        },
        "failedTests": failed,
        "privacy": "Contains test IDs/counts only; no project text, media paths, credentials, or user data.",
    }


def write_summary(report_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "summary.json"
    md_path = report_dir / "summary.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = payload["counts"]
    lines = [
        "# MMO Video Studio QA Summary",
        "",
        f"- Profile: `{payload['profile']}`",
        f"- Exit status: `{payload['exitStatus']}`",
        f"- Passed: **{counts['passed']}**",
        f"- Failed: **{counts['failed']}**",
        f"- Skipped: **{counts['skipped']}**",
        f"- XFailed: **{counts['xfailed']}**",
        f"- XPassed: **{counts['xpassed']}**",
        f"- Errors: **{counts['errors']}**",
        "",
        "The report stores test identifiers and aggregate counts only. It does not store private user data.",
    ]
    failed = payload.get("failedTests") or []
    if failed:
        lines += ["", "## Failed tests", ""] + [f"- `{nodeid}`" for nodeid in failed]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def pytest_session_summary(config: object, exitstatus: int) -> None:
    raw_dir = os.environ.get("SPVS_QA_REPORT_DIR", "").strip()
    if not raw_dir:
        return
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    stats = getattr(reporter, "stats", {}) if reporter is not None else {}
    payload = build_summary(stats, exitstatus, os.environ.get("SPVS_QA_PROFILE", "custom"))
    write_summary(Path(raw_dir), payload)

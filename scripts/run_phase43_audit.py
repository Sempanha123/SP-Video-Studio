from __future__ import annotations

"""Deterministic source/artifact hygiene checks for the Phase 43 production audit.

This helper intentionally does not pretend to replace the Windows 11 manual release
matrix. It catches repository/artifact mistakes that can be verified safely and
offline, and emits machine-readable evidence for the final audit report.
"""

import argparse
import ast
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

SOURCE_ROOTS = (
    "app", "domain", "engines", "media", "rendering", "services", "storage",
    "ui", "workers", "workflows",
)
TEXT_SUFFIXES = {".py", ".qml", ".json", ".toml", ".ini", ".iss", ".ps1", ".md", ".txt"}
FORBIDDEN_ARTIFACT_PARTS = {".git", ".pytest_cache", "__pycache__", "tests", "test-results"}
FORBIDDEN_ARTIFACT_NAMES = {".env", ".env.local", ".env.production"}
FORBIDDEN_ARTIFACT_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".pyc", ".pyo"}
MEDIA_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".wav", ".mp3", ".flac", ".m4a"}

# app/constants.py intentionally prints APP_VERSION for the --version CLI path.
PRINT_ALLOWLIST = {("app/phase40_runtime.py", 83)}
MARKER_ALLOWLIST = {
    "services/support_bundle_service.py",  # safely filters a file named debug.log
    "services/performance_telemetry_service.py",  # diagnostic/debug timing category
    "services/privacy_service.py",  # user-facing diagnostics/privacy wording
    "services/update_service.py",  # text sanitization/control-character logic
}

@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    detail: str


def _files(root: Path, roots: Iterable[str] = SOURCE_ROOTS) -> Iterable[Path]:
    for name in roots:
        base = root / name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and "__pycache__" not in path.parts:
                yield path


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _python_prints(root: Path, path: Path, text: str) -> list[Finding]:
    rel = _relative(root, path)
    if path.suffix != ".py":
        return []
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as exc:
        return [Finding("P1", "PYTHON_SYNTAX", rel, f"Syntax error: {exc.msg} at line {exc.lineno}")]
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            key = (rel, int(getattr(node, "lineno", 0)))
            if key not in PRINT_ALLOWLIST:
                findings.append(Finding("P2", "PRODUCTION_PRINT", rel, f"print() at line {key[1]}"))
    return findings


def source_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    secret_assignment = re.compile(
        r"(?im)^\s*(?:[A-Za-z_][\w.]*\.)?(?:api[_-]?key|secret|password|access[_-]?token|auth[_-]?token)\s*[:=]\s*[\"']([^\"']{8,})[\"']"
    )
    dev_home = re.compile(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+)")
    unfinished = re.compile(r"(?i)\b(TODO|FIXME|Lorem ipsum|Test Button)\b")

    for path in _files(root):
        rel = _relative(root, path)
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(_python_prints(root, path, text))
        if "shell=True" in text.replace(" ", ""):
            findings.append(Finding("P1", "SHELL_TRUE", rel, "Production subprocess call uses shell=True."))
        for match in secret_assignment.finditer(text):
            value = match.group(1)
            if value.casefold().startswith(("example", "placeholder", "changeme", "your-", "<")):
                continue
            findings.append(Finding("P0", "HARDCODED_SECRET", rel, "Credential-like literal assignment found."))
        if rel not in MARKER_ALLOWLIST:
            match = unfinished.search(text)
            if match:
                findings.append(Finding("P2", "UNFINISHED_MARKER", rel, f"Review marker: {match.group(1)}"))
        # Source runtime code must not be tied to a developer's home directory.
        if rel.split("/", 1)[0] in SOURCE_ROOTS:
            match = dev_home.search(text)
            if match:
                findings.append(Finding("P1", "DEVELOPER_HOME_PATH", rel, "Hardcoded developer home path found."))
    return findings


def _artifact_entry_findings(name: str) -> list[Finding]:
    clean = name.replace("\\", "/").lstrip("/")
    parts = tuple(p for p in PurePosixPath(clean).parts if p not in {"", "."})
    lowered = tuple(p.casefold() for p in parts)
    leaf = lowered[-1] if lowered else ""
    suffix = Path(leaf).suffix.casefold()
    out: list[Finding] = []
    if any(part in {p.casefold() for p in FORBIDDEN_ARTIFACT_PARTS} for part in lowered):
        out.append(Finding("P1", "ARTIFACT_DEV_FILE", clean, "Development/test metadata present in release artifact."))
    if leaf in FORBIDDEN_ARTIFACT_NAMES or suffix in FORBIDDEN_ARTIFACT_SUFFIXES:
        out.append(Finding("P1", "ARTIFACT_PRIVATE_FILE", clean, "Environment/database/cache file present in release artifact."))
    if suffix in MEDIA_SUFFIXES and any(token in leaf for token in ("private", "customer", "fixture", "sample-source", "screenshot")):
        out.append(Finding("P1", "ARTIFACT_PRIVATE_MEDIA", clean, "Potential private/test media present in release artifact."))
    return out


def artifact_findings(path: Path) -> list[Finding]:
    if not path.exists():
        return [Finding("P1", "ARTIFACT_MISSING", str(path), "Artifact path does not exist.")]
    findings: list[Finding] = []
    if path.is_dir():
        for item in path.rglob("*"):
            if item.is_file():
                findings.extend(_artifact_entry_findings(item.relative_to(path).as_posix()))
                if item.suffix.lower() in TEXT_SUFFIXES:
                    text = item.read_text(encoding="utf-8", errors="replace")
                    if re.search(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+)", text):
                        findings.append(Finding("P1", "ARTIFACT_DEVELOPER_HOME", item.relative_to(path).as_posix(), "Developer home path embedded in artifact text."))
        return findings
    if path.suffix.casefold() != ".zip":
        return _artifact_entry_findings(path.name)
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                findings.append(Finding("P1", "ARTIFACT_ZIP_CRC", bad, "ZIP CRC validation failed."))
            for info in archive.infolist():
                if info.is_dir():
                    continue
                findings.extend(_artifact_entry_findings(info.filename))
                if Path(info.filename).suffix.lower() in TEXT_SUFFIXES and info.file_size <= 4 * 1024 * 1024:
                    text = archive.read(info).decode("utf-8", errors="replace")
                    if re.search(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+)", text):
                        findings.append(Finding("P1", "ARTIFACT_DEVELOPER_HOME", info.filename, "Developer home path embedded in artifact text."))
    except zipfile.BadZipFile:
        findings.append(Finding("P1", "ARTIFACT_BAD_ZIP", str(path), "Artifact is not a valid ZIP archive."))
    return findings


def contract_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    required = (
        "README.md",
        "docs/manual-qa-checklist.md",
        "docs/known-issues.md",
        "packaging/windows/notices/THIRD_PARTY_NOTICES.md",
        "packaging/windows/notices/APPLICATION_LICENSE_NOTICE.txt",
        "scripts/run_release_qa.py",
        "scripts/verify_windows_build.ps1",
        "scripts/verify_windows_installer.ps1",
    )
    for rel in required:
        if not (root / rel).exists():
            findings.append(Finding("P1", "REQUIRED_RELEASE_FILE", rel, "Required release-audit file is missing."))

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8") if (root / "pyproject.toml").exists() else ""
    main = (root / "main.py").read_text(encoding="utf-8") if (root / "main.py").exists() else ""
    p40 = (root / "app/phase40_runtime.py").read_text(encoding="utf-8") if (root / "app/phase40_runtime.py").exists() else ""
    p38 = (root / "app/phase38_runtime.py").read_text(encoding="utf-8") if (root / "app/phase38_runtime.py").exists() else ""
    if 'app.phase40_runtime:run' not in pyproject or 'from app.phase40_runtime import run' not in main:
        findings.append(Finding("P1", "PACKAGED_ENTRYPOINT", "pyproject.toml/main.py", "Stable Phase 40 packaged entrypoint is not intact."))
    if "run_phase38" not in p40 or "run_phase37" not in p38:
        findings.append(Finding("P1", "SECURITY_LAYER_CHAIN", "app/phase40_runtime.py", "Security/migration runtime chain is not reachable from packaged entrypoint."))
    if (root / "app/phase43_runtime.py").exists():
        findings.append(Finding("P1", "FEATURE_FREEZE_RUNTIME", "app/phase43_runtime.py", "Phase 43 must not add a new feature runtime layer."))
    return findings


def audit(root: Path, artifact: Path | None = None) -> dict:
    findings = source_findings(root) + contract_findings(root)
    artifact_result = None
    if artifact is not None:
        artifact_find = artifact_findings(artifact)
        findings.extend(artifact_find)
        artifact_result = {"path": str(artifact), "findingCount": len(artifact_find)}
    counts = {level: sum(1 for f in findings if f.severity == level) for level in ("P0", "P1", "P2", "P3")}
    return {
        "phase": 43,
        "root": str(root),
        "artifact": artifact_result,
        "counts": counts,
        "blocking": counts["P0"] > 0 or counts["P1"] > 0,
        "findings": [asdict(f) for f in findings],
        "scopeNote": "Static/source and supplied-artifact hygiene only; native Windows/manual acceptance remains separate.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Phase 43 production source/artifact audit checks.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--artifact", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    artifact = Path(args.artifact).resolve() if args.artifact else None
    result = audit(root, artifact)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Phase 43 static audit: P0={result['counts']['P0']} P1={result['counts']['P1']} P2={result['counts']['P2']} P3={result['counts']['P3']}")
        for finding in result["findings"]:
            print(f"[{finding['severity']}] {finding['code']} {finding['path']}: {finding['detail']}")
    return 1 if result["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

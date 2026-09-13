from __future__ import annotations

import compileall
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.packaging_smoke
ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_entrypoint_and_release_markers_are_valid():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["requires-python"] == ">=3.11,<3.15"
    assert data["project"]["scripts"]["sp-video-studio"] == "app.phase38_runtime:run"
    marker_text = "\n".join(data["tool"]["pytest"]["ini_options"]["markers"])
    for marker in ("fast", "integration", "e2e", "real_engine_optional", "packaging_smoke", "security", "migration"):
        assert marker in marker_text


def test_release_qa_runner_and_required_docs_exist():
    required = [
        "scripts/run_release_qa.py",
        "docs/PHASE39_RELEASE_QA.md",
        "docs/manual-qa-checklist.md",
        "docs/known-issues.md",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    assert not missing, f"Missing release QA resources: {missing}"


def test_phase39_python_sources_compile():
    targets = [ROOT / "tests" / "qa_support", ROOT / "scripts" / "run_release_qa.py"]
    for target in targets:
        if target.is_dir():
            assert compileall.compile_dir(str(target), quiet=1)
        else:
            assert compileall.compile_file(str(target), quiet=1)


def test_tests_do_not_commit_large_generated_media():
    tests = ROOT / "tests"
    if not tests.is_dir():
        pytest.skip("Tests directory unavailable")
    offenders = []
    media_suffixes = {".mp4", ".mov", ".mkv", ".wav", ".mp3", ".flac", ".png", ".jpg", ".jpeg"}
    for path in tests.rglob("*"):
        if path.is_file() and path.suffix.casefold() in media_suffixes and path.stat().st_size > 512 * 1024:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"Large media must be generated at test time: {offenders}"


def test_phase39_remains_a_qa_layer_without_its_own_runtime():
    # Phase 39 is deliberately test-only. Future phases may change the current
    # entrypoint, so this regression must not freeze the repository at Phase 39.
    assert not (ROOT / "app" / "phase39_runtime.py").exists()
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entrypoint = data["project"]["scripts"]["sp-video-studio"]
    assert entrypoint.startswith("app.phase") and entrypoint.endswith("_runtime:run")

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.packaging_smoke
ROOT = Path(__file__).resolve().parents[1]


def _audit_module():
    path = ROOT / "scripts" / "run_phase43_audit.py"
    spec = importlib.util.spec_from_file_location("phase43_audit", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase43_is_feature_freeze_without_new_runtime_layer():
    assert not (ROOT / "app" / "phase43_runtime.py").exists()
    report = (ROOT / "docs" / "production-audit-phase43.md").read_text(encoding="utf-8")
    assert "Feature freeze" in report
    assert "No major new feature scope" in report


def test_packaged_entrypoint_still_reaches_migration_and_security_layers():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    phase40 = (ROOT / "app" / "phase40_runtime.py").read_text(encoding="utf-8")
    phase38 = (ROOT / "app" / "phase38_runtime.py").read_text(encoding="utf-8")
    assert 'app.phase40_runtime:run' in pyproject
    assert 'from app.phase40_runtime import run' in main
    assert "run_phase38" in phase40
    assert "run_phase37" in phase38


def test_static_production_source_audit_has_no_p0_or_p1():
    module = _audit_module()
    result = module.audit(ROOT)
    assert result["counts"]["P0"] == 0, result["findings"]
    assert result["counts"]["P1"] == 0, result["findings"]


def test_artifact_scanner_rejects_env_database_git_and_test_content(tmp_path):
    module = _audit_module()
    archive = tmp_path / "bad-release.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(".env", "SECRET=x")
        zf.writestr(".git/config", "x")
        zf.writestr("tests/test_release.py", "x")
        zf.writestr("data/private.sqlite3", "x")
    result = module.artifact_findings(archive)
    codes = {item.code for item in result}
    assert "ARTIFACT_PRIVATE_FILE" in codes
    assert "ARTIFACT_DEV_FILE" in codes


def test_artifact_scanner_accepts_clean_minimal_archive(tmp_path):
    module = _audit_module()
    archive = tmp_path / "clean-release.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("MMO Video Studio.exe", b"fixture")
        zf.writestr("licenses/THIRD_PARTY_NOTICES.md", "notices")
    assert module.artifact_findings(archive) == []


def test_audit_report_has_all_required_sections_and_release_decision():
    text = (ROOT / "docs" / "production-audit-phase43.md").read_text(encoding="utf-8")
    for heading in (
        "## Environment", "## Build", "## Workflows", "## Performance", "## Security",
        "## Privacy", "## Accessibility", "## Installer", "## Updates", "## Known Issues",
        "## Release Recommendation",
    ):
        assert heading in text
    assert "NOT READY — BLOCKERS REMAIN" in text
    recommendation = text.split("## Release Recommendation", 1)[1]
    assert recommendation.lstrip().startswith("**NOT READY — BLOCKERS REMAIN**")


def test_release_blockers_are_explicit_and_no_p0_is_claimed():
    known = (ROOT / "docs" / "known-issues.md").read_text(encoding="utf-8")
    assert "REL-43-001" in known and "P1" in known
    assert "REL-43-002" in known
    assert "no known open p0" in known.casefold()
    assert "Phase 44" in known and "blocked" in known.casefold()


def test_application_license_notice_does_not_claim_legal_approval():
    notice = (ROOT / "packaging" / "windows" / "notices" / "APPLICATION_LICENSE_NOTICE.txt").read_text(encoding="utf-8")
    assert "owner-approved public application license terms" in notice
    assert "does not currently" in notice
    audit = (ROOT / "docs" / "production-audit-phase43.md").read_text(encoding="utf-8")
    assert "REL-43-002" in audit


def test_third_party_notice_covers_qt_ffmpeg_models_and_uncertain_items():
    text = (ROOT / "packaging" / "windows" / "notices" / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").casefold()
    for term in ("pyside6", "qt", "ffmpeg", "model"):
        assert term in text
    assert "not verified" in text or "verify" in text


def test_manual_qa_checklist_covers_phase43_workflow_and_platform_gates():
    text = (ROOT / "docs" / "manual-qa-checklist.md").read_text(encoding="utf-8").casefold()
    for term in (
        "normal video", "news", "reporter", "interview", "story", "translate & dub", "shorts",
        "speechblock", "timeline", "subtitle", "music", "template", "asset library", "batch factory",
        "recovery", "storage", "diagnostics", "migration", "200%", "narrator", "unicode", "offline",
        "libx264", "application updates", "non-admin",
    ):
        assert term.casefold() in text


def test_multilingual_release_contract_keeps_four_required_languages():
    checklist = (ROOT / "docs" / "manual-qa-checklist.md").read_text(encoding="utf-8")
    for sample in ("English", "Khmer", "Thai", "Vietnamese", "ខ្មែរ", "ไทย", "Việt"):
        assert sample in checklist


def test_update_release_audit_retains_security_failure_matrix():
    text = (ROOT / "tests" / "test_phase42_updates.py").read_text(encoding="utf-8").casefold()
    assert "checksum" in text or "sha256" in text
    assert "cancel" in text
    assert "active" in text and ("render" in text or "batch" in text)
    assert "offline" in text or "urlerror" in text


def test_installer_audit_retains_data_preservation_and_nonadmin_contracts():
    text = (ROOT / "tests" / "test_phase41_installer.py").read_text(encoding="utf-8").casefold()
    assert "non-admin" in text or "nonadmin" in text or "privilegesrequired=lowest" in text
    assert "preserv" in text
    assert "removeappdata" in text


def test_phase43_completion_report_uses_required_readiness_and_stop_rule():
    text = (ROOT / "PHASE43_REPORT.md").read_text(encoding="utf-8")
    required = (
        "PHASE 43 STATUS", "Feature freeze:", "Clean-machine audit:", "Onboarding:",
        "Normal Video:", "News:", "Interview:", "Story:", "Dub:", "Shorts:",
        "Speech/TTS:", "Timeline:", "Subtitles:", "Audio:", "Templates:", "Assets:",
        "Batch:", "Recovery:", "Storage/cache:", "Diagnostics:", "Migrations:",
        "Multilingual:", "Performance:", "Security:", "Privacy:", "Accessibility:",
        "Packaging:", "Installer:", "Updates:", "License/notices:", "Artifact secret scan:",
        "P0 issues:", "P1 issues:", "P2/P3 issues:", "New files:", "Modified files:",
        "Tests/audits run:", "Release readiness:", "NOT READY — BLOCKERS REMAIN",
        "Known issues:", "Architecture decisions:", "Recommended next phase:",
        "Phase 44 — Release Candidate", "ONLY if release readiness is READY.",
        "chore: complete final production readiness audit",
    )
    for token in required:
        assert token in text

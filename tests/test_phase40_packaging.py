from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest
from PIL import Image

from app.constants import APP_DATA_DIR_NAME, APP_VERSION, PRODUCT_NAME
from app.runtime_paths import application_root, local_appdata_root, resource_path
from media.ffmpeg_locator import FFmpegLocator

pytestmark = pytest.mark.packaging_smoke
ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict:
    return json.loads((ROOT / "packaging/windows/build_config.json").read_text(encoding="utf-8"))


def test_phase40_entrypoint_and_central_version():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dynamic"] == ["version"]
    assert data["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "app.constants.APP_VERSION"
    assert data["project"]["scripts"]["sp-video-studio"] == "app.phase40_runtime:run"
    assert APP_VERSION == "0.1.0"
    assert PRODUCT_NAME == "MMO Video Studio"


def test_windows_packaging_target_is_one_folder_py311():
    cfg = _config()
    assert cfg["target"] == "Windows 11 x64"
    assert cfg["python"] == "3.11"
    assert cfg["mode"] == "standalone-one-folder"
    assert cfg["oneFile"] is False
    assert cfg["packager"] == "Nuitka"


def test_pinned_packager_and_qt_versions_match_documented_build():
    cfg = _config()
    pins = (ROOT / "packaging/windows/constraints-win311.txt").read_text(encoding="utf-8")
    assert cfg["packagerVersion"] == "4.2.1" and "Nuitka==4.2.1" in pins
    assert cfg["pyside6Version"] == "6.11.2" and "PySide6==6.11.2" in pins


def test_release_is_gui_and_debug_keeps_console():
    cfg = _config()
    script = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    assert cfg["releaseConsole"] is False and cfg["debugConsole"] is True
    assert "--windows-console-mode=disable" in script
    assert "--windows-console-mode=force" in script


def test_qml_and_resource_payload_are_explicit():
    cfg = _config()
    script = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    assert cfg["resources"] == ["ui/qml", "resources"]
    assert "--include-data-dir=ui/qml=ui/qml" in script
    assert "--include-data-dir=resources=resources" in script
    assert "--include-qt-plugins=qml" in script
    assert "--include-qt-plugins=all" not in script


def test_required_qml_pages_exist_in_source_overlay():
    qml = ROOT / "ui/qml"
    required = [
        "Main.qml", "pages/HomePage.qml", "pages/CreatePage.qml", "pages/ProjectsPage.qml",
        "pages/ProjectWorkspacePage.qml", "pages/BatchPage.qml", "pages/VoicesPage.qml",
        "pages/TemplatesPage.qml", "pages/AssetsPage.qml", "pages/ModelsPage.qml",
        "pages/SettingsPage.qml", "diagnostics/DiagnosticsPage.qml",
    ]
    missing = [x for x in required if not (qml / x).is_file()]
    if missing and len(list(qml.rglob("*.qml"))) < 30:
        pytest.skip(f"Partial sandbox QML overlay; full checkout required: {missing}")
    assert not missing


def test_qt_plugin_policy_is_selective():
    plugins = _config()["qtPlugins"]
    for name in ("qml", "platforms", "imageformats", "multimedia"):
        assert name in plugins
    assert "styles" not in plugins and "tls" not in plugins and "all" not in plugins


def test_ffmpeg_strategy_is_bundled_without_runtime_download():
    cfg = _config()["ffmpeg"]
    assert cfg["strategy"] == "bundled-at-build-time"
    assert cfg["runtimeDownload"] is False
    assert set(cfg["requiredFiles"]) == {"ffmpeg.exe", "ffprobe.exe", "LICENSE.txt", "SOURCE.txt"}
    runtime = (ROOT / "app/phase40_runtime.py").read_text(encoding="utf-8").lower()
    locator = (ROOT / "media/ffmpeg_locator.py").read_text(encoding="utf-8").lower()
    assert "download" not in runtime
    assert "urlopen" not in locator and "requests.get" not in locator


def test_ffmpeg_locator_still_supports_developer_path_fallback():
    if not shutil.which("ffmpeg"):
        pytest.skip("System FFmpeg unavailable")
    ffmpeg, ffprobe = FFmpegLocator().discover()
    assert ffmpeg.available and ffprobe.available


def test_runtime_data_root_contract_is_localappdata():
    root = local_appdata_root(environ={"LOCALAPPDATA": r"C:\Users\QA\AppData\Local"}, home=r"C:\Users\QA", platform_name="nt")
    assert str(root).replace("/", "\\").endswith(r"AppData\Local\MMOVideoStudio")
    assert APP_DATA_DIR_NAME == "MMOVideoStudio"
    assert _config()["runtimeDataRoot"] == "%LOCALAPPDATA%/MMOVideoStudio"


def test_models_are_not_bundled():
    models = _config()["models"]
    assert models["bundledWeights"] is False
    assert models["root"].endswith("/models")
    build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    assert "models=" not in build and "--include-data-dir=models" not in build


def test_ai_runtime_packages_are_explicit_and_cpu_is_default():
    cfg = _config()
    packages = set(cfg["explicitDynamicPackages"])
    assert {"faster_whisper", "ctranslate2", "voxcpm", "transformers", "torch"} <= packages
    build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    assert "download.pytorch.org/whl/cpu" in build
    assert "MMOVS_SIGN_CERT_THUMBPRINT" in build
    assert "CUDA" not in (ROOT / "packaging/windows/constraints-win311.txt").read_text(encoding="utf-8")


def test_app_icon_is_multisize_ico():
    icon = ROOT / "resources/icons/app.ico"
    assert icon.is_file()
    with Image.open(icon) as image:
        assert image.format == "ICO"
        sizes = set(image.info.get("sizes") or [])
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= sizes


def test_nuitka_build_embeds_icon_and_version_metadata():
    build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    for option in ("--windows-icon-from-ico=", "--product-name=MMO Video Studio", "--company-name=SP Video Studio", "--file-description=MMO Video Studio", "--copyright=Copyright (c) SP Video Studio", "--file-version=", "--product-version="):
        assert option in build


def test_window_icon_uses_qt_standard_argument_in_packaged_runtime():
    runtime = (ROOT / "app/phase40_runtime.py").read_text(encoding="utf-8")
    assert '"-qwindowicon"' in runtime
    assert 'resource_path("resources", "icons", "app.ico")' in runtime


def test_application_root_does_not_need_source_checkout_when_packaged(tmp_path):
    exe = tmp_path / "Program Files Like" / "MMO Video Studio.exe"
    exe.parent.mkdir(parents=True)
    exe.touch()
    assert application_root(executable=exe, packaged=True) == exe.parent.resolve()
    assert resource_path("ui", "qml", "Main.qml", executable=exe, packaged=True) == exe.parent.resolve() / "ui/qml/Main.qml"


def test_build_script_requires_staged_ffmpeg_not_network_fetch():
    build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8").lower()
    assert "mmovs_ffmpeg_dir" in build
    assert "ffmpeg.exe" in build and "ffprobe.exe" in build
    assert "invoke-webrequest" not in build and "start-bitstransfer" not in build and "curl.exe" not in build


def test_ffmpeg_notice_requires_exact_license_and_source():
    notice = (ROOT / "packaging/windows/FFMPEG_STAGING.md").read_text(encoding="utf-8")
    assert "LICENSE.txt" in notice and "SOURCE.txt" in notice
    assert "legal conclusion" in notice


def test_font_policy_adds_no_font_binary():
    delta_roots = [ROOT / "packaging/windows", ROOT / "app", ROOT / "docs"]
    font_suffixes = {".ttf", ".otf", ".woff", ".woff2"}
    assert not [p for root in delta_roots if root.exists() for p in root.rglob("*") if p.is_file() and p.suffix.lower() in font_suffixes]
    notice = (ROOT / "packaging/windows/notices/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "adds no font files" in notice


def test_build_manifest_generator_has_no_secret_fields():
    source = (ROOT / "scripts/generate_build_manifest.py").read_text(encoding="utf-8")
    for expected in ("appVersion", "commit", "buildTimeUtc", "pythonVersion", "PySide6Version", "NuitkaVersion", "ffmpegVersion", "architecture"):
        assert expected in source
    lowered = source.lower()
    assert '"api_key"' not in lowered and '"token"' not in lowered and '"password"' not in lowered


def test_verify_script_enforces_secret_and_development_file_scan():
    verify = (ROOT / "scripts/verify_windows_build.ps1").read_text(encoding="utf-8")
    for token in (".env", "tests", "*.pem", "*.key", "CredentialPattern"):
        assert token in verify
    assert "LOCALAPPDATA" in verify and "MMOVideoStudio" in verify


def test_verify_script_runs_no_python_self_check_and_unicode_path():
    verify = (ROOT / "scripts/verify_windows_build.ps1").read_text(encoding="utf-8")
    assert "--phase40-self-check" in verify
    assert "$env:PATH = \"$env:SystemRoot\\System32;$env:SystemRoot\"" in verify
    assert "ខ្មែរ" in verify


def test_self_check_validates_bundled_resources_and_libx264():
    source = (ROOT / "app/packaging_self_check.py").read_text(encoding="utf-8")
    assert '"libx264"' in source
    for item in ("ui", "qml", "languages.json", "app.ico", "THIRD_PARTY_NOTICES.md"):
        assert item in source
    assert "shell=False" in source


def test_release_dist_excludes_tests_and_source_repo():
    build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    verify = (ROOT / "scripts/verify_windows_build.ps1").read_text(encoding="utf-8")
    assert "--nofollow-import-to=*.tests" in build
    assert "'.git'" in verify and "'tests'" in verify


def test_packaging_scripts_are_present():
    for path in ("scripts/build_windows.ps1", "scripts/verify_windows_build.ps1", "scripts/generate_build_manifest.py"):
        assert (ROOT / path).is_file()


def test_central_version_used_by_diagnostics_and_migrations():
    for path in ("services/environment_report_service.py", "services/diagnostics_service.py", "services/project_migration_service.py"):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "APP_VERSION" in text
    assert '"0.1.0"' not in (ROOT / "services/environment_report_service.py").read_text(encoding="utf-8")



def test_release_logging_does_not_require_console_stream():
    source = (ROOT / "app/logging_setup.py").read_text(encoding="utf-8")
    assert "if sys.stderr is not None" in source
    assert "RotatingFileHandler" in source



def test_build_performs_optional_ai_import_smoke_without_model_load():
    build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    for name in ("ctranslate2", "faster_whisper", "sentencepiece", "soundfile", "torch", "transformers", "voxcpm"):
        assert name in build
    assert "AI runtime import smoke failed" in build


def test_powershell_scripts_do_not_require_ps7_iswindows_variable():
    for path in (ROOT / "scripts/build_windows.ps1", ROOT / "scripts/verify_windows_build.ps1"):
        text = path.read_text(encoding="utf-8")
        assert "$IsWindows" not in text
        assert "[PlatformID]::Win32NT" in text


def test_phase40_docs_cover_windows_acceptance_and_known_limitations():
    doc = ROOT / "docs/PHASE40_WINDOWS_PACKAGING.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    for phrase in ("Windows 11 x64", "Python 3.11", "one-folder", "Fresh profile", "No-Python", "FFmpeg", "code signing", "antivirus"):
        assert phrase.casefold() in text.casefold()


def test_windows_verifier_includes_models_page_without_model_smoke():
    verifier = (ROOT / "scripts/verify_windows_build.ps1").read_text(encoding="utf-8")
    assert "Open Models with no managed AI models installed" in verifier
    assert "all seven steps succeed" in verifier


def test_build_manifest_script_runs_from_source_checkout(tmp_path):
    import json
    import shutil
    import subprocess
    import sys

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/FFprobe are unavailable for manifest smoke")
    dist = tmp_path / "dist"
    (dist / "bin").mkdir(parents=True)
    shutil.copy2(ffmpeg, dist / "bin" / "ffmpeg.exe")
    shutil.copy2(ffprobe, dist / "bin" / "ffprobe.exe")
    notice = tmp_path / "SOURCE.txt"
    notice.write_text("phase40 manifest smoke\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_build_manifest.py"), "--dist", str(dist), "--mode", "Release", "--repo", str(ROOT), "--ffmpeg-source-file", str(notice)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    payload = json.loads((dist / "build-manifest.json").read_text(encoding="utf-8"))
    assert payload["productName"] == "MMO Video Studio"
    assert payload["appVersion"] == APP_VERSION
    assert payload["modelsBundled"] is False

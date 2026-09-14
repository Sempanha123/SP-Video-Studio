from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.packaging_smoke
ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging/windows/installer/MMO-Video-Studio.iss"
BUILD = ROOT / "scripts/build_windows_installer.ps1"
VERIFY = ROOT / "scripts/verify_windows_installer.ps1"
CONFIG = ROOT / "packaging/windows/installer/installer_config.json"
APP_ID = "{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}"
MUTEX = "MMOVideoStudio.AppInstance.38CE0934A2D44D9B9499AEA7F28FC0EB"


def _iss() -> str:
    return ISS.read_text(encoding="utf-8")


def _build() -> str:
    return BUILD.read_text(encoding="utf-8")


def _verify() -> str:
    return VERIFY.read_text(encoding="utf-8")


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_installer_technology_scope_and_target_are_explicit():
    cfg = _config()
    assert cfg["technology"] == "Inno Setup"
    assert cfg["compilerVersion"] == "7.1.0"
    assert cfg["target"] == "Windows 11 x64"
    assert cfg["setupArchitecture"] == "x64"
    assert cfg["architecturesAllowed"] == "x64os"
    assert cfg["scope"] == "per-user"
    assert cfg["requiresElevation"] is False


def test_stable_app_id_and_uninstall_identity():
    cfg = _config()
    text = _iss()
    assert cfg["appId"] == APP_ID
    assert "AppId={{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}" in text
    assert "CreateUninstallRegKey=yes" in text
    assert "{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}_is1" in text


def test_per_user_install_does_not_force_elevation():
    text = _iss()
    assert "PrivilegesRequired=lowest" in text
    assert r"DefaultDirName={localappdata}\Programs\MMO Video Studio" in text
    assert "PrivilegesRequired=admin" not in text


def test_target_is_windows_11_x64_only():
    text = _iss()
    assert "SetupArchitecture=x64" in text
    assert "ArchitecturesAllowed=x64os" in text
    assert "ArchitecturesInstallIn64BitMode=x64os" in text
    assert "MinVersion=10.0.22000" in text


def test_installer_ui_stays_simple_and_desktop_shortcut_is_opt_in():
    text = _iss()
    assert "WizardStyle=modern" in text
    assert "DisableWelcomePage=no" in text
    assert 'Name: "desktopicon"' in text
    assert "Flags: unchecked" in text
    assert 'Name: "{group}\\MMO Video Studio"' in text
    assert 'Name: "{autodesktop}\\MMO Video Studio"' in text


def test_no_file_association_or_protocol_handler_is_added():
    text = _iss().casefold()
    assert "changesassociations=no" in text
    assert ".mmovtemplate" not in text
    for token in ("url protocol", "urlprotocol", "classes\\mmovideo"):
        assert token not in text


def test_upgrade_reuses_install_identity_and_previous_directory():
    text = _iss()
    assert "UsePreviousAppDir=yes" in text
    assert "UsePreviousGroup=yes" in text
    assert "OutputBaseFilename=MMO-Video-Studio-{#MyAppVersion}-Setup" in text


def test_downgrade_guard_reads_registered_display_version_and_compares_numeric_versions():
    text = _iss()
    assert "RegQueryStringValue(HKCU, ProductUninstallKey, 'DisplayVersion'" in text
    assert "StrToVersion" in text
    assert "ComparePackedVersion(InstalledVersion, CurrentVersion) > 0" in text
    assert "A newer version of MMO Video Studio is already installed." in text
    assert "Result := False" in text


def test_running_app_mutex_matches_packaged_runtime():
    installer = _iss()
    runtime = (ROOT / "app/phase40_runtime.py").read_text(encoding="utf-8")
    assert MUTEX in installer
    assert MUTEX in runtime
    assert "CreateMutexW" in runtime
    assert "create_mutex.restype = ctypes.c_void_p" in runtime
    assert "AppMutex={#MyAppMutex}" in installer
    assert "CloseApplications=yes" in installer
    assert "RestartApplications=no" in installer


def test_installer_does_not_force_reboot():
    text = _iss()
    assert "AlwaysRestart=no" in text
    assert "RestartIfNeededByRun=no" in text
    assert "RestartApplications=no" in text


def test_default_uninstall_has_no_user_data_delete_section():
    text = _iss()
    assert "[UninstallDelete]" not in text
    # The managed root may appear only in guarded Pascal uninstall code, never a declarative delete rule.
    assert "CurUninstallStepChanged" in text
    assert "ManagedDataRoot = '{localappdata}\\MMOVideoStudio'" in text


def test_optional_data_removal_is_explicit_default_no_and_managed_root_only():
    text = _iss()
    assert "MB_YESNO or MB_DEFBUTTON2" in text
    assert "HasUninstallSwitch('/REMOVEAPPDATA')" in text
    assert "UninstallSilent()" in text
    assert "DelTree(DataPath, True, True, True)" in text
    assert "Projects or exports stored outside this managed folder are NOT removed." in text
    assert "Documents" not in text


def test_models_are_not_bundled_by_installer_layer():
    cfg = json.loads((ROOT / "packaging/windows/build_config.json").read_text(encoding="utf-8"))
    assert cfg["models"]["bundledWeights"] is False
    text = _iss().casefold()
    assert "model weights" not in text


def test_installer_consumes_verified_phase40_folder_instead_of_repackaging_python():
    text = _build()
    for required in (
        "MMO Video Studio.exe",
        "build-manifest.json",
        r"bin\ffmpeg.exe",
        r"bin\ffprobe.exe",
        r"licenses\THIRD_PARTY_NOTICES.md",
        r"licenses\ffmpeg\LICENSE.txt",
        r"licenses\ffmpeg\SOURCE.txt",
    ):
        assert required in text
    assert "Copy-Item $DistDir $StageDist -Recurse -Force" in text
    assert "nuitka" not in text.casefold()


def test_installer_builder_does_not_download_inno_or_prerequisites():
    text = _build().casefold()
    for forbidden in ("invoke-webrequest", "start-bitstransfer", "curl.exe", "winget install"):
        assert forbidden not in text
    assert "this script does not download it silently" in text


def test_installer_version_is_checked_against_central_app_version():
    text = _build()
    assert "APP_VERSION" in text
    assert "build-manifest version" in text
    assert "/DMyAppVersion=" in text
    assert "/DMyAppVersionQuad=" in text
    iss = _iss()
    assert "#ifndef MyAppVersion" in iss
    assert "AppVersion={#MyAppVersion}" in iss
    assert "VersionInfoVersion={#MyAppVersionQuad}" in iss


def test_inno_compiler_version_is_pinned_but_reviewable():
    text = _build()
    assert "7.1.0" in text
    assert "-AllowNewerCompiler" in text
    assert "MMOVS_INNO_COMPILER" in text


def test_installer_signing_reuses_external_phase40_credentials_only():
    text = _build()
    assert "MMOVS_SIGN_CERT_THUMBPRINT" in text
    assert "MMOVS_SIGN_TIMESTAMP_URL" in text
    assert "signtool.exe" in text
    lowered = text.casefold()
    assert "password=" not in lowered
    assert "private key" not in lowered
    assert ".pfx" not in lowered




def test_installer_build_keeps_native_acceptance_opt_in_for_clean_vm_safety():
    text = _build()
    assert "[switch]$RunNativeVerify" in text
    assert "if ($RunNativeVerify)" in text
    assert "-RequireCleanProfile" in text
    assert "$SkipVerify" not in text


def test_installer_hash_and_manifest_are_emitted():
    text = _build()
    assert "Get-FileHash $ExpectedSetup -Algorithm SHA256" in text
    assert ".sha256" in text
    assert "installer-manifest.json" in text
    assert "sha256 = $Hash" in text


def test_application_and_third_party_notices_are_required():
    assert (ROOT / "packaging/windows/notices/APPLICATION_LICENSE_NOTICE.txt").is_file()
    assert (ROOT / "packaging/windows/notices/THIRD_PARTY_NOTICES.md").is_file()
    text = _iss()
    assert "APPLICATION_LICENSE_NOTICE.txt" in text
    build = _build()
    assert r"licenses\THIRD_PARTY_NOTICES.md" in build
    assert r"licenses\ffmpeg\LICENSE.txt" in build
    assert r"licenses\ffmpeg\SOURCE.txt" in build


def test_application_license_notice_does_not_invent_an_open_source_license():
    notice = (ROOT / "packaging/windows/notices/APPLICATION_LICENSE_NOTICE.txt").read_text(encoding="utf-8")
    assert "does not currently contain owner-approved public application license terms" in notice
    assert "does not silently imply" in notice
    for license_name in ("MIT License", "Apache License", "GNU General Public License"):
        assert license_name not in notice


def test_verifier_requires_hash_and_refuses_existing_installation():
    text = _verify()
    assert "Get-FileHash $Installer -Algorithm SHA256" in text
    assert "UninstallRegistryPath" in text
    assert "refuses to run over an existing MMO Video Studio installation" in text
    assert "refuses any pre-existing managed data root" in text


def test_verifier_covers_non_admin_unicode_space_path_and_no_python_self_check():
    text = _verify()
    assert "RequireNonAdmin" in text
    assert "MMO Video Studio Phase41 QA ខ្មែរ" in text
    assert '"$env:SystemRoot\\System32;$env:SystemRoot"' in text
    assert "--phase40-self-check" in text


def test_verifier_covers_fresh_install_start_menu_and_render_acceptance():
    text = _verify()
    assert "Assert-Shortcuts" in text
    assert "Start Menu" in text
    assert "Complete or skip onboarding" in text
    assert "Import a tiny media file" in text
    assert "render/export with bundled FFmpeg" in text
    assert "close/reopen the project" in text


def test_verifier_covers_default_uninstall_preservation():
    text = _verify()
    for category in ("settings", "models", "assets", "templates", "cache", "recovery", "logs", "exports"):
        assert f"'{category}'" in text
    assert "Assert-ManagedSentinels $true" in text
    assert "External project was deleted during default uninstall" in text
    assert "Start Menu shortcut remained after uninstall" in text


def test_verifier_covers_explicit_data_removal_without_external_project_deletion():
    text = _verify()
    assert "Invoke-Uninstall -RemoveAppData" in text
    assert "Explicit managed-data removal did not remove" in text
    assert "Explicit managed-data removal touched an external project" in text
    assert "Refusing destructive optional-data-removal test" in text


def test_verifier_requires_real_previous_installer_for_upgrade_release_gate():
    text = _verify()
    assert "PreviousInstaller" in text
    assert "RequireUpgradeFixture" in text
    assert "real earlier release built with the same AppId" in text
    assert "Upgrade did not preserve fixture data" in text
    assert "migrations complete" in text


def test_verifier_checks_future_downgrade_block():
    text = _verify()
    assert "$Downgrade = Start-Process -FilePath $PreviousInstaller" in text
    assert "downgrade guard failed" in text


def test_silent_install_and_standard_logs_are_documented():
    doc = (ROOT / "packaging/windows/installer/README.md").read_text(encoding="utf-8")
    assert "/VERYSILENT" in doc
    assert "/LOG=" in doc
    assert "/REMOVEAPPDATA" in doc
    assert "No certificate, password, private key, or signing token" in doc


def test_phase41_architecture_doc_covers_required_release_matrix():
    text = (ROOT / "docs/PHASE41_WINDOWS_INSTALLER.md").read_text(encoding="utf-8").casefold()
    for phrase in (
        "inno setup 7.1.0",
        "per-user",
        "downgrade",
        "start menu",
        "desktop shortcut",
        "user data",
        "sha-256",
        "non-admin",
        "unicode",
        "upgrade",
        "uninstall",
        "ffmpeg",
        "models",
    ):
        assert phrase in text


def test_build_config_records_installer_contract():
    cfg = json.loads((ROOT / "packaging/windows/build_config.json").read_text(encoding="utf-8"))
    installer = cfg["installer"]
    assert installer["technology"] == "Inno Setup"
    assert installer["compilerVersion"] == "7.1.0"
    assert installer["appId"] == APP_ID
    assert installer["scope"] == "per-user"
    assert installer["requiresElevation"] is False
    assert installer["userDataRoot"] == "%LOCALAPPDATA%/MMOVideoStudio"


def test_phase41_does_not_create_a_new_application_runtime_layer():
    assert not (ROOT / "app/phase41_runtime.py").exists()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'sp-video-studio = "app.phase40_runtime:run"' in pyproject


def test_installer_scripts_do_not_contain_obvious_secret_assignments():
    texts = "\n".join(p.read_text(encoding="utf-8") for p in (ISS, BUILD, VERIFY))
    pattern = re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")
    assert not pattern.search(texts)

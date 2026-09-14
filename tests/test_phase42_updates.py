from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.constants import APP_VERSION
from domain.storage_category import StorageCategory, StorageSafety, definition
from domain.update_manifest import SemanticVersion, UpdateManifest, UpdateManifestError, compare_versions
from domain.update_state import UpdateStateCode
from services.update_download_service import UpdateDownloadCancelled, UpdateDownloadService
from services.update_manifest_service import UpdateCheckError, UpdateManifestService
from services.update_service import UpdateBlockedError, UpdateService
from services.update_state_service import UpdateStateService
from services.update_validation_service import UpdateValidationError, UpdateValidationService

ROOT=Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.packaging_smoke


class Server:
    def __init__(self, manifest: dict, installer: bytes):
        self.manifest=manifest;self.installer=installer
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/manifest.json':
                    body = owner.manifest if isinstance(owner.manifest, bytes) else json.dumps(owner.manifest).encode('utf-8')
                    content='application/json'
                elif self.path == '/installer.exe':
                    body=owner.installer;content='application/octet-stream'
                elif self.path == '/redirect-http':
                    self.send_response(302);self.send_header('Location','http://example.invalid/manifest.json');self.end_headers();return
                else:
                    self.send_response(404);self.end_headers();return
                self.send_response(200);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(body)));self.end_headers()
                # Deliberately chunk installer so cancellation is testable.
                for i in range(0,len(body),65536):
                    try:self.wfile.write(body[i:i+65536]);self.wfile.flush()
                    except (BrokenPipeError,ConnectionResetError):break
            def log_message(self,*_):pass
        self.http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)
    @property
    def base(self):return f'http://127.0.0.1:{self.http.server_address[1]}'
    def __enter__(self):self.thread.start();return self
    def __exit__(self,*_):self.http.shutdown();self.thread.join(timeout=2);self.http.server_close()


def manifest_for(base:str,data:bytes,**changes):
    payload={
      'schema_version':1,'channel':'stable','version':'9.1.0','minimum_supported_version':'0.1.0',
      'published_at':'2026-09-14T00:00:00Z','release_notes':'Safe update\nNo forced install.',
      'release_notes_url':base+'/notes','installer_url':base+'/installer.exe',
      'installer_sha256':hashlib.sha256(data).hexdigest(),'installer_size':len(data),
      'signature':{'type':'authenticode','signer':'informational-only'},'minimum_project_schema':2,
    };payload.update(changes);return payload


def stack(tmp_path,base,data,manifest=None,**kwargs):
    staging=tmp_path/'អ្នកប្រើ'/'MMO Video Studio'/'updates';settings=tmp_path/'settings'
    state=UpdateStateService(settings)
    ms=UpdateManifestService(base+'/manifest.json',allow_test_http=True)
    dl=UpdateDownloadService(staging,allow_test_http=True)
    validation=UpdateValidationService(staging)
    service=UpdateService(state,ms,dl,validation,staging,**kwargs)
    return service


def test_semver_comparison_is_robust():
    assert compare_versions('1.2.0','1.1.9')>0
    assert compare_versions('1.2.0','1.2.0')==0
    assert compare_versions('1.2.0-beta.2','1.2.0-beta.11')<0
    assert compare_versions('1.2.0-beta','1.2.0')<0
    assert SemanticVersion.parse('2.0.1+build.7')==SemanticVersion.parse('2.0.1')
    with pytest.raises(UpdateManifestError):SemanticVersion.parse('1.2')


def test_manifest_schema_and_security_validation():
    data=b'x';base='https://updates.example.test';valid=manifest_for(base,data)
    parsed=UpdateManifest.from_dict(valid);assert parsed.version=='9.1.0' and parsed.channel=='stable'
    bad=dict(valid,installer_url='http://updates.example.test/i.exe')
    with pytest.raises(UpdateManifestError,match='HTTPS'):UpdateManifest.from_dict(bad)
    with pytest.raises(UpdateManifestError):UpdateManifest.from_dict(dict(valid,schema_version=99))
    with pytest.raises(UpdateManifestError):UpdateManifest.from_dict(dict(valid,version='bad'))
    with pytest.raises(UpdateManifestError):UpdateManifest.from_dict(dict(valid,installer_sha256='00'))
    with pytest.raises(UpdateManifestError):UpdateManifest.from_dict(dict(valid,installer_size=0))
    with pytest.raises(UpdateManifestError,match='forbidden'):UpdateManifest.from_dict(dict(valid,command='calc.exe'))
    with pytest.raises(UpdateManifestError):UpdateManifest.from_dict(dict(valid,channel='beta'))



def test_malformed_json_manifest_is_rejected_without_interrupting_app(tmp_path):
    with Server(b"{not-json", b"installer") as server:
        state = UpdateStateService(tmp_path / "settings")
        staging = tmp_path / "updates"
        service = UpdateService(
            state,
            UpdateManifestService(server.base + "/manifest.json", allow_test_http=True),
            UpdateDownloadService(staging, allow_test_http=True),
            UpdateValidationService(staging),
            staging,
        )
        assert service.check() is None
        assert service.state.state == "error"
        assert service.state.last_error


def test_expected_authenticode_publisher_is_verified_when_configured(monkeypatch, tmp_path):
    import types
    import services.update_validation_service as validation_module
    data = b"signed-installer"
    root = tmp_path / "updates"
    root.mkdir()
    path = root / "MMO-Video-Studio-9.1.0-Setup.exe"
    path.write_bytes(data)
    manifest = UpdateManifest.from_dict(manifest_for("https://updates.example.test", data))
    good = UpdateValidationService(root, expected_signer_subject="CN=MMO Video Studio Publisher")
    bad = UpdateValidationService(root, expected_signer_subject="CN=Different Publisher")
    monkeypatch.setattr(validation_module.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        validation_module.subprocess,
        "run",
        lambda *args, **kwargs: types.SimpleNamespace(
            returncode=0,
            stdout='{"Status":"Valid","Subject":"CN=MMO Video Studio Publisher, O=MMO Studio"}',
        ),
    )
    result = good.verify_authenticode(path)
    assert result["signatureConfigured"] is True and result["signatureValid"] is True
    with pytest.raises(UpdateValidationError, match="expected publisher"):
        bad.verify_authenticode(path)

def test_production_manifest_service_rejects_http():
    with pytest.raises(UpdateCheckError,match='HTTPS'):
        UpdateManifestService('http://example.test/manifest.json').fetch()


def test_mock_server_newer_same_and_older(tmp_path):
    data=b'installer'
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data,version='9.1.0');service=stack(tmp_path,server.base,data)
        assert service.check().version=='9.1.0' and service.state.state=='available'
        server.manifest=manifest_for(server.base,data,version=APP_VERSION);assert service.check() is None and service.state.state=='up_to_date'
        server.manifest=manifest_for(server.base,data,version='0.0.1');assert service.check() is None and service.state.state=='up_to_date'


def test_offline_is_nonfatal_and_exact_message(tmp_path):
    state=UpdateStateService(tmp_path/'settings');staging=tmp_path/'updates'
    service=UpdateService(state,UpdateManifestService('http://127.0.0.1:1/manifest.json',allow_test_http=True),UpdateDownloadService(staging,allow_test_http=True),UpdateValidationService(staging),staging)
    assert service.check() is None;assert service.state.last_error=='Could not check for updates.';assert service.state.state=='error'


def test_download_progress_checksum_and_unicode_staging(tmp_path):
    data=os.urandom(350_000)
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data);service=stack(tmp_path,server.base,data);service.check();seen=[]
        path=service.download(progress=seen.append)
        assert path.is_file() and path.read_bytes()==data and path.parent.name=='updates'
        assert seen and seen[-1]==1.0 and service.state.installer_validated and service.state.state=='ready'


def test_size_mismatch_rejected_and_staged_file_removed(tmp_path):
    data=b'a'*1000
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data,installer_size=len(data)+1);service=stack(tmp_path,server.base,data);service.check()
        with pytest.raises(UpdateValidationError,match='size'):service.download()
        assert not list((tmp_path/'អ្នកប្រើ'/'MMO Video Studio'/'updates').glob('*.exe'))


def test_mandatory_checksum_attack_never_launches(tmp_path):
    original=b'GOOD-INSTALLER';altered=b'EVIL-INSTALLER!';launched=[]
    with Server({},altered) as server:
        server.manifest=manifest_for(server.base,original,installer_size=len(altered));service=stack(tmp_path,server.base,altered,launcher=lambda args:launched.append(args));service.check()
        with pytest.raises(UpdateValidationError,match='checksum'):service.download()
        assert launched==[] and not service.state.installer_validated
        with pytest.raises(Exception):service.install_ready_update()
        assert launched==[]


class CancelAfterProgress:
    def __init__(self):self.cancelled=False
    @property
    def is_cancelled(self):return self.cancelled


def test_cancelled_download_removes_partial_and_can_retry(tmp_path):
    data=os.urandom(900_000)
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data);service=stack(tmp_path,server.base,data);service.check();token=CancelAfterProgress()
        def progress(v):
            if v>0:token.cancelled=True
        with pytest.raises(UpdateDownloadCancelled):service.download(cancellation=token,progress=progress)
        root=tmp_path/'អ្នកប្រើ'/'MMO Video Studio'/'updates';assert not list(root.glob('*.part'))
        assert service.state.state=='available'
        path=service.download();assert path.is_file() and service.state.state=='ready'


def test_staging_containment_uses_generated_filename(tmp_path):
    data=b'x';base='https://updates.example.test'
    m=UpdateManifest.from_dict(manifest_for(base,data,installer_url='https://updates.example.test/../../evil.exe?name=evil.exe'))
    service=UpdateDownloadService(tmp_path/'updates')
    path=service.installer_path(m);assert path.parent==(tmp_path/'updates').resolve() and path.name=='MMO-Video-Studio-9.1.0-Setup.exe'


def test_signature_not_claimed_when_no_publisher_identity_configured(tmp_path):
    data=b'signed-or-not';root=tmp_path/'updates';root.mkdir();path=root/'MMO-Video-Studio-9.1.0-Setup.exe';path.write_bytes(data)
    m=UpdateManifest.from_dict(manifest_for('https://updates.example.test',data))
    result=UpdateValidationService(root).validate(path,m)
    assert result['signatureConfigured'] is False and result['signatureValid'] is None


def test_mandatory_active_work_blocks_install_until_clear(tmp_path):
    data=b'installer';active=['render','Batch'];launched=[];flushed=[]
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data);service=stack(tmp_path,server.base,data,active_work_provider=lambda:list(active),flush_callback=lambda:flushed.append(True) or True,launcher=lambda args:launched.append(args));service.check();service.download()
        with pytest.raises(UpdateBlockedError,match='render'):service.install_ready_update()
        assert launched==[] and flushed==[]
        active.clear();path=service.install_ready_update();assert launched==[[str(path)]] and flushed==[True]


def test_autosave_flush_failure_blocks_installer(tmp_path):
    data=b'installer';launched=[]
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data);service=stack(tmp_path,server.base,data,flush_callback=lambda:False,launcher=lambda args:launched.append(args));service.check();service.download()
        with pytest.raises(UpdateBlockedError,match='could not be saved'):service.install_ready_update()
        assert launched==[]


def test_installer_handoff_uses_single_safe_argv_and_pending_marker(tmp_path):
    data=b'installer';calls=[]
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data);service=stack(tmp_path,server.base,data,launcher=lambda args:calls.append(args));service.check();path=service.download();service.install_ready_update()
        assert calls==[[str(path)]] and len(calls[0])==1
        marker=json.loads(service.pending_marker.read_text(encoding='utf-8'));assert marker['fromVersion']==APP_VERSION and marker['toVersion']=='9.1.0'


def test_failed_installer_launch_keeps_ready_app_state(tmp_path):
    data=b'installer'
    def broken(_):raise OSError('launch failed')
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data);service=stack(tmp_path,server.base,data,launcher=broken);service.check();service.download()
        with pytest.raises(Exception):service.install_ready_update()
        assert service.state.state=='ready' and service.state.installer_validated and not service.pending_marker.exists()


def test_post_update_marker_finalizes_only_after_new_version(monkeypatch,tmp_path):
    # Phase 42 runtime calls this only after normal startup/database migration initialization.
    from services import update_service as mod
    root=tmp_path/'updates';state=UpdateStateService(tmp_path/'settings');service=UpdateService(state,UpdateManifestService('https://example.test/x'),UpdateDownloadService(root),UpdateValidationService(root),root)
    root.mkdir();service.pending_marker.write_text(json.dumps({'fromVersion':'0.0.1','toVersion':APP_VERSION}),encoding='utf-8')
    result=service.finalize_post_update();assert result and not service.pending_marker.exists() and (root/'last-update.json').is_file()


def test_stale_staging_cleanup_skips_active_update(tmp_path):
    root=tmp_path/'updates';root.mkdir();old=root/'old.part';old.write_bytes(b'x');os.utime(old,(1,1))
    state=UpdateStateService(tmp_path/'settings');service=UpdateService(state,UpdateManifestService('https://example.test/x'),UpdateDownloadService(root),UpdateValidationService(root),root)
    assert service.cleanup_stale(older_than_days=1)==1 and not old.exists()
    active=root/'active.part';active.write_bytes(b'x');os.utime(active,(1,1));state.update(state=UpdateStateCode.DOWNLOADING.value)
    assert service.cleanup_stale(older_than_days=1)==0 and active.exists()


def test_update_temp_storage_category_is_clearable_but_active_files_are_service_guarded():
    d=definition(StorageCategory.UPDATE_TEMP);assert d.safety==StorageSafety.SAFE_TO_CLEAR and d.cache


def test_update_state_persistence_does_not_resume_transient_install(tmp_path):
    service=UpdateStateService(tmp_path/'settings');service.set_automatic_check(False);service.update(state='installing',last_check_at='today',last_error='safe')
    loaded=UpdateStateService(tmp_path/'settings').current;assert loaded.automatic_check is False and loaded.state=='idle' and loaded.last_check_at=='today'


def test_phase42_runtime_and_entrypoints_are_thin():
    main=(ROOT/'main.py').read_text(encoding='utf-8');pyproject=(ROOT/'pyproject.toml').read_text(encoding='utf-8');runtime=(ROOT/'app/phase42_runtime.py').read_text(encoding='utf-8')
    assert 'app.phase40_runtime' in main and 'app.phase40_runtime:run' in pyproject
    phase40=(ROOT/'app/phase40_runtime.py').read_text(encoding='utf-8')
    assert 'run_phase42(run_phase38)' in phase40
    assert 'p31._install' in runtime and 'base_runner()' in runtime and 'AutosaveService' in runtime and 'RecoverySnapshotService' in runtime


def test_update_qml_is_plain_text_and_user_controlled():
    dialog=(ROOT/'ui/qml/updates/UpdateAvailableDialog.qml').read_text(encoding='utf-8');settings=(ROOT/'ui/qml/updates/UpdateSettings.qml').read_text(encoding='utf-8')
    assert 'Text.PlainText' in dialog and 'Download Update' in dialog and 'Later' in dialog and 'Install Now' in dialog
    assert 'Check for Updates' in settings and 'Automatically Check' in settings and 'Stable' in settings
    assert 'WebEngine' not in dialog and 'RichText' not in dialog


def test_build_config_has_stable_update_trust_contract():
    data=json.loads((ROOT/'packaging/windows/build_config.json').read_text(encoding='utf-8'));u=data['updates']
    assert u['channel']=='stable' and u['requiresHttps'] is True and u['automaticInstallerDownload'] is False
    assert u['officialManifestUrl']=='' and u['expectedAuthenticodeSignerSubject']==''


def test_diagnostics_reports_update_state_without_project_data():
    text=(ROOT/'services/diagnostics_service.py').read_text(encoding='utf-8')
    assert 'lastUpdateCheck' in text and 'updateState' in text and 'lastUpdateError' in text and 'currentVersion' in text


def test_manifest_does_not_accept_arbitrary_command_fields():
    data=b'x';payload=manifest_for('https://updates.example.test',data)
    for key in ('command','commands','args','script','executable','powershell','shell'):
        with pytest.raises(UpdateManifestError):UpdateManifest.from_dict({**payload,key:'anything'})


def test_redirect_cannot_escape_test_local_http_to_untrusted_http():
    data=b'x'
    with Server({},data) as server:
        service=UpdateManifestService(server.base+'/redirect-http',allow_test_http=True)
        with pytest.raises(UpdateCheckError,match='HTTPS|rejected'):
            service.fetch()


def test_manifest_generator_uses_central_version_and_hash(tmp_path):
    import subprocess,sys
    installer=tmp_path/'MMO Video Studio Setup.exe';installer.write_bytes(b'installer-bytes')
    output=tmp_path/'manifest.json'
    done=subprocess.run([sys.executable,str(ROOT/'scripts/generate_update_manifest.py'),'--installer',str(installer),'--installer-url','https://updates.example.test/MMO-Video-Studio-Setup.exe','--output',str(output),'--release-notes','ខ្មែរ ไทย Tiếng Việt'],cwd=ROOT,capture_output=True,text=True,shell=False,timeout=20)
    assert done.returncode==0,done.stderr
    payload=json.loads(output.read_text(encoding='utf-8'))
    assert payload['version']==APP_VERSION and payload['installer_sha256']==hashlib.sha256(b'installer-bytes').hexdigest() and payload['installer_size']==len(b'installer-bytes')
    assert payload['minimum_project_schema']>=1 and payload['release_notes']=='ខ្មែរ ไทย Tiếng Việt'


def test_update_check_never_downloads_without_user_consent(tmp_path):
    data=b'installer'
    with Server({},data) as server:
        server.manifest=manifest_for(server.base,data)
        service=stack(tmp_path,server.base,data)
        assert service.check() is not None
        staging=tmp_path/'អ្នកប្រើ'/'MMO Video Studio'/'updates'
        assert not staging.exists() or not list(staging.glob('*.exe'))


def test_updater_security_sources_never_use_shell_true_or_project_defined_url():
    files=[ROOT/'services/update_service.py',ROOT/'services/update_validation_service.py',ROOT/'services/update_manifest_service.py',ROOT/'services/update_download_service.py',ROOT/'app/update_config.py']
    text='\n'.join(p.read_text(encoding='utf-8') for p in files)
    assert 'shell=True' not in text
    assert 'project_manifest_url' not in text and 'template_manifest_url' not in text
    manifest_text=(ROOT/'services/update_manifest_service.py').read_text(encoding='utf-8')
    assert '"Accept": "application/json"' in manifest_text and 'User-Agent' in manifest_text

def test_download_rejects_payload_larger_than_manifest_before_staging_exe(tmp_path):
    expected = b"expected"
    altered = expected + b"-unexpected-extra-bytes"
    with Server({}, altered) as server:
        server.manifest = manifest_for(server.base, expected)
        service = stack(tmp_path, server.base, altered)
        service.check()
        with pytest.raises(Exception, match="expected installer size|download"):
            service.download()
        staging = tmp_path / "អ្នកប្រើ" / "MMO Video Studio" / "updates"
        assert not list(staging.glob("*.exe")) and not list(staging.glob("*.part"))


def test_settings_page_exposes_updates_section_without_duplicate_settings_logic():
    page = (ROOT / "ui/qml/pages/SettingsPage.qml").read_text(encoding="utf-8")
    assert '"Updates"' in page
    assert '../updates/UpdateSettings.qml' in page
    assert 'root.section === "Updates"' in page


def test_update_dialog_surfaces_safe_install_errors_and_only_gates_install_for_active_work():
    dialog = (ROOT / "ui/qml/updates/UpdateAvailableDialog.qml").read_text(encoding="utf-8")
    controller = (ROOT / "ui/controllers/update_controller.py").read_text(encoding="utf-8")
    assert "Updates.errorMessage" in dialog and "Text.PlainText" in dialog
    assert "!Updates.installReady || Updates.activeWorkMessage.length === 0" in dialog
    assert "last_error=str(exc)[:500]" in controller


def test_phase42_runtime_wires_update_temp_into_existing_phase29_cleanup():
    runtime = (ROOT / "app/phase42_runtime.py").read_text(encoding="utf-8")
    assert "CleanupService" in runtime and "StorageCategory.UPDATE_TEMP" in runtime
    assert "managedRoot" in runtime and "_phase42_update_temp" in runtime
    assert '"downloading", "validating", "ready", "installing"' in runtime

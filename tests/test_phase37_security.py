from __future__ import annotations

import hashlib
import io
import json
import logging
import sqlite3
import stat
import subprocess
import zipfile
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

import pytest

from engines.model_sources import ModelSourceError, _trusted_https_url
from media.ffmpeg import FFmpegRunner
from media.ffmpeg_escape import escape_filter_path, subtitles_filter
from services.archive_security_service import (
    ArchiveLimits,
    UnsafeArchive,
    is_sensitive_template_asset,
    read_member_limited,
    safe_archive_name,
    validate_zip_info,
    validate_zip_layout,
    verify_sha256,
)
from services.batch_import_service import BatchImportService
from services.export_filename_service import ExportFilenameService, ExportInvalidFilename
from services.log_redaction_service import LogRedactionService
from services.news_errors import NewsSourceSecurityError
from services.news_source_fetch_service import NewsSourceFetchService, PublicURLPolicy
from services.privacy_service import PrivacyService
from services.safe_path_service import UnsafeManagedPath, safe_copy_destination, safe_delete
from services.security_event_service import SecurityEventService
from services.support_bundle_service import SupportBundleError, SupportBundleService
from services.model_verification_service import ModelVerificationService
from domain.ai_model import AIModel


ATTACK_STRINGS = [
    '"; calc.exe & echo "',
    '../../outside.txt',
    r'C:\Windows\System32\cmd.exe',
    '$(whoami)',
    r'%TEMP%\evil',
    'ខ្មែរ "quoted" ภาษาไทย tiếng Việt $(whoami)',
]


def _zip(path: Path, rows: list[tuple[zipfile.ZipInfo | str, bytes]]) -> Path:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in rows:
            archive.writestr(name, data)
    return path


def _public_resolver(host, port, type=None):
    mapping = {
        'public.example': '93.184.216.34',
        'private.example': '10.0.0.3',
        'loop.example': '127.0.0.1',
        'v6loop.example': '::1',
    }
    ip = mapping.get(host, host if host.replace('.', '').isdigit() else '93.184.216.34')
    family = 10 if ':' in ip else 2
    return [(family, socket_type(), 6, '', (ip, port, 0, 0) if family == 10 else (ip, port))]


def socket_type():
    import socket
    return socket.SOCK_STREAM


# Filesystem security -------------------------------------------------------

def test_path_traversal_delete_blocked(tmp_path):
    root = tmp_path / 'managed'; root.mkdir()
    outside = tmp_path / 'outside.txt'; outside.write_text('keep')
    with pytest.raises(UnsafeManagedPath):
        safe_delete(root / '..' / 'outside.txt', root)
    assert outside.read_text() == 'keep'


def test_external_file_delete_protection(tmp_path):
    root = tmp_path / 'managed'; root.mkdir()
    outside = tmp_path / 'external.mp4'; outside.write_bytes(b'x')
    with pytest.raises(UnsafeManagedPath):
        safe_delete(outside, root)
    assert outside.exists()


def test_symlink_escape_blocked_where_supported(tmp_path):
    root = tmp_path / 'managed'; root.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir(); (outside / 'private.txt').write_text('keep')
    link = root / 'link'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('Symlink creation is unavailable on this host.')
    with pytest.raises(UnsafeManagedPath):
        safe_delete(link, root, recursive=True)
    assert (outside / 'private.txt').exists()


def test_safe_delete_app_owned_child(tmp_path):
    root = tmp_path / 'managed'; child = root / 'cache' / 'item'; child.mkdir(parents=True); (child / 'x').write_text('x')
    assert safe_delete(child, root, recursive=True)
    assert not child.exists()


@pytest.mark.parametrize('name', ['../outside', r'C:\Windows\System32\x', r'\\server\share\x', 'CON.txt', 'NUL', 'file:stream'])
def test_safe_copy_destination_rejects_unsafe_names(tmp_path, name):
    root = tmp_path / 'root'; root.mkdir()
    with pytest.raises(UnsafeManagedPath):
        safe_copy_destination(root, name)


def test_safe_copy_destination_preserves_unicode(tmp_path):
    root = tmp_path / 'root'; root.mkdir()
    target = safe_copy_destination(root, 'ខ្មែរ/ไทย/tiếng-Việt.txt')
    assert target.name == 'tiếng-Việt.txt'
    assert root.resolve() in target.parents


# ZIP/template package security -------------------------------------------

@pytest.mark.parametrize('name', ['../../evil.txt', '/etc/passwd', r'C:\Windows\x', r'\\server\share\x'])
def test_zip_traversal_and_absolute_paths_blocked(name):
    with pytest.raises(UnsafeArchive):
        safe_archive_name(name)


def test_zip_file_count_limit(tmp_path):
    path = tmp_path / 'many.zip'
    _zip(path, [(f'assets/{i}.txt', b'x') for i in range(4)])
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(UnsafeArchive, match='too many'):
            validate_zip_layout(archive, limits=ArchiveLimits(max_members=3))


def test_zip_bomb_compression_ratio_blocked(tmp_path):
    path = tmp_path / 'bomb.zip'
    _zip(path, [('assets/big.txt', b'A' * (2 * 1024 * 1024))])
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(UnsafeArchive, match='compression ratio'):
            validate_zip_layout(archive, limits=ArchiveLimits(max_compression_ratio=20.0))


def test_executable_template_member_rejected():
    info = zipfile.ZipInfo('assets/run.ps1'); info.file_size = 10; info.compress_size = 10
    with pytest.raises(UnsafeArchive, match='executable'):
        validate_zip_info(info)


def test_template_symlink_member_rejected():
    info = zipfile.ZipInfo('assets/link.wav')
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    info.file_size = 3; info.compress_size = 3
    with pytest.raises(UnsafeArchive, match='symbolic link'):
        validate_zip_info(info)


def test_template_checksum_mismatch_detected():
    assert verify_sha256(b'good', hashlib.sha256(b'good').hexdigest())
    assert not verify_sha256(b'changed', hashlib.sha256(b'good').hexdigest())


def test_reference_voice_asset_marked_sensitive():
    assert is_sensitive_template_asset('reference_voice', {})
    assert is_sensitive_template_asset('audio', {'referenceVoice': True})
    assert not is_sensitive_template_asset('music', {})


def test_bounded_member_read(tmp_path):
    path = tmp_path / 'one.zip'; _zip(path, [('assets/a.txt', b'123456')])
    with zipfile.ZipFile(path) as archive:
        with pytest.raises(UnsafeArchive):
            read_member_limited(archive, 'assets/a.txt', limits=ArchiveLimits(max_member_bytes=5))


# Output filename/path hardening -------------------------------------------

@pytest.mark.parametrize('name', ['../out', r'C:\Windows\out', r'\\server\share\out', 'NUL', 'CON.txt', 'x:stream', 'bad\x00name'])
def test_output_path_escape_and_windows_devices_blocked(name):
    with pytest.raises(ExportInvalidFilename):
        ExportFilenameService().sanitize(name)


def test_malicious_shell_filename_is_data_not_path(tmp_path):
    value = '"; calc.exe & echo " ខ្មែរ ไทย Việt'
    clean = ExportFilenameService().sanitize(value)
    assert clean.endswith('.mp4')
    assert '/' not in clean and '\\' not in clean
    assert 'ខ្មែរ' in clean


# Subprocess / FFmpeg -------------------------------------------------------

class _FakePipe(io.StringIO):
    def __iter__(self): return iter(())


class _FakePopen:
    calls = []
    def __init__(self, cmd, **kwargs):
        self.__class__.calls.append((cmd, kwargs)); self.stdout = _FakePipe(); self.stderr = _FakePipe(); self._code = 0
    def wait(self, timeout=None): return self._code
    def poll(self): return self._code
    def terminate(self): self._code = 0
    def kill(self): self._code = 0


def test_command_injection_string_remains_single_argv_element(monkeypatch):
    _FakePopen.calls.clear(); monkeypatch.setattr(subprocess, 'Popen', _FakePopen)
    attack = '"; calc.exe & echo " $(whoami) %TEMP% ខ្មែរ ไทย Việt'
    FFmpegRunner('ffmpeg').run(['-i', attack, '-f', 'null', '-'])
    cmd, kwargs = _FakePopen.calls[0]
    assert attack in cmd and cmd.count(attack) == 1
    assert kwargs['shell'] is False


def test_ffmpeg_filter_paths_escape_quotes_unicode_and_delimiters():
    source = r"C:\Users\អ្នក\ไทย,Việt;clip's.ass"
    escaped = escape_filter_path(source)
    assert r'\,' in escaped and r'\;' in escaped and r"\'" in escaped
    expr = subtitles_filter(source, fonts_dir=r'C:\Fonts\ខ្មែរ')
    assert 'subtitles=filename=' in expr and 'fontsdir=' in expr
    assert 'ខ្មែរ' in expr and 'ไทย' in expr and 'Việt' in expr


# News SSRF ---------------------------------------------------------------

@pytest.mark.parametrize('url', ['file:///etc/passwd', 'ftp://example.com/x', 'gopher://example.com/1', 'data:text/plain,hello', 'http://localhost/x'])
def test_ssrf_unsafe_scheme_and_localhost_blocked(url):
    policy = PublicURLPolicy(resolver=_public_resolver)
    with pytest.raises(NewsSourceSecurityError): policy.validate(url)


@pytest.mark.parametrize('host', ['private.example', 'loop.example', 'v6loop.example'])
def test_ssrf_private_and_loopback_addresses_blocked(host):
    policy = PublicURLPolicy(resolver=_public_resolver)
    with pytest.raises(NewsSourceSecurityError): policy.validate(f'http://{host}/story')


def test_ssrf_public_address_allowed():
    assert PublicURLPolicy(resolver=_public_resolver).validate('https://public.example/story').hostname == 'public.example'


class _RedirectOpener:
    def open(self, req, timeout=None):
        headers = Message(); headers['Location'] = 'http://private.example/secret'
        raise __import__('urllib.error').error.HTTPError(req.full_url, 302, 'Found', headers, None)


def test_redirect_to_private_ip_blocked():
    service = NewsSourceFetchService(policy=PublicURLPolicy(resolver=_public_resolver), opener=_RedirectOpener())
    with pytest.raises(NewsSourceSecurityError): service.fetch('https://public.example/story')


class _Response:
    status = 200
    def __init__(self, url='https://public.example/story'):
        self._url = url; self.headers = Message(); self.headers['Content-Type'] = 'text/plain; charset=utf-8'; self.fp = SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(getpeername=lambda: ('10.0.0.9', 443))))
    def geturl(self): return self._url
    def read(self, n=-1): return b'hello public article text that is long enough'
    def close(self): pass


class _ResponseOpener:
    def open(self, req, timeout=None): return _Response()


def test_dns_rebinding_private_connected_peer_blocked():
    service = NewsSourceFetchService(policy=PublicURLPolicy(resolver=_public_resolver), opener=_ResponseOpener())
    with pytest.raises(NewsSourceSecurityError): service.fetch('https://public.example/story')


# Secrets / support / provider privacy ------------------------------------

def test_credential_redaction_covers_auth_cookie_and_urls(tmp_path):
    redactor = LogRedactionService(home=tmp_path / 'home')
    text = 'Authorization: Bearer TOPSECRET\nSet-Cookie: session=COOKIESECRET\nhttps://x.test/a?token=URLSECRET&ok=1'
    clean = redactor.redact_text(text)
    for secret in ('TOPSECRET', 'COOKIESECRET', 'URLSECRET'):
        assert secret not in clean
    assert '[REDACTED]' in clean


def test_api_key_not_logged_by_security_event(caplog):
    caplog.set_level(logging.WARNING)
    service = SecurityEventService(redaction=LogRedactionService())
    service.record('template_rejected', api_key='SUPERSECRET', url='https://x.test/?token=URLSECRET')
    joined = '\n'.join(record.getMessage() for record in caplog.records)
    assert 'SUPERSECRET' not in joined and 'URLSECRET' not in joined
    assert '[REDACTED]' in joined


def test_support_bundle_gate_rejects_unredacted_api_key(tmp_path):
    root = tmp_path / 'bundle'; root.mkdir(); (root / 'x.log').write_text('api_key=SUPERSECRET')
    service = object.__new__(SupportBundleService)
    with pytest.raises(SupportBundleError): service._privacy_gate(root)


def test_support_bundle_allowlist_has_no_reference_voice_or_project_data():
    joined = '\n'.join(SupportBundleService.SAFE_FILES).lower()
    for forbidden in ('voice', 'reference', 'project.db', 'media', 'transcript', 'subtitle'):
        assert forbidden not in joined


def test_cloud_provider_requires_first_use_privacy_warning():
    service = PrivacyService()
    assert service.requires_first_use_notice('cloud_llm')
    assert service.requires_first_use_notice('custom_online')
    assert not service.requires_first_use_notice('local')
    cloud = next(row for row in service.provider_rows() if row['name'] == 'Cloud AI Providers')
    assert cloud['mode'] == 'Online' and cloud['configured'] is False


# Model / TLS --------------------------------------------------------------

def _model() -> AIModel:
    return AIModel('m1', 'test', 'Test', '', 'voice', '1', 'huggingface', 'org/model', 'unknown', 1, 1, required_files=('model.bin',), install_relative_path='m1')


def test_model_checksum_failure(tmp_path):
    root = tmp_path / 'm1'; root.mkdir(); data = b'actual'; (root / 'model.bin').write_bytes(data)
    manifest = {'app_model_schema_version': 1, 'model_id': 'm1', 'files': [{'path': 'model.bin', 'size': len(data), 'sha256': hashlib.sha256(b'other').hexdigest()}]}
    (root / 'model_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    result = ModelVerificationService().verify(_model(), root)
    assert not result.valid and any('Hash mismatch' in x for x in result.errors)


def test_model_urls_require_trusted_https():
    assert _trusted_https_url('https://huggingface.co/org/model').scheme == 'https'
    assert _trusted_https_url('https://cdn-lfs.hf.co/file').hostname == 'cdn-lfs.hf.co'
    with pytest.raises(ModelSourceError): _trusted_https_url('http://huggingface.co/org/model')
    with pytest.raises(ModelSourceError): _trusted_https_url('https://evil.example/model')


def test_tls_verification_not_disabled_in_model_source():
    source = (Path(__file__).resolve().parents[1] / 'engines/model_sources.py').read_text(encoding='utf-8')
    assert 'verify=False' not in source
    assert '_create_unverified_context' not in source
    assert 'https://huggingface.co/' in source


# Import/DB handling -------------------------------------------------------

def test_malicious_json_is_handled_without_deserialization(tmp_path):
    path = tmp_path / 'rows.json'; path.write_text('{"__reduce__": "$(whoami)"', encoding='utf-8')
    with pytest.raises(Exception) as caught:
        BatchImportService().import_json(path)
    assert 'could not be parsed' in str(caught.value)


def test_sql_attack_string_is_bound_data_not_sql():
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE projects(id TEXT PRIMARY KEY, title TEXT)')
    db.execute('INSERT INTO projects VALUES(?,?)', ('safe', 'Safe'))
    attack = "safe' OR 1=1; DROP TABLE projects; --"
    row = db.execute('SELECT * FROM projects WHERE id = ?', (attack,)).fetchone()
    assert row is None
    assert db.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 1


@pytest.mark.parametrize('attack', ATTACK_STRINGS)
def test_attack_strings_are_never_interpreted_as_managed_destinations(tmp_path, attack):
    root = tmp_path / 'root'; root.mkdir()
    if attack == r'%TEMP%\evil':
        # Managed paths never expand environment syntax; output filenames still
        # reject the path separator.
        managed = safe_copy_destination(root, attack)
        assert '%TEMP%' in str(managed) and root.resolve() in managed.parents
        with pytest.raises(ExportInvalidFilename): ExportFilenameService().sanitize(attack)
    elif '/' in attack or '\\' in attack or ':' in attack:
        with pytest.raises((UnsafeManagedPath, ExportInvalidFilename)):
            try: safe_copy_destination(root, attack)
            except UnsafeManagedPath: raise
    else:
        clean = ExportFilenameService().sanitize(attack)
        assert clean.endswith('.mp4')

# Static integration contracts ---------------------------------------------

def test_template_import_never_uses_extractall():
    source = (Path(__file__).resolve().parents[1] / 'services/template_package_service.py').read_text(encoding='utf-8')
    assert '.extractall(' not in source
    assert 'extract_member_limited' in source
    assert 'safe_delete' in source


def test_privacy_settings_distinguish_local_online_without_marketing_claim():
    root = Path(__file__).resolve().parents[1]
    panel = (root / 'ui/qml/privacy/PrivacySettingsPanel.qml').read_text(encoding='utf-8')
    settings = (root / 'ui/qml/pages/SettingsPage.qml').read_text(encoding='utf-8')
    assert '"Privacy"' in settings and 'PrivacySettingsPanel' in settings
    assert 'Local & Online Processing' in panel and 'Cloud AI Providers' not in panel  # data comes from service, not duplicated in QML
    assert '100% private' not in panel.lower()


def test_security_layer_remains_reachable_from_current_packaged_entrypoint():
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / 'pyproject.toml').read_text(encoding='utf-8')
    main = (root / 'main.py').read_text(encoding='utf-8')
    phase40 = (root / 'app/phase40_runtime.py').read_text(encoding='utf-8')
    phase38 = (root / 'app/phase38_runtime.py').read_text(encoding='utf-8')
    assert 'app.phase40_runtime:run' in pyproject
    assert 'from app.phase40_runtime import run' in main
    assert 'run_phase38' in phase40
    assert 'run_phase37' in phase38


def test_security_documents_cover_updater_and_unresolved_risks():
    root = Path(__file__).resolve().parents[1]
    threat = (root / 'docs/security-threat-model.md').read_text(encoding='utf-8').lower()
    review = (root / 'docs/security-review-phase37.md').read_text(encoding='utf-8').lower()
    assert 'future updater' in threat and 'reference voice' in threat and 'ssrf' in threat
    assert 'remaining risks' in review and 'pip-audit' in review and 'credential' in review

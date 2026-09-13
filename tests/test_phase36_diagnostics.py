from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.diagnostic_result import DiagnosticResult, DiagnosticStatus
from services.diagnostics_preferences_service import DiagnosticsPreferencesService
from services.diagnostics_service import DiagnosticCancelled, DiagnosticsService
from services.environment_report_service import EnvironmentReportService
from services.log_redaction_service import LogRedactionService
from services.support_bundle_service import SupportBundleService


class FakePaths:
    def __init__(self, root: Path):
        self.root = root
        self.models = root / "models"
        self.cache = root / "cache"
        self.temp = root / "temp"
        self.logs = root / "logs"
        self.settings = root / "settings"
        self.downloads = root / "downloads"
        self.exports = root / "exports"
        self.voices = root / "voices"
        self.templates = root / "templates"
        self.assets = root / "assets"
        self.recovery = root / "recovery"
        self.data = root / "data"
        self.database = self.data / "app.db"
        self.default_projects_root = root / "projects"
        self.ensure()

    def ensure(self):
        for item in (
            self.root, self.models, self.cache, self.temp, self.logs, self.settings,
            self.downloads, self.exports, self.voices, self.templates, self.assets,
            self.recovery, self.data, self.default_projects_root,
        ):
            item.mkdir(parents=True, exist_ok=True)


class FakeSettings:
    def __init__(self, paths: FakePaths):
        self.paths = paths
        self.current = SimpleNamespace(
            language="en",
            theme="system",
            performance_profile="auto",
            default_fps=30,
            default_aspect_ratio="16:9",
            ffmpeg_mode="auto",
            ffmpeg_path="",
            ffprobe_path="",
            default_projects_folder=str(paths.default_projects_root),
            reduce_motion="system",
            interface_text_size="default",
            api_key="MUST_NOT_LEAK",
            password="MUST_NOT_LEAK_EITHER",
        )


class FakeReadiness:
    def __init__(self, *, ffmpeg=True, ffprobe=True, gpu="Test GPU", cuda="available"):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.gpu = gpu
        self.cuda = cuda
        self.calls = 0

    def detect(self):
        self.calls += 1
        return SimpleNamespace(
            cpu_name="Test CPU",
            ram_total=16 * 1024**3,
            gpu_name=self.gpu,
            gpu_status="ready" if self.gpu else "unknown",
            cuda_status=self.cuda,
            ffmpeg_available=self.ffmpeg,
            ffprobe_available=self.ffprobe,
            ffmpeg_path="C:/Tools/ffmpeg.exe" if self.ffmpeg else "",
            ffprobe_path="C:/Tools/ffprobe.exe" if self.ffprobe else "",
        )


class FakeDiskMonitor:
    def __init__(self, state="normal"):
        self.state = state

    def check(self, path, label=""):
        return SimpleNamespace(state=SimpleNamespace(value=self.state), free_bytes=20 * 1024**3)


class FakeDatabase:
    def __init__(self, path: Path, version: int = 1):
        self.path = path
        self._version = version
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, name TEXT, applied_at TEXT)")
            if version:
                conn.execute("INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?)", (version, "test", "now"))
            conn.commit()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    def current_version(self):
        return self._version


class BrokenDatabase:
    def connect(self):
        raise sqlite3.DatabaseError("database is broken")

    def current_version(self):
        raise sqlite3.DatabaseError("database is broken")


class FakeRegistry:
    def __init__(self, models):
        self.models = list(models)

    def list_all(self):
        return list(self.models)


class FakeRepo:
    def __init__(self, mapping=None):
        self.mapping = dict(mapping or {})

    def get(self, model_id):
        return self.mapping.get(model_id)


class FakeVerifier:
    def __init__(self, valid=True):
        self.valid = valid
        self.calls = 0

    def verify(self, model, path):
        self.calls += 1
        return SimpleNamespace(valid=self.valid, errors=[] if self.valid else ["Hash mismatch: model.bin"], checked_files=1)


class FakeModelService:
    def __init__(self, root: Path, models, mapping=None, verify=True):
        self.root = root
        self.registry = FakeRegistry(models)
        self.repository = FakeRepo(mapping)
        self.verification_service = FakeVerifier(verify)
        self.install_calls = 0

    def install_path(self, model):
        return self.root / model.model_id

    def install(self, *args, **kwargs):
        self.install_calls += 1
        raise AssertionError("Diagnostics must never install models")


class FakeProjectService:
    def __init__(self, projects):
        self.projects = projects

    def list_projects(self):
        return list(self.projects)


class FakeIntegrity:
    def __init__(self, ok=True):
        self.ok = ok

    def lightweight_check(self):
        return {"quickCheck": "ok" if self.ok else "failed", "foreignKeyIssues": 0 if self.ok else 1, "ok": self.ok}


def model(model_id="voice", purpose="voice"):
    return SimpleNamespace(
        model_id=model_id,
        family=model_id,
        name=model_id.title(),
        purpose_code=purpose,
        version="1.0",
        required_files=("model.bin",),
    )


def installation(installed=True):
    return SimpleNamespace(installed=installed, status="installed" if installed else "not_installed", verification_status="verified" if installed else "unknown")


def make_service(tmp_path: Path, **kwargs):
    paths = kwargs.pop("paths", FakePaths(tmp_path / "app"))
    settings = kwargs.pop("settings", FakeSettings(paths))
    redaction = kwargs.pop("redaction", LogRedactionService(home=tmp_path / "home" / "tester"))
    return DiagnosticsService(paths, settings, redaction=redaction, **kwargs), paths, settings, redaction


def test_quick_diagnostic_orchestration_is_lightweight(tmp_path):
    m = model()
    models = FakeModelService(tmp_path / "models", [m], {m.model_id: installation(False)})
    service, _, _, _ = make_service(
        tmp_path,
        readiness_service=FakeReadiness(),
        database=FakeDatabase(tmp_path / "db.sqlite"),
        model_service=models,
        disk_monitor=FakeDiskMonitor(),
    )
    results = service.quick_check()
    ids = {x.id for x in results}
    assert {"application.version", "system.platform", "storage.quick", "ffmpeg.availability", "database.quick", "models.registry", "engine.tts", "engine.stt", "engine.translation"} <= ids
    assert models.install_calls == 0
    assert models.verification_service.calls == 0


def test_full_diagnostics_orchestration_adds_deep_categories(tmp_path, monkeypatch):
    m = model()
    model_root = tmp_path / "models"
    (model_root / m.model_id).mkdir(parents=True)
    models = FakeModelService(model_root, [m], {m.model_id: installation(True)})
    service, _, _, _ = make_service(tmp_path, readiness_service=FakeReadiness(ffmpeg=False, ffprobe=False), database=FakeDatabase(tmp_path / "db.sqlite"), model_service=models, disk_monitor=FakeDiskMonitor())
    monkeypatch.setattr(service, "_ffmpeg_full_check", lambda: DiagnosticResult("ffmpeg.capabilities", "FFmpeg", "FFmpeg", "not_configured", "missing"))
    results = service.full_diagnostics()
    ids = {x.id for x in results}
    assert "database.integrity" in ids
    assert f"model.{m.model_id}" in ids
    assert "storage.full" in ids
    assert "network.providers" in ids
    assert models.install_calls == 0


def test_cancellation_is_supported(tmp_path):
    service, *_ = make_service(tmp_path)
    event = threading.Event(); event.set()
    with pytest.raises(DiagnosticCancelled):
        service.quick_check(event)


@pytest.mark.parametrize("ffmpeg,ffprobe,expected", [(True, True, "ready"), (True, False, "warning"), (False, False, "not_configured")])
def test_ffmpeg_and_ffprobe_found_missing(tmp_path, ffmpeg, ffprobe, expected):
    service, *_ = make_service(tmp_path, readiness_service=FakeReadiness(ffmpeg=ffmpeg, ffprobe=ffprobe))
    result = next(x for x in service.quick_check() if x.id == "ffmpeg.availability")
    assert result.status == expected


def test_filter_detection_is_exact_token_based(tmp_path):
    service, *_ = make_service(tmp_path)
    listing = " ... scale V->V\n T.C overlay VV->V\n ..C chromakey V->V\n"
    assert service._has_listing_name(listing, "scale")
    assert service._has_listing_name(listing, "overlay")
    assert not service._has_listing_name(listing, "ass")


def test_encoder_detection_does_not_confuse_substrings(tmp_path):
    service, *_ = make_service(tmp_path)
    listing = " V..... libx264 H.264\n V....D h264_nvenc NVIDIA\n"
    assert service._has_listing_name(listing, "libx264")
    assert service._has_listing_name(listing, "h264_nvenc")
    assert not service._has_listing_name(listing, "h264_qsv")


def test_storage_writable_and_unwritable(tmp_path, monkeypatch):
    service, *_ = make_service(tmp_path, disk_monitor=FakeDiskMonitor())
    assert service._storage_check().status == "ready"
    monkeypatch.setattr("services.diagnostics_service.os.access", lambda *args, **kwargs: False)
    assert service._storage_check().status == "failed"


def test_low_disk_is_warning(tmp_path):
    service, *_ = make_service(tmp_path, disk_monitor=FakeDiskMonitor("low"))
    result = service._storage_check()
    assert result.status == "warning"
    assert "low disk" in result.details.lower()


def test_database_healthy_and_integrity(tmp_path):
    db = FakeDatabase(tmp_path / "app.sqlite", version=1)
    service, *_ = make_service(tmp_path, database=db)
    assert service._database_quick_check().status == "ready"
    full = service._database_full_check()
    assert full.status == "ready"
    assert "transactionProbe=1" in full.details


def test_database_failure_is_friendly(tmp_path):
    service, *_ = make_service(tmp_path, database=BrokenDatabase())
    result = service._database_quick_check()
    assert result.status == "failed"
    assert "broken" in result.details


def test_pending_migration_detection(tmp_path, monkeypatch):
    import services.diagnostics_service as module
    monkeypatch.setattr(module, "MIGRATIONS", (SimpleNamespace(version=1), SimpleNamespace(version=3)))
    service, *_ = make_service(tmp_path, database=FakeDatabase(tmp_path / "app.sqlite", version=1))
    result = service._database_quick_check()
    assert result.status == "warning"
    assert result.metadata["pendingMigrations"] == 1


def test_model_missing_is_not_configured(tmp_path):
    m = model("voxcpm2", "voice")
    models = FakeModelService(tmp_path / "models", [m], {m.model_id: installation(False)})
    service, *_ = make_service(tmp_path, model_service=models)
    result = service._model_full_checks()[0]
    assert result.status == "not_configured"
    assert result.metadata["loadTested"] is False


def test_model_installed_verified_without_loading(tmp_path):
    m = model("voxcpm2", "voice")
    models = FakeModelService(tmp_path / "models", [m], {m.model_id: installation(True)}, verify=True)
    path = models.install_path(m); path.mkdir(parents=True); (path / "model.bin").write_bytes(b"x")
    service, *_ = make_service(tmp_path, model_service=models)
    result = service._model_full_checks()[0]
    assert result.status == "ready"
    assert result.metadata == {"modelId": "voxcpm2", "installed": True, "verified": True, "loadTested": False, "action": ""}
    assert models.install_calls == 0


def test_model_corrupt_routes_to_existing_repair(tmp_path):
    m = model("voxcpm2", "voice")
    models = FakeModelService(tmp_path / "models", [m], {m.model_id: installation(True)}, verify=False)
    path = models.install_path(m); path.mkdir(parents=True); (path / "model.bin").write_bytes(b"bad")
    service, *_ = make_service(tmp_path, model_service=models)
    result = service._model_full_checks()[0]
    assert result.status == "failed"
    assert result.metadata["action"] == "repair_model"


@pytest.mark.parametrize("gpu,cuda", [("NVIDIA Test", "available"), (None, "unavailable"), (None, "unknown")])
def test_gpu_present_absent_and_no_cuda_not_fatal(tmp_path, gpu, cuda):
    service, *_ = make_service(tmp_path, readiness_service=FakeReadiness(gpu=gpu, cuda=cuda))
    result = next(x for x in service.quick_check() if x.id == "system.platform")
    assert result.status in {"ready", "warning"}
    assert "CPU workflows remain supported" in result.details


def test_project_missing_media_and_unicode_paths(tmp_path):
    project_root = tmp_path / "គម្រោង-ไทย-Tiếng Việt"
    project_root.mkdir()
    project_id = "p1"
    (project_root / "project.json").write_text(json.dumps({"project_id": project_id, "version": 1}, ensure_ascii=False), encoding="utf-8")
    db = FakeDatabase(tmp_path / "app.sqlite")
    with db.connect() as conn:
        conn.execute("CREATE TABLE media_assets(id TEXT, project_id TEXT, file_path TEXT)")
        conn.execute("INSERT INTO media_assets VALUES(?,?,?)", ("m1", project_id, "media/ខ្មែរ-ไทย-TiếngViệt.mp4"))
        conn.commit()
    project = SimpleNamespace(project_id=project_id, project_path=str(project_root), version=1)
    service, *_ = make_service(tmp_path, database=db, project_service=FakeProjectService([project]), project_integrity_service=FakeIntegrity(True))
    results = service.diagnose_project(project_id)
    media = next(x for x in results if x.id == "project.media_refs")
    assert media.status == "warning"
    assert media.metadata["missingCount"] == 1
    assert "ខ្មែរ" in media.details


def test_project_invalid_reference_integrity(tmp_path):
    project_root = tmp_path / "project"; project_root.mkdir()
    (project_root / "project.json").write_text('{"project_id":"p1","version":1}', encoding="utf-8")
    project = SimpleNamespace(project_id="p1", project_path=str(project_root), version=1)
    service, *_ = make_service(tmp_path, database=FakeDatabase(tmp_path / "db.sqlite"), project_service=FakeProjectService([project]), project_integrity_service=FakeIntegrity(False))
    result = next(x for x in service.diagnose_project("p1") if x.id == "project.references")
    assert result.status == "failed"


@pytest.mark.parametrize(
    "message,category",
    [
        ("No such file or directory input.mp4", "Missing Media"),
        ("No such filter: fancy_filter", "Unsupported Filter"),
        ("Error while opening encoder h264_nvenc", "Encoder Failure"),
        ("No space left on device", "Disk Full"),
        ("Invalid audio graph near amix", "Invalid Audio Graph"),
        ("libass unable to load font", "Subtitle/Font Problem"),
        ("mysterious ffmpeg exit 1", "Unknown FFmpeg Failure"),
    ],
)
def test_render_failure_categorization(tmp_path, message, category):
    service, *_ = make_service(tmp_path)
    result = service.diagnose_render_failure(message)
    assert result.summary == category
    assert result.metadata["referenceId"].startswith("RND-")


def test_redacts_authorization_tokens_passwords_cookies_and_query_secrets(tmp_path):
    redactor = LogRedactionService(home="C:/Users/ActualName")
    text = (
        "Authorization: Bearer SECRET123\napi_key=TOPSECRET password=hello\n"
        "Cookie: sid=COOKIESECRET\nhttps://api.example.test/v1?q=ok&access_token=URLSECRET\n"
        "https://provider.test/v1?key=PROVIDERKEY\nC:\\Users\\ActualName\\Videos\\private.mp4"
    )
    clean = redactor.redact_text(text)
    for secret in ("SECRET123", "TOPSECRET", "hello", "COOKIESECRET", "URLSECRET", "PROVIDERKEY", "ActualName"):
        assert secret not in clean
    assert "[REDACTED]" in clean
    assert "%USERPROFILE%" in clean


def test_recursive_secret_fields_are_redacted(tmp_path):
    redactor = LogRedactionService(home=tmp_path)
    clean = redactor.redact_value({"nested": {"password": "hello", "apiKey": "x", "safe": "yes"}})
    assert clean["nested"]["password"] == "[REDACTED]"
    assert clean["nested"]["apiKey"] == "[REDACTED]"
    assert clean["nested"]["safe"] == "yes"


def test_diagnostics_preferences_restart_persistence(tmp_path):
    first = DiagnosticsPreferencesService(tmp_path)
    first.set_log_severity("warning")
    first.set_log_limit(777)
    second = DiagnosticsPreferencesService(tmp_path)
    assert second.log_severity == "warning"
    assert second.log_limit == 777


def _bundle_fixture(tmp_path, *, unicode_root=False):
    root = tmp_path / ("កម្មវិធី-ไทย-Tiếng Việt" if unicode_root else "app")
    paths = FakePaths(root)
    settings = FakeSettings(paths)
    redaction = LogRedactionService(home=tmp_path)
    db = FakeDatabase(paths.database)
    diagnostics = DiagnosticsService(paths, settings, database=db, redaction=redaction)
    environment = EnvironmentReportService(paths, settings, redaction, database=db)
    bundles = SupportBundleService(paths, environment, diagnostics, redaction)
    return paths, diagnostics, bundles


def test_mandatory_secret_redaction_in_support_bundle(tmp_path):
    paths, diagnostics, bundles = _bundle_fixture(tmp_path)
    (paths.logs / "app.log").write_text(
        "ERROR Authorization: Bearer SECRET123\nWARNING api_key=TOPSECRET\nERROR password=hello\n",
        encoding="utf-8",
    )
    results = [DiagnosticResult(
        "secret-test", "Application", "Secret test", "failed",
        "api_key=TOPSECRET", "Authorization: Bearer SECRET123", "password=hello",
        technical_details="https://x.test/?token=SECRET123",
        metadata={"password": "hello"},
    )]
    bundle = bundles.create(results)
    with zipfile.ZipFile(bundle.path) as archive:
        names = archive.namelist()
        payload = b"\n".join(archive.read(name) for name in names).decode("utf-8")
    for secret in ("SECRET123", "TOPSECRET", "hello", "MUST_NOT_LEAK", "MUST_NOT_LEAK_EITHER"):
        assert secret not in payload
        assert all(secret not in name for name in names)
    assert "[REDACTED]" in payload


def test_mandatory_support_bundle_excludes_private_project_content_and_media(tmp_path):
    paths, diagnostics, bundles = _bundle_fixture(tmp_path)
    project = paths.default_projects_root / "private-project"; project.mkdir()
    (project / "script.txt").write_text("ខ្មែរ ไทย Tiếng Việt PRIVATE_SCRIPT_CONTENT", encoding="utf-8")
    (project / "reference_voice.json").write_text('{"voice":"PRIVATE_VOICE_METADATA"}', encoding="utf-8")
    (project / "news_sources.json").write_text('{"url":"https://private.example/PRIVATE_NEWS"}', encoding="utf-8")
    (project / "video.mp4").write_bytes(b"PRIVATE_MEDIA_BYTES")
    (project / "project.db").write_bytes(b"PRIVATE_PROJECT_DATABASE")
    bundle = bundles.create([])
    with zipfile.ZipFile(bundle.path) as archive:
        names = archive.namelist()
        payload = b"\n".join(archive.read(name) for name in names)
    assert names == list(SupportBundleService.SAFE_FILES)
    for private in (b"PRIVATE_SCRIPT_CONTENT", b"PRIVATE_VOICE_METADATA", b"PRIVATE_NEWS", b"PRIVATE_MEDIA_BYTES", b"PRIVATE_PROJECT_DATABASE"):
        assert private not in payload
    assert not any("project" in name.lower() or name.endswith((".mp4", ".wav", ".sqlite", ".db")) for name in names)


def test_bundle_zip_paths_are_safe(tmp_path):
    _, _, bundles = _bundle_fixture(tmp_path)
    bundle = bundles.create([])
    with zipfile.ZipFile(bundle.path) as archive:
        assert archive.testzip() is None
        for info in archive.infolist():
            assert not Path(info.filename).is_absolute()
            assert ".." not in Path(info.filename).parts


def test_unicode_paths_bundle_success(tmp_path):
    paths, _, bundles = _bundle_fixture(tmp_path, unicode_root=True)
    (paths.logs / "កម្មវិធី-ไทย-TiếngViệt.log").write_text("ERROR Unicode diagnostic line", encoding="utf-8")
    bundle = bundles.create([])
    assert bundle.path.is_file()
    assert zipfile.is_zipfile(bundle.path)


def test_recent_logs_are_bounded_filtered_and_redacted(tmp_path):
    service, paths, _, _ = make_service(tmp_path)
    lines = [f"INFO item {i}" for i in range(100)] + ["ERROR Authorization: Bearer SECRET123"]
    (paths.logs / "app.log").write_text("\n".join(lines), encoding="utf-8")
    rows = service.recent_logs("error", 50)
    assert len(rows) == 1
    assert rows[0]["severity"] == "error"
    assert "SECRET123" not in rows[0]["message"]


def test_short_report_excludes_technical_details(tmp_path):
    service, *_ = make_service(tmp_path)
    result = DiagnosticResult("x", "Rendering", "Render", "failed", "Friendly", recommendation="Fix it", technical_details="SECRET_TECH")
    report = service.short_report([result])
    assert "Friendly" in report
    assert "SECRET_TECH" not in report


def test_safe_repair_only_recreates_app_owned_directories(tmp_path):
    service, paths, *_ = make_service(tmp_path)
    shutil.rmtree(paths.assets)
    service.rebuild_app_owned_directories()
    assert paths.assets.is_dir()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg unavailable in execution environment")
def test_real_ffmpeg_generated_source_smoke(tmp_path):
    service, *_ = make_service(tmp_path)
    assert service._ffmpeg_source_smoke(shutil.which("ffmpeg")) is True


def test_full_diagnostics_exposes_all_required_categories(tmp_path, monkeypatch):
    service, *_ = make_service(tmp_path, database=FakeDatabase(tmp_path / "db.sqlite"), disk_monitor=FakeDiskMonitor())
    monkeypatch.setattr(service, "_ffmpeg_full_check", lambda: DiagnosticResult("ffmpeg.capabilities", "FFmpeg", "FFmpeg", "not_configured", "missing"))
    categories = {item.category for item in service.full_diagnostics()}
    required = {
        "Application", "System", "Storage", "FFmpeg", "Database", "Projects", "Media",
        "Models", "TTS", "STT", "Translation", "Rendering", "Assets", "Templates",
        "Batch", "Recovery", "Network Providers",
    }
    assert required <= categories


def test_qml_and_runtime_contracts_are_present():
    root = Path(__file__).resolve().parents[1]
    page = (root / "ui/qml/diagnostics/DiagnosticsPage.qml").read_text(encoding="utf-8")
    bundle = (root / "ui/qml/diagnostics/SupportBundleDialog.qml").read_text(encoding="utf-8")
    logs = (root / "ui/qml/diagnostics/LogViewer.qml").read_text(encoding="utf-8")
    main = (root / "ui/qml/Main.qml").read_text(encoding="utf-8")
    runtime = (root / "app/phase36_runtime.py").read_text(encoding="utf-8")
    controller = (root / "ui/controllers/diagnostics_controller.py").read_text(encoding="utf-8")
    render = (root / "ui/qml/render/RenderDialog.qml").read_text(encoding="utf-8")
    assert "Run Quick Check" in page and "Run Full Diagnostics" in page and "Diagnose Current Project" in page
    assert "Nothing is uploaded" in bundle and "Not included" in bundle
    assert "Recent bounded logs" in logs and "Open Logs Folder" in logs
    assert 'diagnostics:"diagnostics/DiagnosticsPage.qml"' in main
    assert "run_phase35" in runtime and "p31._install" in runtime
    assert "worker_pool.submit" in controller
    assert "Diagnose Render" in render and "lastFailureTechnical" in render
    assert "DiagnosticRenderController" in runtime and "lastFailureTechnical" in runtime


def test_no_model_install_or_upload_path_in_core_services():
    root = Path(__file__).resolve().parents[1]
    diagnostics_source = (root / "services/diagnostics_service.py").read_text(encoding="utf-8")
    bundle_source = (root / "services/support_bundle_service.py").read_text(encoding="utf-8")
    assert "model_service.install(" not in diagnostics_source
    assert "requests." not in diagnostics_source
    assert "requests." not in bundle_source
    assert "urllib.request" not in bundle_source
    assert "httpx" not in bundle_source
    assert "socket." not in bundle_source


def test_support_bundle_fixed_allowlist_has_no_private_types():
    joined = "\n".join(SupportBundleService.SAFE_FILES).lower()
    for forbidden in ("project.db", ".sqlite", ".mp4", ".wav", "recovery", "transcript", "subtitle", "voice"):
        assert forbidden not in joined

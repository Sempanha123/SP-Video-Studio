from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from domain.ai_model import AIModel, ModelCompatibility, ModelPurpose
from domain.model_installation import ModelInstallation, ModelInstallStatus, VerificationStatus
from domain.system_readiness import SystemReadiness
from engines.model_registry import ModelRegistry
from engines.model_sources import DownloadCancelled, ModelSourceError, RemoteModelFile
from services.model_compatibility_service import ModelCompatibilityService
from services.model_download_service import ModelDownloadService
from services.model_service import ModelError, ModelService
from services.model_verification_service import ModelVerificationService
from storage.database import SQLiteDatabase
from storage.repositories.model_repository import ModelRepository
from workers.cancellation import CancellationToken


class FakeSource:
    def __init__(self, files: dict[str, bytes], *, fail_times: int = 0) -> None:
        self.files = files
        self.fail_times = fail_times
        self.calls = 0

    def list_files(self, model: AIModel) -> list[RemoteModelFile]:
        result = []
        for path, data in self.files.items():
            result.append(RemoteModelFile(path, len(data), f"fake://{path}", hashlib.sha256(data).hexdigest()))
        return result

    def download_file(self, remote, destination, cancellation, progress):
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ModelSourceError("temporary network failure")
        data = self.files[remote.path]
        destination.parent.mkdir(parents=True, exist_ok=True)
        existing = destination.stat().st_size if destination.exists() else 0
        with destination.open("ab") as handle:
            for index in range(existing, len(data), 3):
                if cancellation.is_cancelled:
                    raise DownloadCancelled("cancelled")
                chunk = data[index : index + 3]
                handle.write(chunk)
                progress(min(index + len(chunk), len(data)), len(data))
        return len(data)


def fake_model() -> AIModel:
    return AIModel(
        model_id="fake-model",
        family="fake",
        name="Fake Model",
        description="Tiny test model",
        purpose=ModelPurpose.VOICE,
        version="1",
        source="fake",
        source_identifier="test/fake",
        license="MIT",
        download_size_bytes=32,
        disk_size_bytes=64,
        supports_cpu=True,
        supports_cuda=False,
        minimum_ram_bytes=1,
        recommended_ram_bytes=1,
        required_files=("config.json", "weights.bin"),
        install_relative_path="fake/default",
    )


def make_service(tmp_path: Path, source: FakeSource | None = None):
    db = SQLiteDatabase(tmp_path / "data" / "app.db")
    db.initialize()
    repo = ModelRepository(db)
    registry = ModelRegistry([fake_model()])
    verifier = ModelVerificationService()
    source = source or FakeSource({"config.json": b"{}", "weights.bin": b"abcdef123456"})
    downloader = ModelDownloadService(tmp_path / "models", source, verifier, retries=3, backoff_seconds=0)
    compat = ModelCompatibilityService()
    service = ModelService(registry, repo, downloader, verifier, compat, tmp_path / "models")
    return service, repo, source, db


def test_registry_loads_official_phase7_entries_and_unique_ids():
    registry = ModelRegistry()
    models = registry.list_all()
    ids = [model.model_id for model in models]
    assert len(ids) == len(set(ids))
    assert {"voxcpm2", "whisper-small", "whisper-medium", "whisper-large-v3"} <= set(ids)
    assert registry.get("voxcpm2").source_identifier == "openbmb/VoxCPM2"
    assert registry.get("whisper-large-v3").source_identifier == "Systran/faster-whisper-large-v3"


def test_model_installation_serialization_and_repository(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db")
    db.initialize()
    assert db.current_version() == 6
    repo = ModelRepository(db)
    item = ModelInstallation(
        model_id="demo",
        installed=True,
        status=ModelInstallStatus.INSTALLED,
        install_path="X:/models/demo",
        installed_version="1",
        verification_status=VerificationStatus.VERIFIED,
        metadata={"hello": "ពិភពលោក"},
    )
    repo.upsert(item)
    loaded = repo.get("demo")
    assert loaded is not None
    assert loaded.installed is True
    assert loaded.status == "installed"
    assert loaded.metadata["hello"] == "ពិភពលោក"
    repo.remove("demo")
    assert repo.get("demo") is None


def test_successful_atomic_install_and_manifest(tmp_path: Path):
    service, repo, _, _ = make_service(tmp_path)
    progress = []
    installed = service.install("fake-model", CancellationToken(), progress.append)
    assert installed.status == "installed"
    target = tmp_path / "models" / "fake" / "default"
    assert (target / "weights.bin").read_bytes() == b"abcdef123456"
    manifest = json.loads((target / "model_manifest.json").read_text())
    assert manifest["model_id"] == "fake-model"
    assert manifest["verification"] == "verified"
    assert not (tmp_path / "models" / ".downloads" / "fake-model").exists()
    assert progress[-1].state == "completed"
    assert repo.get("fake-model").verification_status == "verified"


def test_download_retry_then_success(tmp_path: Path):
    source = FakeSource({"config.json": b"{}", "weights.bin": b"abcdef"}, fail_times=1)
    service, _, _, _ = make_service(tmp_path, source)
    service.install("fake-model", CancellationToken())
    assert source.calls >= 3  # one retry plus second file


def test_download_cancellation_leaves_resumable_partial(tmp_path: Path):
    service, repo, _, _ = make_service(tmp_path)
    token = CancellationToken()
    token.cancel()
    with pytest.raises(DownloadCancelled):
        service.install("fake-model", token)
    loaded = repo.get("fake-model")
    assert loaded is not None
    assert loaded.status == "paused"


def test_interrupted_download_recovery(tmp_path: Path):
    service, repo, _, _ = make_service(tmp_path)
    partial = tmp_path / "models" / ".downloads" / "fake-model"
    partial.mkdir(parents=True)
    (partial / "weights.bin.part").write_bytes(b"abc")
    rows = service.refresh(SystemReadiness(ram_total=8 * 1024**3))
    assert rows[0]["status"] == "paused"
    assert repo.get("fake-model").status == "paused"
    service.remove_partial("fake-model")
    assert not partial.exists()


def test_verifier_detects_missing_size_and_hash_errors(tmp_path: Path):
    model = fake_model()
    folder = tmp_path / "model"
    folder.mkdir()
    (folder / "config.json").write_bytes(b"{}")
    (folder / "weights.bin").write_bytes(b"abc")
    manifest = {
        "app_model_schema_version": 1,
        "model_id": model.model_id,
        "files": [
            {"path": "config.json", "size": 2, "sha256": hashlib.sha256(b"{}").hexdigest()},
            {"path": "weights.bin", "size": 3, "sha256": hashlib.sha256(b"different").hexdigest()},
        ],
    }
    (folder / "model_manifest.json").write_text(json.dumps(manifest))
    result = ModelVerificationService().verify(model, folder)
    assert result.valid is False
    assert any("Hash mismatch" in error for error in result.errors)
    (folder / "weights.bin").unlink()
    result = ModelVerificationService().verify(model, folder)
    assert any("Missing file" in error or "Required file" in error for error in result.errors)


def test_missing_or_invalid_manifest_is_repair_required(tmp_path: Path):
    service, _, _, _ = make_service(tmp_path)
    target = tmp_path / "models" / "fake" / "default"
    target.mkdir(parents=True)
    (target / "weights.bin").write_bytes(b"data")
    assert service.refresh()[0]["status"] == "repair_required"
    (target / "model_manifest.json").write_text("not json")
    assert service.refresh()[0]["status"] == "repair_required"


def test_compatibility_enough_ram_cpu_and_low_ram():
    model = fake_model()
    compat = ModelCompatibilityService()
    okay = compat.assess(model, SystemReadiness(ram_total=8 * 1024**3, cuda_status="unavailable"))
    assert okay.status == ModelCompatibility.COMPATIBLE
    heavier = AIModel(**{**model.__dict__, "minimum_ram_bytes": 16 * 1024**3}) if hasattr(model, "__dict__") else None
    if heavier is None:
        heavier = AIModel(
            model_id="heavy", family="fake", name="Heavy", description="x", purpose=ModelPurpose.VOICE,
            version="1", source="fake", source_identifier="test/heavy", license="MIT",
            download_size_bytes=1, disk_size_bytes=1, supports_cpu=True, supports_cuda=False,
            minimum_ram_bytes=16 * 1024**3, install_relative_path="fake/heavy",
        )
    low = compat.assess(heavier, SystemReadiness(ram_total=8 * 1024**3))
    assert low.status == ModelCompatibility.NOT_RECOMMENDED
    assert compat.assess(model, None).status == ModelCompatibility.UNKNOWN


def test_cuda_model_compatibility_variants():
    registry = ModelRegistry()
    model = registry.get("voxcpm2")
    compat = ModelCompatibilityService()
    ready = compat.assess(model, SystemReadiness(ram_total=32 * 1024**3, cuda_status="available", gpu_memory_total=12 * 1024**3))
    assert ready.status == ModelCompatibility.COMPATIBLE
    cpu_only = compat.assess(model, SystemReadiness(ram_total=32 * 1024**3, cuda_status="unavailable"))
    assert cpu_only.status == ModelCompatibility.COMPATIBLE_WITH_WARNING


def test_safe_model_deletion_guard_and_remove_does_not_touch_project(tmp_path: Path):
    service, _, _, _ = make_service(tmp_path)
    service.install("fake-model", CancellationToken())
    project = tmp_path / "Projects" / "important" / "project.json"
    project.parent.mkdir(parents=True)
    project.write_text("{}")
    service.remove("fake-model")
    assert project.exists()
    assert not (tmp_path / "models" / "fake" / "default").exists()
    with pytest.raises(ModelError):
        service._assert_safe_managed_model_path(fake_model(), tmp_path / "Projects")


def test_refresh_discovers_valid_install_without_database_record(tmp_path: Path):
    service, repo, _, _ = make_service(tmp_path)
    service.install("fake-model", CancellationToken())
    repo.remove("fake-model")
    rows = service.refresh()
    assert rows[0]["status"] == "installed"
    assert repo.get("fake-model") is not None


def test_family_status_and_storage_calculation(tmp_path: Path):
    service, _, _, _ = make_service(tmp_path)
    assert service.family_status("fake") == "not-installed"
    service.install("fake-model", CancellationToken())
    assert service.family_status("fake") == "installed"
    assert service.total_storage_bytes() > 0


def test_unicode_model_root_path(tmp_path: Path):
    root = tmp_path / "ម៉ូដែល AI"
    db = SQLiteDatabase(tmp_path / "unicode.db")
    db.initialize()
    repo = ModelRepository(db)
    registry = ModelRegistry([fake_model()])
    verifier = ModelVerificationService()
    source = FakeSource({"config.json": b"{}", "weights.bin": b"abcdef"})
    downloader = ModelDownloadService(root, source, verifier, retries=1, backoff_seconds=0)
    service = ModelService(registry, repo, downloader, verifier, ModelCompatibilityService(), root)
    service.install("fake-model", CancellationToken())
    assert (root / "fake" / "default" / "weights.bin").is_file()


def test_huggingface_source_rejects_path_traversal(monkeypatch):
    from engines.model_sources import HuggingFaceSource, ModelSourceError

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"siblings": [{"rfilename": "../escape.bin", "size": 1}]}).encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(ModelSourceError):
        HuggingFaceSource().list_files(fake_model())


def test_download_service_rolls_back_failed_stage_without_false_install(tmp_path: Path):
    source = FakeSource({"config.json": b"{}"})  # required weights.bin never arrives
    service, repo, _, _ = make_service(tmp_path, source)
    with pytest.raises(ModelError):
        service.install("fake-model", CancellationToken())
    state = repo.get("fake-model")
    assert state is not None
    assert state.status == "failed"
    assert not (tmp_path / "models" / "fake" / "default").exists()


def test_readiness_uses_model_manager_family_status(tmp_path: Path):
    from app.paths import AppPaths
    from domain.settings import AppSettings
    from services.system_readiness_service import SystemReadinessService

    root = tmp_path / "runtime"
    paths = AppPaths(
        root=root,
        models=root / "models",
        cache=root / "cache",
        temp=root / "temp",
        logs=root / "logs",
        settings=root / "settings",
        downloads=root / "downloads",
    )
    paths.ensure()
    settings = AppSettings(default_projects_folder=str(tmp_path / "Projects"))
    service = SystemReadinessService(
        paths,
        lambda: settings,
        model_status_provider=lambda family: "installed" if family == "voxcpm2" else "repair-required",
    )
    result = SystemReadiness()
    service._detect_models(result)
    assert result.voxcpm_status == "installed"
    assert result.whisper_status == "repair-required"

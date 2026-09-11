from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from app.paths import AppPaths
from domain.settings import AppSettings
from domain.system_readiness import SystemReadiness
from media.ffmpeg_locator import ExecutableInfo
from services.system_readiness_service import (
    LOW_DISK_CRITICAL_BYTES,
    LOW_DISK_WARNING_BYTES,
    SystemReadinessService,
)


class StubLocator:
    def __init__(self, available: bool = True) -> None:
        self.available = available

    def discover(self, ffmpeg_custom=None, ffprobe_custom=None):
        if self.available:
            return (
                ExecutableInfo(True, "/tools/ffmpeg", "7.1"),
                ExecutableInfo(True, "/tools/ffprobe", "7.1"),
            )
        return ExecutableInfo(False), ExecutableInfo(False)


def make_paths(tmp_path: Path) -> AppPaths:
    root = tmp_path / "app"
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
    return paths


def make_service(tmp_path: Path, locator=None):
    paths = make_paths(tmp_path)
    settings = AppSettings.defaults(tmp_path / "projects")
    return SystemReadinessService(
        paths,
        lambda: settings,
        ffmpeg_locator=locator or StubLocator(),
    ), paths, settings


def test_cpu_and_ram_readiness_structure(monkeypatch, tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    monkeypatch.setattr("services.system_readiness_service.platform.system", lambda: "Windows")
    monkeypatch.setattr("services.system_readiness_service.platform.release", lambda: "11")
    monkeypatch.setattr("services.system_readiness_service.platform.machine", lambda: "AMD64")
    monkeypatch.setattr("services.system_readiness_service.platform.processor", lambda: "Test CPU")
    import psutil
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: 16 if logical else 8)
    monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(total=32 * 1024**3, available=18 * 1024**3))

    result = SystemReadiness()
    service._detect_os_cpu_memory(result)

    assert result.os_name == "Windows"
    assert result.cpu_name == "Test CPU"
    assert result.cpu_cores_physical == 8
    assert result.cpu_cores_logical == 16
    assert result.ram_total == 32 * 1024**3
    assert result.ram_available == 18 * 1024**3


def test_gpu_detection_fallback_is_nonfatal(monkeypatch, tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    monkeypatch.setattr(service, "_detect_nvidia", lambda: None)
    monkeypatch.setattr(service, "_detect_windows_gpu", lambda: ())
    monkeypatch.setitem(sys.modules, "torch", None)
    result = SystemReadiness()

    service._detect_gpu_cuda(result)

    assert result.gpu_status == "unknown"
    assert result.gpu_name is None
    assert result.cuda_status == "unknown"


def test_nvidia_without_torch_means_cuda_possibly_available(monkeypatch, tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    monkeypatch.setattr(
        service,
        "_detect_nvidia",
        lambda: {"name": "NVIDIA Test", "memory_total": "12288", "memory_free": "8192", "cuda_version": "12.4"},
    )
    monkeypatch.setitem(sys.modules, "torch", None)
    result = SystemReadiness()

    service._detect_gpu_cuda(result)

    assert result.gpu_vendor == "NVIDIA"
    assert result.gpu_status == "ready"
    assert result.cuda_status == "possibly_available"
    assert result.cuda_version == "12.4"


def test_media_tool_readiness_uses_locator(tmp_path: Path):
    service, _, _ = make_service(tmp_path, StubLocator(True))
    result = SystemReadiness()
    service._detect_media_tools(result)
    assert result.ffmpeg_available is True
    assert result.ffprobe_available is True
    assert result.ffmpeg_version == "7.1"


def test_disk_space_detection_and_thresholds(monkeypatch, tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    configured = tmp_path / "projects"
    configured.mkdir()
    monkeypatch.setattr(
        "services.system_readiness_service.shutil.disk_usage",
        lambda _: SimpleNamespace(total=100 * 1024**3, used=95 * 1024**3, free=5 * 1024**3),
    )
    disk = service._disk_readiness("Projects", configured, configured)
    assert disk.status == "warning"
    assert disk.free_bytes < LOW_DISK_WARNING_BYTES
    assert disk.free_bytes > LOW_DISK_CRITICAL_BYTES


def test_critical_disk_space(monkeypatch, tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    target = tmp_path / "disk"
    target.mkdir()
    monkeypatch.setattr(
        "services.system_readiness_service.shutil.disk_usage",
        lambda _: SimpleNamespace(total=20 * 1024**3, used=19 * 1024**3, free=1 * 1024**3),
    )
    assert service._disk_readiness("Temp", target, target).status == "critical"


def test_overall_readiness_requires_ffmpeg(tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    result = SystemReadiness(gpu_status="ready", ffmpeg_available=False, ffprobe_available=False)
    service._calculate_overall(result)
    assert result.overall_status == "setup-required"
    assert any("FFmpeg" in warning for warning in result.warnings)


def test_missing_ai_models_are_warning_not_critical(tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    result = SystemReadiness(
        gpu_status="ready",
        ffmpeg_available=True,
        ffprobe_available=True,
        voxcpm_status="not-installed",
        whisper_status="not-installed",
    )
    service._calculate_overall(result)
    assert result.overall_status == "ready-with-warnings"


def test_model_status_only_reports_installed_for_nonempty_folder(tmp_path: Path):
    service, paths, _ = make_service(tmp_path)
    model = paths.models / "voxcpm2"
    model.mkdir()
    assert service._model_status(("voxcpm2",)) == "not-installed"
    (model / "model.bin").write_bytes(b"model")
    assert service._model_status(("voxcpm2",)) == "installed"

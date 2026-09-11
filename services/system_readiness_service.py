from __future__ import annotations

import csv
import io
import logging
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.paths import AppPaths
from domain.settings import AppSettings
from domain.system_readiness import DiskReadiness, SystemReadiness, format_bytes
from media.ffmpeg_locator import FFmpegLocator

LOW_DISK_WARNING_BYTES = 10 * 1024**3
LOW_DISK_CRITICAL_BYTES = 3 * 1024**3


class SystemReadinessService:
    """Best-effort system detector. Failures are represented as Unknown, never crashes."""

    def __init__(
        self,
        paths: AppPaths,
        settings_provider: Callable[[], AppSettings],
        ffmpeg_locator: FFmpegLocator | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.settings_provider = settings_provider
        self.ffmpeg_locator = ffmpeg_locator or FFmpegLocator()
        self.logger = logger or logging.getLogger("sp_video_studio.readiness")

    def detect(self) -> SystemReadiness:
        result = SystemReadiness()
        self._detect_os_cpu_memory(result)
        self._detect_gpu_cuda(result)
        self._detect_media_tools(result)
        self._detect_models(result)
        self._detect_disks(result)
        self._calculate_overall(result)
        result.last_checked_at = datetime.now(timezone.utc).isoformat()
        return result

    def _detect_os_cpu_memory(self, result: SystemReadiness) -> None:
        try:
            result.os_name = platform.system() or "Unknown"
            result.os_version = platform.release() or platform.version() or "Unknown"
            result.architecture = platform.machine() or platform.architecture()[0] or "Unknown"
            result.cpu_name = platform.processor() or self._cpu_name_fallback() or "Unknown"
        except Exception:
            self.logger.exception("Operating system/CPU identity detection failed")
        try:
            import psutil

            result.cpu_cores_physical = psutil.cpu_count(logical=False)
            result.cpu_cores_logical = psutil.cpu_count(logical=True) or os.cpu_count()
            memory = psutil.virtual_memory()
            result.ram_total = int(memory.total)
            result.ram_available = int(memory.available)
        except Exception:
            self.logger.exception("psutil CPU/RAM detection failed")
            result.cpu_cores_logical = os.cpu_count()
            self._memory_fallback(result)

    def _cpu_name_fallback(self) -> str | None:
        if os.name != "nt":
            return None
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"],
                capture_output=True,
                text=True,
                timeout=3,
                shell=False,
                check=False,
            )
            value = completed.stdout.strip()
            return value or None
        except (OSError, subprocess.SubprocessError):
            return None

    def _memory_fallback(self, result: SystemReadiness) -> None:
        if os.name == "posix" and hasattr(os, "sysconf"):
            try:
                page = os.sysconf("SC_PAGE_SIZE")
                total_pages = os.sysconf("SC_PHYS_PAGES")
                available_pages = os.sysconf("SC_AVPHYS_PAGES")
                result.ram_total = int(page * total_pages)
                result.ram_available = int(page * available_pages)
            except (ValueError, OSError):
                pass

    def _detect_gpu_cuda(self, result: SystemReadiness) -> None:
        nvidia = self._detect_nvidia()
        if nvidia:
            result.gpu_name = nvidia.get("name") or None
            result.gpu_vendor = "NVIDIA"
            result.gpu_status = "ready"
            result.gpu_memory_total = _mib_to_bytes(nvidia.get("memory_total"))
            result.gpu_memory_available = _mib_to_bytes(nvidia.get("memory_free"))
            driver_cuda = nvidia.get("cuda_version")
            result.cuda_version = driver_cuda or None
            result.cuda_status = "possibly_available"
        else:
            generic = self._detect_windows_gpu()
            if generic:
                result.gpu_name = generic[0]
                result.gpu_vendor = _gpu_vendor(generic[0])
                result.gpu_status = "ready"
            else:
                result.gpu_status = "unknown"

        try:
            import torch  # type: ignore

            if bool(torch.cuda.is_available()):
                result.cuda_status = "available"
                result.cuda_version = getattr(getattr(torch, "version", None), "cuda", None) or result.cuda_version
            elif result.gpu_vendor != "NVIDIA":
                result.cuda_status = "unavailable"
        except ImportError:
            # PyTorch is deliberately optional; absence does not prove CUDA is unavailable.
            pass
        except Exception:
            self.logger.exception("PyTorch CUDA capability query failed")

    def _detect_nvidia(self) -> dict[str, str] | None:
        executable = shutil.which("nvidia-smi")
        if not executable:
            return None
        query = "name,memory.total,memory.free,driver_version"
        try:
            completed = subprocess.run(
                [executable, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=4,
                shell=False,
                check=False,
            )
            if completed.returncode != 0 or not completed.stdout.strip():
                return None
            row = next(csv.reader(io.StringIO(completed.stdout.strip())))
            if len(row) < 4:
                return None
            cuda_version = self._nvidia_cuda_version(executable)
            return {
                "name": row[0].strip(),
                "memory_total": row[1].strip(),
                "memory_free": row[2].strip(),
                "driver_version": row[3].strip(),
                "cuda_version": cuda_version or "",
            }
        except (OSError, subprocess.SubprocessError, StopIteration, csv.Error):
            self.logger.info("NVIDIA detection unavailable", exc_info=True)
            return None

    def _nvidia_cuda_version(self, executable: str) -> str | None:
        try:
            completed = subprocess.run(
                [executable], capture_output=True, text=True, timeout=4, shell=False, check=False
            )
            output = completed.stdout or ""
            marker = "CUDA Version:"
            if marker in output:
                return output.split(marker, 1)[1].strip().split()[0]
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    def _detect_windows_gpu(self) -> tuple[str, ...]:
        if os.name != "nt":
            return ()
        try:
            completed = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
                ],
                capture_output=True,
                text=True,
                timeout=4,
                shell=False,
                check=False,
            )
            return tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())
        except (OSError, subprocess.SubprocessError):
            return ()

    def _detect_media_tools(self, result: SystemReadiness) -> None:
        settings = self.settings_provider()
        custom_ffmpeg = settings.ffmpeg_path if settings.ffmpeg_mode == "custom" else None
        custom_ffprobe = settings.ffprobe_path if settings.ffmpeg_mode == "custom" else None
        ffmpeg, ffprobe = self.ffmpeg_locator.discover(custom_ffmpeg, custom_ffprobe)
        result.ffmpeg_available = ffmpeg.available
        result.ffmpeg_path = ffmpeg.path
        result.ffmpeg_version = ffmpeg.version
        result.ffprobe_available = ffprobe.available
        result.ffprobe_path = ffprobe.path
        result.ffprobe_version = ffprobe.version

    def _detect_models(self, result: SystemReadiness) -> None:
        result.voxcpm_status = self._model_status(("voxcpm2", "VoxCPM2"))
        result.whisper_status = self._model_status(("faster-whisper", "whisper"))

    def _model_status(self, candidates: tuple[str, ...]) -> str:
        for name in candidates:
            path = self.paths.models / name
            try:
                if path.is_dir() and any(path.iterdir()):
                    return "installed"
            except OSError:
                continue
        return "not-installed"

    def _detect_disks(self, result: SystemReadiness) -> None:
        settings = self.settings_provider()
        locations = (
            ("Application Data", self.paths.root),
            ("Projects", Path(settings.default_projects_folder)),
            ("Models", self.paths.models),
            ("Temporary", self.paths.temp),
        )
        seen: set[str] = set()
        for name, configured in locations:
            target = _existing_ancestor(configured)
            key = str(target.resolve()) if target else str(configured)
            if key in seen and name != "Projects":
                continue
            seen.add(key)
            result.disks.append(self._disk_readiness(name, configured, target))

    def _disk_readiness(self, name: str, configured: Path, target: Path | None) -> DiskReadiness:
        if target is None:
            return DiskReadiness(name=name, path=str(configured))
        try:
            usage = shutil.disk_usage(target)
            if usage.free < LOW_DISK_CRITICAL_BYTES:
                status = "critical"
            elif usage.free < LOW_DISK_WARNING_BYTES:
                status = "warning"
            else:
                status = "ready"
            return DiskReadiness(
                name=name,
                path=str(configured),
                free_bytes=int(usage.free),
                total_bytes=int(usage.total),
                status=status,
                detail=f"{format_bytes(int(usage.free))} free of {format_bytes(int(usage.total))}",
            )
        except OSError:
            self.logger.info("Disk detection failed for %s", configured, exc_info=True)
            return DiskReadiness(name=name, path=str(configured))

    def _calculate_overall(self, result: SystemReadiness) -> None:
        warnings: list[str] = []
        critical = False
        if not result.ffmpeg_available:
            warnings.append("FFmpeg is missing; media operations require setup.")
            critical = True
        if not result.ffprobe_available:
            warnings.append("FFprobe is missing; media inspection requires setup.")
            critical = True
        if result.gpu_status != "ready":
            warnings.append("GPU detection is unavailable; CPU workflows can still be used.")
        if result.voxcpm_status != "installed":
            warnings.append("VoxCPM2 is not installed.")
        if result.whisper_status != "installed":
            warnings.append("faster-whisper is not installed.")
        if any(item.status in {"warning", "critical"} for item in result.disks):
            warnings.append("One or more storage locations are low on free space.")
        result.warnings = warnings
        if critical:
            result.overall_status = "setup-required"
        elif warnings:
            result.overall_status = "ready-with-warnings"
        else:
            result.overall_status = "ready"


def _existing_ancestor(path: Path) -> Path | None:
    current = Path(path).expanduser()
    while not current.exists() and current != current.parent:
        current = current.parent
    return current if current.exists() else None


def _mib_to_bytes(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(float(value) * 1024**2)
    except ValueError:
        return None


def _gpu_vendor(name: str) -> str:
    lower = name.lower()
    if "nvidia" in lower:
        return "NVIDIA"
    if "amd" in lower or "radeon" in lower:
        return "AMD"
    if "intel" in lower:
        return "Intel"
    return "Unknown"

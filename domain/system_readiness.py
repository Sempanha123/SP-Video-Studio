from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def format_bytes(value: int | None) -> str:
    if value is None:
        return "Unknown"
    size = float(max(0, value))
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit in {"GB", "TB"}:
                return f"{size:.1f} {unit}"
            return f"{size:.0f} {unit}"
        size /= 1024
    return "Unknown"


@dataclass(slots=True)
class DiskReadiness:
    name: str
    path: str
    free_bytes: int | None = None
    total_bytes: int | None = None
    status: str = "unknown"
    detail: str = "Detection unavailable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "freeBytes": self.free_bytes,
            "totalBytes": self.total_bytes,
            "freeDisplay": format_bytes(self.free_bytes),
            "totalDisplay": format_bytes(self.total_bytes),
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(slots=True)
class SystemReadiness:
    os_name: str = "Unknown"
    os_version: str = "Unknown"
    architecture: str = "Unknown"
    cpu_name: str = "Unknown"
    cpu_cores_physical: int | None = None
    cpu_cores_logical: int | None = None
    ram_total: int | None = None
    ram_available: int | None = None
    gpu_name: str | None = None
    gpu_vendor: str | None = None
    gpu_memory_total: int | None = None
    gpu_memory_available: int | None = None
    gpu_status: str = "unknown"
    cuda_status: str = "unknown"
    cuda_version: str | None = None
    ffmpeg_available: bool = False
    ffmpeg_path: str | None = None
    ffmpeg_version: str | None = None
    ffprobe_available: bool = False
    ffprobe_path: str | None = None
    ffprobe_version: str | None = None
    voxcpm_status: str = "not-installed"
    whisper_status: str = "not-installed"
    overall_status: str = "unknown"
    warnings: list[str] = field(default_factory=list)
    disks: list[DiskReadiness] = field(default_factory=list)
    last_checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "os": self.os_name,
            "osVersion": self.os_version,
            "architecture": self.architecture,
            "cpuName": self.cpu_name,
            "cpuPhysicalCores": self.cpu_cores_physical,
            "cpuLogicalCores": self.cpu_cores_logical,
            "ramTotal": self.ram_total,
            "ramAvailable": self.ram_available,
            "ramTotalDisplay": format_bytes(self.ram_total),
            "ramAvailableDisplay": format_bytes(self.ram_available),
            "gpuName": self.gpu_name or "Detection unavailable",
            "gpuVendor": self.gpu_vendor or "Unknown",
            "gpuMemoryTotal": self.gpu_memory_total,
            "gpuMemoryAvailable": self.gpu_memory_available,
            "gpuMemoryTotalDisplay": format_bytes(self.gpu_memory_total),
            "gpuMemoryAvailableDisplay": format_bytes(self.gpu_memory_available),
            "gpuStatus": self.gpu_status,
            "cudaStatus": self.cuda_status,
            "cudaStatusDisplay": self.cuda_status.replace("_", " ").title(),
            "cudaVersion": self.cuda_version or "Unknown",
            "ffmpegAvailable": self.ffmpeg_available,
            "ffmpegPath": self.ffmpeg_path or "",
            "ffmpegVersion": self.ffmpeg_version or "Unknown",
            "ffprobeAvailable": self.ffprobe_available,
            "ffprobePath": self.ffprobe_path or "",
            "ffprobeVersion": self.ffprobe_version or "Unknown",
            "voxcpmStatus": self.voxcpm_status,
            "whisperStatus": self.whisper_status,
            "overallStatus": self.overall_status,
            "overallDisplay": self.overall_status.replace("-", " ").title(),
            "warnings": list(self.warnings),
            "disks": [item.to_dict() for item in self.disks],
            "lastCheckedAt": self.last_checked_at,
        }

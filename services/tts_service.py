from __future__ import annotations

import importlib
import logging
from pathlib import Path

from domain.model_installation import ModelInstallStatus
from domain.settings import PerformanceProfile
from domain.voice_config import TTSDevice
from engines.tts.errors import (
    TTSDependencyMissing,
    TTSInvalidRequest,
    TTSModelNotInstalled,
    TTSUnsupportedDevice,
)
from engines.tts.manager import TTSEngineManager
from engines.tts.types import TTSRequest, TTSResult
from services.ai_resource_manager import AIResourceConflict, AIResourceManager
from services.model_service import ModelService
from services.settings_service import SettingsService
from services.system_readiness_service import SystemReadinessService
from workers.cancellation import CancellationToken


class TTSService:
    ENGINE_ID = "voxcpm2"
    MODEL_ID = "voxcpm2"

    def __init__(
        self,
        manager: TTSEngineManager,
        model_service: ModelService,
        readiness: SystemReadinessService,
        settings: SettingsService,
        logger: logging.Logger | None = None,
    ) -> None:
        self.manager = manager
        self.model_service = model_service
        self.readiness = readiness
        self.settings = settings
        self.logger = logger or logging.getLogger("sp_video_studio.tts")
        self.resource_manager: AIResourceManager | None = None
        self._active_jobs = 0

    @property
    def active_jobs(self) -> int:
        return self._active_jobs

    def set_resource_manager(self, manager: AIResourceManager) -> None:
        self.resource_manager = manager

    def model_path(self) -> Path:
        return self.model_service.install_path(self.model_service.registry.get(self.MODEL_ID))

    def ensure_model_ready(self) -> None:
        installation = self.model_service.repository.get(self.MODEL_ID)
        path = self.model_path()
        if installation is None or installation.status_code != ModelInstallStatus.INSTALLED.value or not path.is_dir():
            if path.exists():
                raise TTSModelNotInstalled("VoxCPM2 needs verification or repair before it can be used.")
            raise TTSModelNotInstalled()

    def resolve_device(self, requested: str) -> str:
        requested = (requested or TTSDevice.AUTO.value).lower()
        if requested not in {item.value for item in TTSDevice} and not requested.startswith("cuda:"):
            raise TTSUnsupportedDevice(f"Unsupported TTS device: {requested}")
        readiness = self.readiness.detect()
        if requested.startswith("cuda"):
            if readiness.cuda_status != "available":
                raise TTSUnsupportedDevice("CUDA is not available in the current PyTorch runtime.")
            return requested
        if requested == TTSDevice.CPU.value:
            return "cpu"
        profile = self.settings.current.performance_profile
        if profile == PerformanceProfile.LOW_MEMORY.value:
            # Prefer the least failure-prone path when memory is constrained.
            if readiness.cuda_status == "available" and (readiness.gpu_memory_available or 0) >= 8 * 1024**3:
                return "cuda"
            return "cpu"
        if readiness.cuda_status == "available":
            return "cuda"
        return "cpu"

    def load(self, device: str = "auto") -> str:
        self.ensure_model_ready()
        resolved = self.resolve_device(device)
        if self.resource_manager is not None:
            try:
                self.resource_manager.prepare("tts", resolved)
            except AIResourceConflict as exc:
                raise TTSUnsupportedDevice(str(exc)) from exc
        engine = self.manager.get(self.ENGINE_ID)
        if not engine.is_available():
            raise TTSDependencyMissing(
                "The official VoxCPM package and PyTorch are required for local narration generation."
            )
        self.model_service.acquire_model(self.MODEL_ID, loaded=True)
        try:
            self.manager.load(self.ENGINE_ID, resolved)
        except Exception:
            self.model_service.release_model(self.MODEL_ID, unload=True)
            raise
        return resolved

    def unload(self) -> None:
        engine = self.manager.get(self.ENGINE_ID)
        if not engine.is_loaded():
            return
        try:
            self.manager.unload(self.ENGINE_ID)
        finally:
            self.model_service.release_model(self.MODEL_ID, unload=True)

    def generate(self, request: TTSRequest, cancellation: CancellationToken | None = None) -> TTSResult:
        self.ensure_model_ready()
        engine = self.manager.get(self.ENGINE_ID)
        engine.validate_request(request)
        resolved = self.resolve_device(request.voice_config.device_code)
        request.voice_config.device = resolved
        if not engine.is_loaded():
            self.load(resolved)
        self.model_service.acquire_model(self.MODEL_ID, loaded=True)
        self._active_jobs += 1
        try:
            return engine.generate(request, cancellation)
        finally:
            self._active_jobs = max(0, self._active_jobs - 1)
            self.model_service.release_model(self.MODEL_ID, unload=False)

    def validate_reference(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_file():
            raise TTSInvalidRequest("This reference recording could not be found.")
        if candidate.suffix.lower() not in {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac"}:
            raise TTSInvalidRequest("This reference recording format is not supported yet.")
        if candidate.stat().st_size <= 0:
            raise TTSInvalidRequest("This reference recording is empty.")
        try:
            sf = importlib.import_module("soundfile")
            info = sf.info(str(candidate))
            duration = float(info.duration)
            if duration < 0.1:
                raise TTSInvalidRequest("This reference recording is too short.")
            if duration > 300:
                raise TTSInvalidRequest("Choose a reference recording shorter than five minutes.")
        except TTSInvalidRequest:
            raise
        except ModuleNotFoundError as exc:
            raise TTSDependencyMissing("Install the optional TTS dependencies to validate reference audio.") from exc
        except Exception as exc:
            raise TTSInvalidRequest("This reference recording could not be decoded.") from exc
        return candidate

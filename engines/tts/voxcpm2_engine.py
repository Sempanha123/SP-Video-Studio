from __future__ import annotations

import gc
import importlib
import importlib.metadata
import logging
from pathlib import Path
from threading import RLock

from engines.tts.base import TTSEngine
from engines.tts.errors import (
    TTSCancelled,
    TTSDependencyMissing,
    TTSGenerationError,
    TTSInvalidRequest,
    TTSModelLoadError,
    TTSOutOfMemory,
    TTSUnsupportedDevice,
)
from engines.tts.types import TTSCapabilities, TTSEngineState, TTSRequest, TTSResult
from workers.cancellation import CancellationToken

VOXCPM_MODEL_ID = "openbmb/VoxCPM2"
VOXCPM_PACKAGE_MIN_VERSION = "2.0.3"
DEFAULT_CFG_VALUE = 2.0
DEFAULT_INFERENCE_TIMESTEPS = 10
CFG_MIN = 0.1
CFG_MAX = 10.0
TIMESTEPS_MIN = 1
TIMESTEPS_MAX = 100
DEFAULT_SAMPLE_RATE = 48_000


class VoxCPM2Engine(TTSEngine):
    """Lazy adapter for the official OpenBMB `voxcpm` package.

    Heavy dependencies are imported only from load()/generate(). The rest of the
    desktop application can run even when torch/VoxCPM is unavailable.
    """

    def __init__(self, model_path: Path, logger: logging.Logger | None = None) -> None:
        self.model_path = Path(model_path)
        self.logger = logger or logging.getLogger("sp_video_studio.tts.voxcpm2")
        self.state = TTSEngineState.UNLOADED
        self.device = "auto"
        self._model = None
        self._torch = None
        self._lock = RLock()
        self._package_version = ""

    @property
    def package_version(self) -> str:
        if self._package_version:
            return self._package_version
        try:
            self._package_version = importlib.metadata.version("voxcpm")
        except importlib.metadata.PackageNotFoundError:
            self._package_version = ""
        return self._package_version

    def is_available(self) -> bool:
        try:
            return importlib.util.find_spec("voxcpm") is not None and importlib.util.find_spec("torch") is not None
        except (ImportError, AttributeError, ValueError):
            return False

    def load(self, device: str = "auto") -> None:
        with self._lock:
            if self.state == TTSEngineState.LOADED:
                return
            if self.state == TTSEngineState.LOADING:
                return
            if not self.model_path.is_dir():
                raise TTSModelLoadError("The managed VoxCPM2 model folder is missing.")
            self.state = TTSEngineState.LOADING
            self.device = self._validate_device(device)
            try:
                torch = importlib.import_module("torch")
                module = importlib.import_module("voxcpm")
                VoxCPM = getattr(module, "VoxCPM")
                if self.device.startswith("cuda") and not bool(torch.cuda.is_available()):
                    raise TTSUnsupportedDevice("CUDA is unavailable in the installed PyTorch runtime.")
                self.logger.info("Loading VoxCPM2 from managed model path on %s", self.device)
                self._model = VoxCPM.from_pretrained(
                    hf_model_id=str(self.model_path),
                    load_denoiser=False,
                    local_files_only=True,
                    device=self.device,
                )
                self._torch = torch
                self._package_version = self.package_version
                self.state = TTSEngineState.LOADED
                self.logger.info("VoxCPM2 loaded")
            except TTSUnsupportedDevice:
                self.state = TTSEngineState.ERROR
                raise
            except (ImportError, ModuleNotFoundError) as exc:
                self.state = TTSEngineState.ERROR
                raise TTSDependencyMissing(
                    "Install the optional TTS dependencies with `pip install -e .[tts]`."
                ) from exc
            except Exception as exc:
                self.state = TTSEngineState.ERROR
                if _is_oom(exc):
                    self._cleanup_cuda()
                    raise TTSOutOfMemory() from exc
                raise TTSModelLoadError(str(exc) or "VoxCPM2 could not be loaded.") from exc

    def unload(self) -> None:
        with self._lock:
            if self.state == TTSEngineState.UNLOADED:
                return
            self.state = TTSEngineState.UNLOADING
            self._model = None
            gc.collect()
            self._cleanup_cuda()
            self.state = TTSEngineState.UNLOADED
            self.logger.info("VoxCPM2 unloaded")

    def is_loaded(self) -> bool:
        return self.state == TTSEngineState.LOADED and self._model is not None

    def get_capabilities(self) -> TTSCapabilities:
        return TTSCapabilities(
            supports_text_to_speech=True,
            supports_voice_design=True,
            supports_reference_voice=True,
            supports_prompt_audio=True,
            supports_seed=True,
            supports_cfg=True,
            supports_inference_steps=True,
            supports_streaming=True,
            supports_cpu=True,
            supports_cuda=True,
            supported_languages=("en", "km", "multilingual"),
            output_sample_rate=DEFAULT_SAMPLE_RATE,
        )

    def validate_request(self, request: TTSRequest) -> None:
        text = request.text.strip()
        if not text:
            raise TTSInvalidRequest("Narration text is required.")
        if len(text) > 20_000:
            raise TTSInvalidRequest("This TTS segment is too long. Split it into smaller sections.")
        config = request.voice_config
        if not (CFG_MIN <= float(config.cfg_value) <= CFG_MAX):
            raise TTSInvalidRequest(f"CFG must be between {CFG_MIN} and {CFG_MAX}.")
        if not (TIMESTEPS_MIN <= int(config.inference_timesteps) <= TIMESTEPS_MAX):
            raise TTSInvalidRequest(
                f"Inference steps must be between {TIMESTEPS_MIN} and {TIMESTEPS_MAX}."
            )
        if config.seed is not None and not isinstance(config.seed, int):
            raise TTSInvalidRequest("Seed must be an integer.")
        mode = config.mode_code
        if mode == "designed" and not config.description.strip():
            raise TTSInvalidRequest("Describe the voice you want to design.")
        if mode == "reference":
            if not config.consent_confirmed:
                raise TTSInvalidRequest("Confirm that you have permission to use the reference voice.")
            if not config.reference_audio_path:
                raise TTSInvalidRequest("Choose a reference recording.")
        if mode == "continuation":
            if not config.consent_confirmed:
                raise TTSInvalidRequest("Confirm that you have permission to use the prompt recording.")
            if not config.prompt_audio_path or not config.prompt_text.strip():
                raise TTSInvalidRequest("Prompt audio and its transcript are required for continuation mode.")
        for value in (config.reference_audio_path, config.prompt_audio_path):
            if value and not Path(value).is_file():
                raise TTSInvalidRequest("The selected voice recording could not be found.")

    def generate(self, request: TTSRequest, cancellation: CancellationToken | None = None) -> TTSResult:
        self.validate_request(request)
        if cancellation and cancellation.is_cancelled:
            raise TTSCancelled()
        with self._lock:
            if not self.is_loaded():
                self.load(request.voice_config.device_code)
            if cancellation and cancellation.is_cancelled:
                raise TTSCancelled()
            output = Path(request.output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            config = request.voice_config
            final_text = request.text.strip()
            if config.mode_code == "designed":
                final_text = f"({config.description.strip()}){final_text}"
            elif config.mode_code == "reference" and config.description.strip():
                final_text = f"({config.description.strip()}){final_text}"

            kwargs = {
                "text": final_text,
                "cfg_value": float(config.cfg_value),
                "inference_timesteps": int(config.inference_timesteps),
                "normalize": bool(config.normalize_text),
                "seed": config.seed,
            }
            if config.mode_code == "reference":
                kwargs["reference_wav_path"] = config.reference_audio_path
            elif config.mode_code == "continuation":
                kwargs["prompt_wav_path"] = config.prompt_audio_path
                kwargs["prompt_text"] = config.prompt_text.strip()
                if config.reference_audio_path:
                    kwargs["reference_wav_path"] = config.reference_audio_path

            try:
                audio = self._model.generate(**kwargs)
                if cancellation and cancellation.is_cancelled:
                    raise TTSCancelled()
                sf = importlib.import_module("soundfile")
                sample_rate = int(getattr(getattr(self._model, "tts_model", None), "sample_rate", DEFAULT_SAMPLE_RATE))
                sf.write(str(output), audio, sample_rate)
                info = sf.info(str(output))
                duration_ms = int(round(float(info.duration) * 1000.0))
                channels = int(info.channels)
                return TTSResult(
                    output_path=output,
                    sample_rate=sample_rate,
                    channels=channels,
                    duration_ms=duration_ms,
                    engine_version=self.package_version,
                    model_version=VOXCPM_MODEL_ID,
                    metadata={"device": self.device},
                )
            except TTSCancelled:
                output.unlink(missing_ok=True)
                raise
            except Exception as exc:
                output.unlink(missing_ok=True)
                if _is_oom(exc):
                    self._cleanup_cuda()
                    raise TTSOutOfMemory() from exc
                raise TTSGenerationError(str(exc) or "VoxCPM2 generation failed.") from exc

    def _cleanup_cuda(self) -> None:
        torch = self._torch
        try:
            if torch is not None and bool(torch.cuda.is_available()):
                torch.cuda.empty_cache()
        except Exception:
            self.logger.debug("CUDA cleanup was unavailable", exc_info=True)

    @staticmethod
    def _validate_device(device: str) -> str:
        value = (device or "auto").strip().lower()
        if value == "cuda":
            return "cuda"
        if value in {"auto", "cpu"} or value.startswith("cuda:"):
            return value
        raise TTSUnsupportedDevice(f"Unsupported TTS device: {device}")


def _is_oom(exc: BaseException) -> bool:
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    return "outofmemory" in name or "out of memory" in text or "cuda oom" in text

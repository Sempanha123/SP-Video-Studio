from __future__ import annotations

import importlib.metadata
import logging
from pathlib import Path
from typing import Any

from engines.translation.base import TranslationEngine
from engines.translation.errors import (
    TranslationCancelled,
    TranslationDependencyMissing,
    TranslationInvalidRequest,
    TranslationModelLoadError,
    TranslationOutOfMemory,
    TranslationProviderError,
    TranslationUnsupportedLanguagePair,
)
from engines.translation.types import TranslationCapabilities, TranslationRequest, TranslationResult
from workers.cancellation import CancellationToken


MODEL_TARGET_PREFIX: dict[tuple[str, str], str] = {
    ("en", "km"): ">>khm<< ",
    ("km", "en"): "",
}


class LocalMarianEngine(TranslationEngine):
    """Lazy Transformers adapter for app-managed Marian/OPUS model folders."""

    ENGINE_ID = "local-marian"

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("sp_video_studio.translation.marian")
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._model_path = ""
        self._model_id = ""
        self._device = "cpu"
        self._version = ""

    def load(self, *, model_path: str = "", model_id: str = "", device: str = "auto") -> None:
        path = Path(model_path).resolve() if model_path else None
        if path is None or not path.is_dir():
            raise TranslationModelLoadError("The local translation model folder is missing.")
        resolved_device = self._resolve_device(device)
        if self.is_loaded() and self._model_path == str(path) and self._device == resolved_device:
            return
        self.unload()
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            import torch
        except Exception as exc:
            raise TranslationDependencyMissing(
                'Install the optional translation runtime with pip install -e ".[translation]".'
            ) from exc
        try:
            tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(str(path), local_files_only=True)
            model.to(resolved_device)
            model.eval()
        except Exception as exc:
            raise TranslationModelLoadError("The local translation model could not be loaded.") from exc
        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self._model_path = str(path)
        self._model_id = model_id
        self._device = resolved_device
        try:
            self._version = importlib.metadata.version("transformers")
        except importlib.metadata.PackageNotFoundError:
            self._version = "unknown"
        self.logger.info("Marian translation model loaded: %s on %s", model_id, resolved_device)

    def unload(self) -> None:
        model = self._model
        self._model = None
        self._tokenizer = None
        self._model_path = ""
        self._model_id = ""
        if model is not None:
            del model
        if self._torch is not None and self._device.startswith("cuda"):
            try:
                self._torch.cuda.empty_cache()
            except Exception:
                pass
        self._torch = None

    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def translate(
        self,
        request: TranslationRequest,
        cancellation: CancellationToken | None = None,
    ) -> TranslationResult:
        self.validate_request(request)
        if not self.is_loaded():
            raise TranslationModelLoadError("The local translation model is not loaded.")
        if cancellation is not None and cancellation.is_cancelled:
            raise TranslationCancelled()
        source_text = MODEL_TARGET_PREFIX.get((request.source_language, request.target_language), "") + request.text
        try:
            encoded = self._tokenizer(source_text, return_tensors="pt", padding=False, truncation=False)
            input_ids = encoded.get("input_ids")
            model_max = int(getattr(self._tokenizer, "model_max_length", 0) or 0)
            if input_ids is not None and model_max and model_max < 100000:
                length = int(input_ids.shape[-1])
                if length > model_max:
                    raise TranslationInvalidRequest(
                        "This translation chunk exceeds the model input limit. Split the source text first."
                    )
            encoded = {key: value.to(self._device) for key, value in encoded.items()}
            kwargs: dict[str, object] = {
                "num_beams": int(request.settings.get("num_beams", 4)),
                "renormalize_logits": True,
            }
            with self._torch.inference_mode():
                generated = self._model.generate(**encoded, **kwargs)
            if cancellation is not None and cancellation.is_cancelled:
                raise TranslationCancelled()
            text = self._tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()
            return TranslationResult(
                text=text,
                model_id=self._model_id,
                provider_version=self._version,
                metadata={"device": self._device},
            )
        except TranslationInvalidRequest:
            raise
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() or "cuda" in str(exc).lower() and "memory" in str(exc).lower():
                if self._torch is not None and self._device.startswith("cuda"):
                    try:
                        self._torch.cuda.empty_cache()
                    except Exception:
                        pass
                raise TranslationOutOfMemory() from exc
            raise TranslationProviderError("The local translation model failed to generate text.") from exc
        except Exception as exc:
            if cancellation is not None and cancellation.is_cancelled:
                raise
            raise TranslationProviderError("The local translation model failed to generate text.") from exc

    def supports_language_pair(self, source: str, target: str) -> bool:
        return (source, target) in self.get_supported_language_pairs()

    def get_supported_language_pairs(self) -> tuple[tuple[str, str], ...]:
        return (("en", "km"), ("km", "en"))

    def get_capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities(
            supports_batch=False,
            supports_context=False,
            supports_glossary=False,
            supports_cpu=True,
            supports_cuda=True,
            supports_offline=True,
        )

    def validate_request(self, request: TranslationRequest) -> None:
        request.validate()
        if not self.supports_language_pair(request.source_language, request.target_language):
            raise TranslationUnsupportedLanguagePair()

    def is_available(self) -> bool:
        try:
            importlib.metadata.version("transformers")
            importlib.metadata.version("torch")
            return True
        except importlib.metadata.PackageNotFoundError:
            return False

    def _resolve_device(self, device: str) -> str:
        requested = (device or "auto").lower()
        if requested not in {"auto", "cpu", "cuda"}:
            raise TranslationInvalidRequest("Device must be Auto, CPU, or CUDA.")
        if requested == "cpu":
            return "cpu"
        try:
            import torch
        except Exception:
            if requested == "cuda":
                raise TranslationDependencyMissing("PyTorch is required for CUDA translation.")
            return "cpu"
        if requested == "cuda":
            if not torch.cuda.is_available():
                raise TranslationInvalidRequest("CUDA is unavailable for the local translation engine.")
            return "cuda"
        # CPU-first policy avoids occupying VRAM for these small models unless the user explicitly chooses CUDA.
        return "cpu"

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class ModelPurpose(StrEnum):
    VOICE = "voice"
    SPEECH_TO_TEXT = "speech-to-text"
    TRANSLATION = "translation"


class ModelCompatibility(StrEnum):
    COMPATIBLE = "compatible"
    COMPATIBLE_WITH_WARNING = "compatible_with_warning"
    NOT_RECOMMENDED = "not_recommended"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AIModel:
    model_id: str
    family: str
    name: str
    description: str
    purpose: str | ModelPurpose
    version: str
    source: str
    source_identifier: str
    license: str
    download_size_bytes: int
    disk_size_bytes: int
    supported_languages: tuple[str, ...] = ()
    supports_cpu: bool = True
    supports_cuda: bool = True
    minimum_ram_bytes: int | None = None
    recommended_ram_bytes: int | None = None
    minimum_vram_bytes: int | None = None
    recommended_vram_bytes: int | None = None
    required_dependencies: tuple[str, ...] = ()
    install_strategy: str = "huggingface_snapshot"
    required_files: tuple[str, ...] = ()
    install_relative_path: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("Model ID is required.")
        if not self.source_identifier.strip():
            raise ValueError("Model source identifier is required.")
        if self.download_size_bytes < 0 or self.disk_size_bytes < 0:
            raise ValueError("Model sizes cannot be negative.")
        relative = self.install_relative_path.replace("\\", "/").strip("/")
        if not relative or relative.startswith(".") or ".." in relative.split("/"):
            raise ValueError("Model install path must be a safe relative path.")

    @property
    def purpose_code(self) -> str:
        return str(self.purpose)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.model_id,
            "family": self.family,
            "name": self.name,
            "description": self.description,
            "purpose": self.purpose_code,
            "version": self.version,
            "source": self.source,
            "sourceIdentifier": self.source_identifier,
            "license": self.license,
            "downloadSizeBytes": self.download_size_bytes,
            "diskSizeBytes": self.disk_size_bytes,
            "supportedLanguages": list(self.supported_languages),
            "supportsCpu": self.supports_cpu,
            "supportsCuda": self.supports_cuda,
            "minimumRamBytes": self.minimum_ram_bytes,
            "recommendedRamBytes": self.recommended_ram_bytes,
            "minimumVramBytes": self.minimum_vram_bytes,
            "recommendedVramBytes": self.recommended_vram_bytes,
            "requiredDependencies": list(self.required_dependencies),
            "installStrategy": self.install_strategy,
            "requiredFiles": list(self.required_files),
            "installRelativePath": self.install_relative_path,
            "metadata": dict(self.metadata),
        }

from __future__ import annotations

from collections.abc import Iterable

from domain.ai_model import AIModel, ModelPurpose

GIB = 1024**3
MIB = 1024**2


class ModelRegistry:
    """Static model catalog. Runtime installation state lives elsewhere."""

    def __init__(self, models: Iterable[AIModel] | None = None) -> None:
        catalog = tuple(models) if models is not None else _default_models()
        ids = [item.model_id for item in catalog]
        if len(ids) != len(set(ids)):
            raise ValueError("Model registry contains duplicate IDs.")
        self._models = {item.model_id: item for item in catalog}

    def get(self, model_id: str) -> AIModel:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown AI model: {model_id}") from exc

    def list_all(self) -> tuple[AIModel, ...]:
        return tuple(self._models.values())

    def list_family(self, family: str) -> tuple[AIModel, ...]:
        return tuple(item for item in self._models.values() if item.family == family)

    def contains(self, model_id: str) -> bool:
        return model_id in self._models


def _default_models() -> tuple[AIModel, ...]:
    # Source identifiers, licenses, approximate repository sizes and required files
    # were verified against the public model repositories on 2026-09-11.
    return (
        AIModel(
            model_id="voxcpm2",
            family="voxcpm2",
            name="VoxCPM2",
            description="Multilingual local text-to-speech model with voice design and reference-voice capabilities.",
            purpose=ModelPurpose.VOICE,
            version="2",
            source="huggingface",
            source_identifier="openbmb/VoxCPM2",
            license="Apache-2.0",
            download_size_bytes=4_960_000_000,
            disk_size_bytes=5_200_000_000,
            supported_languages=("Multilingual", "English", "Khmer"),
            supports_cpu=True,
            supports_cuda=True,
            minimum_ram_bytes=16 * GIB,
            recommended_ram_bytes=24 * GIB,
            minimum_vram_bytes=8 * GIB,
            recommended_vram_bytes=8 * GIB,
            required_dependencies=("voxcpm >= 2.0.3", "PyTorch >= 2.5"),
            required_files=("config.json", "model.safetensors", "audiovae.pth", "tokenizer.json"),
            install_relative_path="voxcpm2/default",
            metadata={
                "qualityLabel": "Recommended VoxCPM2",
                "sourceVerifiedDate": "2026-09-11",
                "officialModelParameters": "2B",
                "officialVramGuidance": "~8 GB",
            },
        ),
        AIModel(
            model_id="whisper-small",
            family="faster-whisper",
            name="Whisper Small",
            description="Lower-resource multilingual speech recognition for faster local transcription.",
            purpose=ModelPurpose.SPEECH_TO_TEXT,
            version="small",
            source="huggingface",
            source_identifier="Systran/faster-whisper-small",
            license="MIT",
            download_size_bytes=486_000_000,
            disk_size_bytes=520_000_000,
            supported_languages=("Multilingual", "English", "Khmer"),
            supports_cpu=True,
            supports_cuda=True,
            minimum_ram_bytes=4 * GIB,
            recommended_ram_bytes=8 * GIB,
            minimum_vram_bytes=None,
            recommended_vram_bytes=2 * GIB,
            required_dependencies=("faster-whisper", "CTranslate2"),
            required_files=("config.json", "model.bin", "tokenizer.json"),
            install_relative_path="whisper/small",
            metadata={"qualityLabel": "Lower hardware requirements", "sourceVerifiedDate": "2026-09-11"},
        ),
        AIModel(
            model_id="whisper-medium",
            family="faster-whisper",
            name="Whisper Medium",
            description="Balanced multilingual speech recognition with stronger accuracy and moderate resource use.",
            purpose=ModelPurpose.SPEECH_TO_TEXT,
            version="medium",
            source="huggingface",
            source_identifier="Systran/faster-whisper-medium",
            license="MIT",
            download_size_bytes=1_530_000_000,
            disk_size_bytes=1_620_000_000,
            supported_languages=("Multilingual", "English", "Khmer"),
            supports_cpu=True,
            supports_cuda=True,
            minimum_ram_bytes=8 * GIB,
            recommended_ram_bytes=12 * GIB,
            minimum_vram_bytes=None,
            recommended_vram_bytes=4 * GIB,
            required_dependencies=("faster-whisper", "CTranslate2"),
            required_files=("config.json", "model.bin", "tokenizer.json"),
            install_relative_path="whisper/medium",
            metadata={"qualityLabel": "Balanced", "sourceVerifiedDate": "2026-09-11"},
        ),
        AIModel(
            model_id="whisper-large-v3",
            family="faster-whisper",
            name="Whisper Large V3",
            description="Heavier multilingual speech recognition for the highest-quality local Whisper option.",
            purpose=ModelPurpose.SPEECH_TO_TEXT,
            version="large-v3",
            source="huggingface",
            source_identifier="Systran/faster-whisper-large-v3",
            license="MIT",
            download_size_bytes=3_090_000_000,
            disk_size_bytes=3_250_000_000,
            supported_languages=("Multilingual", "English", "Khmer"),
            supports_cpu=True,
            supports_cuda=True,
            minimum_ram_bytes=12 * GIB,
            recommended_ram_bytes=16 * GIB,
            minimum_vram_bytes=None,
            recommended_vram_bytes=6 * GIB,
            required_dependencies=("faster-whisper", "CTranslate2"),
            required_files=("config.json", "model.bin", "tokenizer.json", "preprocessor_config.json"),
            install_relative_path="whisper/large-v3",
            metadata={"qualityLabel": "Highest recognition quality", "sourceVerifiedDate": "2026-09-11"},
        ),
    )

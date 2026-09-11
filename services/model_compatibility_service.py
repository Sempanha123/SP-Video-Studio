from __future__ import annotations

from dataclasses import dataclass

from domain.ai_model import AIModel, ModelCompatibility
from domain.system_readiness import SystemReadiness


@dataclass(frozen=True, slots=True)
class CompatibilityAssessment:
    status: ModelCompatibility
    summary: str
    warnings: tuple[str, ...] = ()


class ModelCompatibilityService:
    def assess(self, model: AIModel, readiness: SystemReadiness | None) -> CompatibilityAssessment:
        if readiness is None:
            return CompatibilityAssessment(ModelCompatibility.UNKNOWN, "Hardware compatibility not checked yet.")
        warnings: list[str] = []
        hard_limit = False
        if readiness.ram_total is not None and model.minimum_ram_bytes is not None:
            if readiness.ram_total < model.minimum_ram_bytes:
                warnings.append("System RAM is below this model's estimated minimum guidance.")
                hard_limit = True
            elif model.recommended_ram_bytes and readiness.ram_total < model.recommended_ram_bytes:
                warnings.append("More RAM is recommended for smoother use.")
        if model.supports_cuda:
            if readiness.cuda_status == "available":
                if (
                    model.minimum_vram_bytes is not None
                    and readiness.gpu_memory_total is not None
                    and readiness.gpu_memory_total < model.minimum_vram_bytes
                ):
                    warnings.append("Detected GPU VRAM is below this model's estimated minimum guidance.")
                    hard_limit = True
                elif (
                    model.recommended_vram_bytes is not None
                    and readiness.gpu_memory_total is not None
                    and readiness.gpu_memory_total < model.recommended_vram_bytes
                ):
                    warnings.append("More GPU VRAM is recommended.")
            elif model.supports_cpu:
                warnings.append("CUDA is not confirmed; CPU execution may be slower.")
            else:
                warnings.append("This model currently expects a CUDA-capable environment.")
                hard_limit = True
        if hard_limit:
            return CompatibilityAssessment(ModelCompatibility.NOT_RECOMMENDED, "Not recommended on detected hardware.", tuple(warnings))
        if warnings:
            return CompatibilityAssessment(ModelCompatibility.COMPATIBLE_WITH_WARNING, "Compatible with limitations.", tuple(warnings))
        return CompatibilityAssessment(ModelCompatibility.COMPATIBLE, "Compatible with detected hardware.")

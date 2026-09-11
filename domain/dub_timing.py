from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DubTimingAnalysis:
    target_duration_ms: int
    generated_duration_ms: int
    difference_ms: int
    duration_ratio: float
    required_tempo: float
    status: str
    safe_to_fit: bool
    strong_stretch_required: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "targetDurationMs": self.target_duration_ms,
            "generatedDurationMs": self.generated_duration_ms,
            "differenceMs": self.difference_ms,
            "durationRatio": self.duration_ratio,
            "requiredTempo": self.required_tempo,
            "status": self.status,
            "safeToFit": self.safe_to_fit,
            "strongStretchRequired": self.strong_stretch_required,
        }

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping

ONBOARDING_VERSION = 1
ONBOARDING_STEPS = (
    "welcome",
    "language_appearance",
    "workspace",
    "readiness",
    "ai",
    "first_project",
    "complete",
)


class OnboardingStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class OnboardingState:
    status: str = OnboardingStatus.NOT_STARTED.value
    onboarding_version: int = ONBOARDING_VERSION
    current_step: int = 0
    default_project_language: str = "en"
    continue_without_ai: bool = False
    first_project_id: str = ""
    migrated_existing_user: bool = False
    dismissed_tips: list[str] = field(default_factory=list)
    updated_at: str = ""

    @property
    def step_id(self) -> str:
        return ONBOARDING_STEPS[max(0, min(self.current_step, len(ONBOARDING_STEPS) - 1))]

    def validate(self) -> None:
        if self.status not in {item.value for item in OnboardingStatus}:
            raise ValueError("Unsupported onboarding state.")
        if int(self.onboarding_version) < 1:
            raise ValueError("Unsupported onboarding version.")
        if not 0 <= int(self.current_step) < len(ONBOARDING_STEPS):
            raise ValueError("Invalid onboarding step.")
        if not str(self.default_project_language).strip():
            raise ValueError("Default project language is required.")
        self.dismissed_tips = sorted({str(x) for x in self.dismissed_tips if str(x).strip()})

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["step_id"] = self.step_id
        return result

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OnboardingState":
        state = cls(
            status=str(payload.get("status", OnboardingStatus.NOT_STARTED.value)),
            onboarding_version=int(payload.get("onboarding_version", ONBOARDING_VERSION) or ONBOARDING_VERSION),
            current_step=int(payload.get("current_step", 0) or 0),
            default_project_language=str(payload.get("default_project_language", "en") or "en"),
            continue_without_ai=bool(payload.get("continue_without_ai", False)),
            first_project_id=str(payload.get("first_project_id", "") or ""),
            migrated_existing_user=bool(payload.get("migrated_existing_user", False)),
            dismissed_tips=list(payload.get("dismissed_tips") or []),
            updated_at=str(payload.get("updated_at", "") or ""),
        )
        state.validate()
        return state

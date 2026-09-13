from __future__ import annotations

from pathlib import Path

from domain.onboarding import ONBOARDING_VERSION, OnboardingState, OnboardingStatus


class FirstRunService:
    """Determines whether setup should be shown without forcing existing configured users through it."""

    def __init__(self, settings_service, project_service, default_projects_root: Path) -> None:
        self.settings = settings_service
        self.projects = project_service
        self.default_projects_root = Path(default_projects_root).expanduser()

    def initial_state(self) -> OnboardingState:
        if self.is_existing_configured_installation():
            return OnboardingState(
                status=OnboardingStatus.COMPLETED.value,
                onboarding_version=ONBOARDING_VERSION,
                current_step=6,
                default_project_language=self._existing_content_language(),
                migrated_existing_user=True,
            )
        return OnboardingState(
            status=OnboardingStatus.NOT_STARTED.value,
            onboarding_version=ONBOARDING_VERSION,
            current_step=0,
            default_project_language=self._existing_content_language(),
        )

    def is_existing_configured_installation(self) -> bool:
        try:
            if list(self.projects.list_projects()):
                return True
        except Exception:
            try:
                if list(self.projects.repository.list_all()):
                    return True
            except Exception:
                pass
        s = self.settings.current
        default_root = str(self.default_projects_root.resolve(strict=False))
        configured_root = str(Path(s.default_projects_folder).expanduser().resolve(strict=False))
        return any(
            (
                s.theme != "system",
                configured_root != default_root,
                s.performance_profile != "auto",
                bool(s.ffmpeg_path),
                bool(s.shortcut_overrides),
                s.reduce_motion != "system",
                s.interface_text_size != "default",
                s.stronger_focus_indicator,
            )
        )

    def _existing_content_language(self) -> str:
        # Existing Settings.language is an application-UI preference and is only a safe
        # seed when it is a real content language. Phase 35 stores content default separately.
        value = str(getattr(self.settings.current, "language", "en") or "en")
        return value if value in {"en", "km"} else "en"

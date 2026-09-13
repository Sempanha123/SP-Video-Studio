from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.onboarding import ONBOARDING_VERSION, OnboardingStatus
from services.first_run_service import FirstRunService
from services.onboarding_service import OnboardingService


@dataclass
class FakeSettings:
    language: str = "en"
    theme: str = "system"
    default_projects_folder: str = ""
    performance_profile: str = "auto"
    ffmpeg_path: str = ""
    shortcut_overrides: dict[str, str] = field(default_factory=dict)
    reduce_motion: str = "system"
    interface_text_size: str = "default"
    stronger_focus_indicator: bool = False

    def with_changes(self, **changes):
        for key, value in changes.items():
            setattr(self, key, value)
        return self


class FakeSettingsService:
    def __init__(self, root: Path):
        self.paths = SimpleNamespace(default_projects_root=root, settings=root.parent / "settings")
        self.current = FakeSettings(default_projects_folder=str(root))
        self.updates = []

    def update(self, **changes):
        self.updates.append(dict(changes))
        self.current.with_changes(**changes)
        return self.current

    def validate_directory(self, path, create=False):
        target = Path(path)
        if target.name == "invalid":
            raise ValueError("This folder cannot be used for projects.")
        if create:
            target.mkdir(parents=True, exist_ok=True)
        if not target.is_dir():
            raise ValueError("This folder cannot be used for projects.")
        return target.resolve()

    def set_project_folder(self, path):
        target = self.validate_directory(path, create=True)
        self.current.default_projects_folder = str(target)
        return self.current


class FakeProjectService:
    def __init__(self, projects=None):
        self._projects = list(projects or [])
        self.root_changes = []
        self.repository = SimpleNamespace(list_all=lambda: list(self._projects))

    def list_projects(self): return list(self._projects)
    def set_project_root(self, path): self.root_changes.append(Path(path))


class FakeLanguageService:
    rows = [
        {"code": "en", "displayName": "English", "nativeName": "English", "details": {"overall": "supported"}},
        {"code": "km", "displayName": "Khmer", "nativeName": "ខ្មែរ", "details": {"overall": "partially_supported"}},
        {"code": "th", "displayName": "Thai", "nativeName": "ไทย", "details": {"overall": "partially_supported"}},
        {"code": "vi", "displayName": "Vietnamese", "nativeName": "Tiếng Việt", "details": {"overall": "partially_supported"}},
    ]
    def get(self, code):
        if code not in {x["code"] for x in self.rows}: raise ValueError("Unsupported language")
        return code
    def list_languages(self, query=""): return list(self.rows)


class FakeReadiness:
    def __init__(self, *, ffmpeg=True, gpu=False, voxcpm="not-installed", whisper="not-installed"):
        self.ffmpeg=ffmpeg; self.gpu=gpu; self.voxcpm=voxcpm; self.whisper=whisper; self.calls=0
    def detect(self):
        self.calls += 1
        return SimpleNamespace(to_dict=lambda: {
            "overallStatus": "ready" if self.ffmpeg else "setup-required",
            "overallDisplay": "Ready" if self.ffmpeg else "Setup Required",
            "ffmpegAvailable": self.ffmpeg,
            "gpuStatus": "ready" if self.gpu else "unknown",
            "cpuName": "Test CPU", "cpuLogicalCores": 8,
            "voxcpmStatus": self.voxcpm, "whisperStatus": self.whisper,
            "disks": [{"name":"Projects","detail":"100 GB free"}], "warnings": [],
        })


class FakeModelService:
    def __init__(self): self.refresh_calls=0; self.install_calls=0
    def refresh(self):
        self.refresh_calls += 1
        return [{"id":"voxcpm2","name":"VoxCPM2","installed":False,"compatibility":"supported"}]
    def install(self, *a, **k): self.install_calls += 1


class FakePerformance:
    def __init__(self): self.values=[]
    def set_profile(self, value): self.values.append(value)


class FakeDiskMonitor:
    def check(self, path, label=""):
        return SimpleNamespace(free_bytes=50*1024**3, state=SimpleNamespace(value="normal"))


def make_service(tmp_path: Path, *, projects=None, readiness=None, models=None):
    project_root = tmp_path / "Projects"
    settings = FakeSettingsService(project_root)
    paths = SimpleNamespace(settings=tmp_path / "settings", default_projects_root=project_root)
    project_service = FakeProjectService(projects)
    return OnboardingService(
        paths, settings, project_service, FakeLanguageService(), readiness or FakeReadiness(),
        model_service=models, performance_service=FakePerformance(), disk_monitor=FakeDiskMonitor(),
    )


def test_fresh_install_is_explicit_not_started(tmp_path):
    svc=make_service(tmp_path)
    assert svc.state.status == OnboardingStatus.NOT_STARTED.value
    assert svc.state.onboarding_version == ONBOARDING_VERSION
    assert svc.should_show is True


def test_existing_user_is_migrated_without_forced_wizard(tmp_path):
    svc=make_service(tmp_path, projects=[SimpleNamespace(id="existing")])
    assert svc.state.status == OnboardingStatus.COMPLETED.value
    assert svc.state.migrated_existing_user is True
    assert svc.should_show is False


def test_existing_customized_settings_are_not_forced(tmp_path):
    root=tmp_path/"Projects"; settings=FakeSettingsService(root); settings.current.theme="dark"
    first=FirstRunService(settings, FakeProjectService(), root)
    assert first.is_existing_configured_installation() is True
    assert first.initial_state().status == "completed"


def test_resume_incomplete_onboarding_after_restart(tmp_path):
    svc=make_service(tmp_path); svc.begin(); svc.set_step(3); svc.set_content_language("km")
    svc2=make_service(tmp_path)
    assert svc2.state.status == "in_progress"
    assert svc2.state.current_step == 3
    assert svc2.state.default_project_language == "km"


def test_skip_keeps_getting_started_state_available(tmp_path):
    svc=make_service(tmp_path); svc.skip()
    assert svc.state.status == "skipped" and not svc.should_show
    svc.reopen()
    assert svc.state.status == "in_progress" and svc.state.current_step == 0


@pytest.mark.parametrize("code", ["en","km","th","vi"])
def test_language_registry_selection_persists(tmp_path, code):
    svc=make_service(tmp_path); svc.set_content_language(code)
    assert make_service(tmp_path).state.default_project_language == code


def test_theme_accessibility_and_performance_use_existing_settings(tmp_path):
    svc=make_service(tmp_path)
    svc.set_theme("dark"); svc.set_reduce_motion(True); svc.set_large_text(True); svc.set_performance_profile("balanced")
    s=svc.settings.current
    assert (s.theme,s.reduce_motion,s.interface_text_size,s.performance_profile)==("dark","on","large","balanced")
    assert svc.performance.values == ["balanced"]


def test_project_folder_validation_uses_central_disk_monitor(tmp_path):
    svc=make_service(tmp_path)
    folder=tmp_path/"Projects2"; result=svc.set_project_folder(folder)
    assert result["valid"] is True and result["diskState"] == "normal" and result["freeGb"] == 50.0
    assert svc.projects.root_changes[-1] == folder.resolve()


def test_invalid_project_folder_is_actionable(tmp_path):
    svc=make_service(tmp_path)
    result=svc.validate_project_folder(tmp_path/"invalid")
    assert result["valid"] is False
    assert "cannot be used" in result["message"].lower()


def test_ffmpeg_missing_does_not_block_editor(tmp_path):
    svc=make_service(tmp_path, readiness=FakeReadiness(ffmpeg=False))
    data=svc.readiness_snapshot()
    assert data["ffmpegAvailable"] is False
    assert "still enter the editor" in data["renderingMessage"]


def test_cpu_only_mode_is_not_failure(tmp_path):
    svc=make_service(tmp_path, readiness=FakeReadiness(gpu=False))
    assert "CPU mode available" in svc.readiness_snapshot()["cpuModeMessage"]


def test_gpu_available_mode_is_reported(tmp_path):
    svc=make_service(tmp_path, readiness=FakeReadiness(gpu=True))
    assert svc.readiness_snapshot()["cpuModeMessage"] == "GPU acceleration available."


def test_models_are_not_discovered_or_downloaded_on_service_start(tmp_path):
    models=FakeModelService(); svc=make_service(tmp_path, models=models)
    assert models.refresh_calls == 0 and models.install_calls == 0
    rows=svc.model_snapshot()
    assert models.refresh_calls == 1 and models.install_calls == 0
    assert rows[0]["onboardingStatus"] == "Model Required"


def test_continue_without_ai_persists(tmp_path):
    svc=make_service(tmp_path); svc.mark_continue_without_ai()
    assert make_service(tmp_path).state.continue_without_ai is True


def test_complete_and_first_project_persist(tmp_path):
    svc=make_service(tmp_path); svc.record_first_project("p1"); svc.complete("p1")
    state=make_service(tmp_path).state
    assert state.status == "completed" and state.first_project_id == "p1"


def test_run_setup_again_does_not_touch_projects_or_models(tmp_path):
    models=FakeModelService(); project=SimpleNamespace(id="keep")
    svc=make_service(tmp_path, projects=[project], models=models)
    before=list(svc.projects.list_projects()); svc.reopen(); after=list(svc.projects.list_projects())
    assert before == after and models.install_calls == 0


def test_dismissed_contextual_tip_persists(tmp_path):
    svc=make_service(tmp_path); assert svc.should_show_tip("home_asset_tip")
    svc.dismiss_tip("home_asset_tip")
    assert not make_service(tmp_path).should_show_tip("home_asset_tip")


def test_quick_setup_summary_is_plain_and_optional(tmp_path):
    svc=make_service(tmp_path, readiness=FakeReadiness(ffmpeg=False))
    summary=svc.summary()
    assert summary["ffmpeg"] == "Needs Setup"
    assert summary["voiceAI"] == "Not installed"


def test_qml_contracts_and_no_auto_download():
    root=Path(__file__).resolve().parents[1]
    main=(root/"ui/qml/Main.qml").read_text(encoding="utf-8")
    wizard=(root/"ui/qml/onboarding/SetupWizard.qml").read_text(encoding="utf-8")
    models=(root/"ui/qml/onboarding/ModelSetup.qml").read_text(encoding="utf-8")
    first=(root/"ui/qml/onboarding/FirstProjectSetup.qml").read_text(encoding="utf-8")
    runtime=(root/"app/phase35_runtime.py").read_text(encoding="utf-8")
    assert "SPVideoStudio.Onboarding 1.0" in main and "if(Onboarding.shouldShow) setupWizard.open()" in main
    assert "Skip Setup" in wizard and "Close setup and resume later" in wizard
    assert "Continue Without AI" in models and "Install / Manage" in models
    assert "Onboarding.openModels()" in models and ".install(" not in runtime
    assert all(x in first for x in ["Blank Video","News","Story","Translate & Dub","Shorts","Start from Template"])


def test_accessibility_high_dpi_and_multilingual_contracts():
    root=Path(__file__).resolve().parents[1]
    wizard=(root/"ui/qml/onboarding/SetupWizard.qml").read_text(encoding="utf-8")
    lang=(root/"ui/qml/onboarding/LanguageSetup.qml").read_text(encoding="utf-8")
    main=(root/"ui/qml/Main.qml").read_text(encoding="utf-8")
    assert "width: Math.min(920" in wizard and "height: Math.min(720" in wizard
    assert "focus: true" in wizard and "ScrollView" in wizard
    assert "ខ្មែរ" not in lang or "សួស្តី" in lang
    assert "สวัสดี" in lang and "Xin chào" in lang
    assert "minimumWidth: 1080" in main and "minimumHeight: 700" in main


def test_help_and_template_handoff_are_reopenable():
    root=Path(__file__).resolve().parents[1]
    main=(root/"ui/qml/Main.qml").read_text(encoding="utf-8")
    home=(root/"ui/qml/pages/HomePage.qml").read_text(encoding="utf-8")
    guide=(root/"ui/qml/onboarding/QuickGuide.qml").read_text(encoding="utf-8")
    assert "Getting Started" in main and "Quick Guide" in main
    assert "Onboarding.runAgain()" in main
    assert "Start from Template" in home and 'navigateRequested("templates"' in home
    for text in ["Create a project","Import media","Add voice","Add subtitles","Use Timeline","Export video"]:
        assert text in guide


def test_entrypoint_is_phase35():
    root=Path(__file__).resolve().parents[1]
    assert "app.phase35_runtime" in (root/"main.py").read_text(encoding="utf-8")
    assert 'sp-video-studio = "app.phase35_runtime:run"' in (root/"pyproject.toml").read_text(encoding="utf-8")


def test_fresh_install_acceptance_sequence(tmp_path):
    models=FakeModelService(); readiness=FakeReadiness(ffmpeg=True,gpu=False)
    svc=make_service(tmp_path, readiness=readiness, models=models)
    svc.begin()
    svc.set_content_language("km")
    svc.set_theme("dark")
    target=tmp_path/"Creator Projects"
    assert svc.set_project_folder(target)["valid"]
    assert svc.readiness_snapshot()["ffmpegAvailable"] is True
    svc.mark_continue_without_ai()
    svc.record_first_project("blank-video-1")
    svc.complete("blank-video-1")
    state=make_service(tmp_path).state
    assert state.status == "completed"
    assert state.default_project_language == "km"
    assert state.first_project_id == "blank-video-1"
    assert models.install_calls == 0
    assert svc.settings.current.theme == "dark"
    assert Path(svc.settings.current.default_projects_folder) == target.resolve()


def test_no_internet_or_model_discovery_failure_still_allows_manual_setup(tmp_path):
    class OfflineModels:
        def refresh(self): raise OSError("offline")
        def install(self,*a,**k): raise AssertionError("must not auto install")
    svc=make_service(tmp_path, models=OfflineModels())
    assert svc.model_snapshot() == []
    svc.mark_continue_without_ai(); svc.complete()
    assert svc.state.status == "completed"


def test_startup_does_not_run_readiness_or_model_discovery(tmp_path):
    readiness=FakeReadiness(); models=FakeModelService()
    svc=make_service(tmp_path, readiness=readiness, models=models)
    assert readiness.calls == 0
    assert models.refresh_calls == 0
    assert svc.should_show

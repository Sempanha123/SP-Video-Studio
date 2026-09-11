from pathlib import Path

from app.paths import AppPaths
from domain.settings import AppSettings, PerformanceProfile, SETTINGS_VERSION, ThemeMode
from services.settings_service import InvalidSettingsPathError, SettingsService
from storage.repositories.settings_repository import SettingsRepository


def make_paths(tmp_path: Path) -> AppPaths:
    root = tmp_path / "app"
    paths = AppPaths(
        root=root,
        models=root / "models",
        cache=root / "cache",
        temp=root / "temp",
        logs=root / "logs",
        settings=root / "settings",
        downloads=root / "downloads",
    )
    paths.ensure()
    return paths


def make_service(tmp_path: Path) -> tuple[SettingsService, AppPaths, SettingsRepository]:
    paths = make_paths(tmp_path)
    repository = SettingsRepository(paths.settings / "settings.json")
    return SettingsService(repository, paths), paths, repository


def test_settings_defaults_are_versioned(tmp_path: Path):
    service, _, repository = make_service(tmp_path)
    assert service.current.settings_version == SETTINGS_VERSION
    assert service.current.theme == ThemeMode.SYSTEM.value
    assert service.current.performance_profile == PerformanceProfile.AUTO.value
    assert service.current.language == "en"
    assert service.current.readiness_check_on_startup is True
    assert repository.exists()


def test_settings_persist_across_service_restart(tmp_path: Path):
    service, paths, repository = make_service(tmp_path)
    project_root = tmp_path / "custom-projects"
    service.update(theme="dark", performance_profile="balanced", language="km")
    service.set_project_folder(project_root)

    restarted = SettingsService(repository, paths)
    assert restarted.current.theme == "dark"
    assert restarted.current.performance_profile == "balanced"
    assert restarted.current.language == "km"
    assert Path(restarted.current.default_projects_folder) == project_root.resolve()


def test_theme_persistence(tmp_path: Path):
    service, paths, repository = make_service(tmp_path)
    service.update(theme="light")
    assert SettingsService(repository, paths).current.theme == "light"


def test_performance_profile_persistence(tmp_path: Path):
    service, paths, repository = make_service(tmp_path)
    service.update(performance_profile="maximum_quality")
    assert SettingsService(repository, paths).current.performance_profile == "maximum_quality"


def test_settings_reset_does_not_remove_application_data(tmp_path: Path):
    service, paths, _ = make_service(tmp_path)
    project_database = paths.data / "app.db"
    model_marker = paths.models / "keep-model.bin"
    project_database.write_text("database", encoding="utf-8")
    model_marker.write_text("model", encoding="utf-8")
    service.update(theme="dark", language="km", debug_logging=True)

    reset = service.reset_defaults()

    assert reset.theme == "system"
    assert reset.language == "en"
    assert reset.debug_logging is False
    assert project_database.read_text(encoding="utf-8") == "database"
    assert model_marker.read_text(encoding="utf-8") == "model"


def test_invalid_settings_are_quarantined_and_defaults_restored(tmp_path: Path):
    paths = make_paths(tmp_path)
    repository = SettingsRepository(paths.settings / "settings.json")
    repository.settings_file.write_text('{"settings_version": 999}', encoding="utf-8")

    service = SettingsService(repository, paths)

    assert service.current.settings_version == SETTINGS_VERSION
    assert list(paths.settings.glob("settings.json.invalid*"))


def test_custom_project_path_must_be_directory(tmp_path: Path):
    service, _, _ = make_service(tmp_path)
    file_path = tmp_path / "not-a-folder"
    file_path.write_text("x", encoding="utf-8")
    try:
        service.set_project_folder(file_path)
    except InvalidSettingsPathError:
        pass
    else:
        raise AssertionError("file path must be rejected as a project folder")


def test_settings_serialization_round_trip(tmp_path: Path):
    defaults = AppSettings.defaults(tmp_path / "projects")
    defaults.theme = "dark"
    defaults.default_fps = 60
    restored = AppSettings.from_dict(defaults.to_dict(), tmp_path / "fallback")
    assert restored.theme == "dark"
    assert restored.default_fps == 60
    assert restored.settings_version == SETTINGS_VERSION

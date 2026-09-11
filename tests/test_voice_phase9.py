from __future__ import annotations

import wave
from pathlib import Path

import pytest

from engines.voice_registry import VoiceRegistry
from services.project_service import ProjectService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from services.voice_service import VoiceInUseError, VoiceService, VoiceServiceError
from storage.database import SQLiteDatabase
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.voice_repository import VoiceRepository


def make_wav(path: Path, milliseconds: int = 300) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 16000
    frames = int(rate * milliseconds / 1000)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(b"\x00\x00" * frames)
    return path


@pytest.fixture
def voice_system(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "data" / "app.db")
    db.initialize()
    projects = ProjectRepository(db)
    project_service = ProjectService(projects, tmp_path / "projects")
    scripts = ScriptRepository(db)
    script_service = ScriptService(scripts, projects, ScriptAnalysisService())
    project_service.set_script_service(script_service)
    voices = VoiceRepository(db)
    service = VoiceService(VoiceRegistry(), voices, tmp_path / "runtime" / "voices")
    project_service.set_voice_service(service)
    return db, projects, project_service, script_service, voices, service


def test_phase9_database_migration(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db")
    db.initialize()
    assert db.current_version() == 15
    with db.connect() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        project_columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
        section_columns = {row["name"] for row in connection.execute("PRAGMA table_info(script_sections)")}
    assert {"voice_profiles", "voice_preferences"} <= tables
    assert "default_voice_id" in project_columns
    assert "voice_override_id" in section_columns


def test_builtin_registry_has_unique_english_and_khmer_presets():
    registry = VoiceRegistry()
    voices = registry.list_all()
    ids = [voice.voice_id for voice in voices]
    assert len(ids) == len(set(ids))
    assert {voice.language for voice in voices} == {"en", "km"}
    assert {"James", "Maya", "Oliver", "Sophie", "Leo"} <= {v.name for v in voices}
    assert {"Sokha", "Dara", "Sreypov", "Ratha"} <= {v.name for v in voices}
    assert all(voice.is_builtin for voice in voices)


def test_voice_search_language_category_and_my_filters(voice_system):
    *_, service = voice_system
    assert {v.name for v in service.browse(query="news")} >= {"James", "Sokha"}
    assert all(v.language == "km" for v in service.browse(language="km"))
    assert all(v.category == "News Anchor" for v in service.browse(category_filter="news"))
    service.create_designed("My Tech", "en", "Professional", "Clear technical narrator")
    my = service.browse(category_filter="my")
    assert [v.name for v in my] == ["My Tech"]


def test_favorite_and_recent_usage_persist(voice_system):
    db, _, _, _, _, service = voice_system
    assert service.toggle_favorite("preset-james") is True
    service.mark_used("preset-james")
    restarted = VoiceService(VoiceRegistry(), VoiceRepository(db), service.voice_root)
    james = restarted.get("preset-james")
    assert james.favorite is True
    assert james.usage_count == 1
    assert james.last_used_at
    assert [v.voice_id for v in restarted.browse(category_filter="favorites")] == ["preset-james"]


def test_designed_voice_create_edit_duplicate_delete(voice_system):
    *_, service = voice_system
    voice = service.create_designed("Modern Tech", "en", "News Anchor", "Professional technology narrator", ["Clear", "Modern"])
    assert service.get(voice.voice_id).voice_description.startswith("Professional")
    edited = service.edit_voice(voice.voice_id, name="Modern Tech Anchor", voice_description="Warm modern technology narrator")
    assert edited.name == "Modern Tech Anchor"
    clone = service.duplicate_voice(voice.voice_id)
    assert clone.voice_id != voice.voice_id
    assert clone.name.endswith("Copy")
    service.delete_voice(clone.voice_id)
    with pytest.raises(VoiceServiceError):
        service.get(clone.voice_id)


def test_designed_voice_validation_and_khmer_unicode(voice_system):
    *_, service = voice_system
    with pytest.raises(VoiceServiceError):
        service.create_designed("", "en", "News Anchor", "voice")
    with pytest.raises(VoiceServiceError):
        service.create_designed("Bad", "xx", "News Anchor", "voice")
    voice = service.create_designed(
        "សំឡេងព័ត៌មាន", "km", "News Anchor",
        "សំឡេងអ្នកអានព័ត៌មានភាសាខ្មែរ ច្បាស់លាស់ មានទំនុកចិត្ត និងល្បឿនធម្មជាតិ។",
    )
    assert service.get(voice.voice_id).name == "សំឡេងព័ត៌មាន"


def test_reference_voice_requires_consent_and_copies_managed_audio(voice_system, tmp_path: Path):
    *_, service = voice_system
    source = make_wav(tmp_path / "authorized.wav")
    with pytest.raises(VoiceServiceError):
        service.create_reference("My Voice", "en", "Professional", source, False)
    voice = service.create_reference("My Voice", "en", "Professional", source, True)
    managed = Path(voice.reference_audio_path)
    assert managed.is_file()
    assert managed != source
    assert source.is_file()
    assert service.voice_root.resolve() in managed.resolve().parents


def test_reference_voice_replace_rolls_back_on_invalid_source(voice_system, tmp_path: Path):
    *_, service = voice_system
    source = make_wav(tmp_path / "first.wav")
    voice = service.create_reference("Reference", "en", "Friendly", source, True)
    old = Path(voice.reference_audio_path)
    with pytest.raises(Exception):
        service.replace_reference(voice.voice_id, tmp_path / "missing.wav", True)
    persisted = service.get(voice.voice_id)
    assert Path(persisted.reference_audio_path) == old
    assert old.is_file()


def test_project_default_and_section_override_resolution(voice_system):
    _, _, projects, scripts, _, voices = voice_system
    project = projects.create_project("Voice Assignment", "story", "en", "16:9", 30)
    _, sections = scripts.load_or_create(project.project_id)
    voices.assign_project(project.project_id, "preset-james")
    voices.assign_section(project.project_id, sections[1].section_id, "preset-maya")
    assert voices.resolve_voice(project.project_id).voice_id == "preset-james"
    assert voices.resolve_voice(project.project_id, sections[0].section_id).voice_id == "preset-james"
    assert voices.resolve_voice(project.project_id, sections[1].section_id).voice_id == "preset-maya"
    voices.assign_section(project.project_id, sections[1].section_id, None)
    assert voices.resolve_voice(project.project_id, sections[1].section_id).voice_id == "preset-james"


def test_assignments_persist_after_database_restart(voice_system):
    db, _, projects, scripts, _, voices = voice_system
    project = projects.create_project("Restart", "video", "km", "9:16", 30)
    _, sections = scripts.load_or_create(project.project_id)
    custom = voices.create_designed("ខ្មែរ", "km", "Professional", "Clear Khmer professional voice")
    voices.assign_project(project.project_id, custom.voice_id)
    voices.assign_section(project.project_id, sections[0].section_id, "preset-sokha")
    restarted = VoiceService(VoiceRegistry(), VoiceRepository(db), voices.voice_root)
    assert restarted.project_voice(project.project_id).voice_id == custom.voice_id
    assert restarted.section_voice(sections[0].section_id).voice_id == "preset-sokha"


def test_project_duplication_preserves_voice_assignments(voice_system):
    _, _, projects, scripts, _, voices = voice_system
    project = projects.create_project("Duplicate Voice", "news", "en", "16:9", 30)
    _, sections = scripts.load_or_create(project.project_id)
    voices.assign_project(project.project_id, "preset-james")
    voices.assign_section(project.project_id, sections[1].section_id, "preset-maya")
    duplicate = projects.duplicate_project(project.project_id)
    _, duplicate_sections = scripts.load_or_create(duplicate.project_id)
    assert voices.project_voice(duplicate.project_id).voice_id == "preset-james"
    assert voices.section_voice(duplicate_sections[1].section_id).voice_id == "preset-maya"


def test_deleting_project_does_not_delete_global_user_voice(voice_system):
    _, _, projects, _, _, voices = voice_system
    project = projects.create_project("Delete Project", "video", "en", "16:9", 30)
    voice = voices.create_designed("Global Voice", "en", "Professional", "Clear professional narrator")
    voices.assign_project(project.project_id, voice.voice_id)
    projects.delete_project(project.project_id)
    assert voices.get(voice.voice_id).name == "Global Voice"


def test_delete_assigned_voice_requires_explicit_cleanup(voice_system):
    _, _, projects, scripts, _, voices = voice_system
    project = projects.create_project("Guard", "video", "en", "16:9", 30)
    _, sections = scripts.load_or_create(project.project_id)
    voice = voices.create_designed("Assigned", "en", "Professional", "Professional voice")
    voices.assign_project(project.project_id, voice.voice_id)
    voices.assign_section(project.project_id, sections[0].section_id, voice.voice_id)
    assert voices.assignment_count(voice.voice_id) == 2
    with pytest.raises(VoiceInUseError):
        voices.delete_voice(voice.voice_id)
    voices.delete_voice(voice.voice_id, clear_assignments=True)
    assert voices.project_voice(project.project_id) is None
    assert voices.section_voice(sections[0].section_id) is None


def test_reference_delete_never_deletes_original(voice_system, tmp_path: Path):
    *_, service = voice_system
    source = make_wav(tmp_path / "original.wav")
    voice = service.create_reference("Safe", "en", "Friendly", source, True)
    managed = Path(voice.reference_audio_path)
    service.delete_voice(voice.voice_id)
    assert source.is_file()
    assert not managed.exists()


def test_voice_config_maps_friendly_controls_to_design_description(voice_system):
    *_, service = voice_system
    config = service.voice_config("preset-james", pace="slow", energy="high", tone="calm")
    assert config.mode_code == "designed"
    assert "slow" in config.description
    assert "high" in config.description
    assert config.metadata["voice_id"] == "preset-james"
    reference_source = make_wav(service.voice_root / "sample.wav")
    reference = service.create_reference("Ref", "en", "Professional", reference_source, True)
    ref_config = service.voice_config(reference.voice_id)
    assert ref_config.mode_code == "reference"
    assert ref_config.consent_confirmed is True


def test_preview_cache_key_is_stable_and_changes_with_inputs(voice_system):
    *_, service = voice_system
    a = service.preview_cache_key("preset-james", "Hello", {"cfg": 2}, "v1")
    b = service.preview_cache_key("preset-james", "Hello", {"cfg": 2}, "v1")
    c = service.preview_cache_key("preset-james", "Hello!", {"cfg": 2}, "v1")
    assert a == b
    assert a != c


def test_builtin_voice_is_not_editable_or_deletable(voice_system):
    *_, service = voice_system
    with pytest.raises(VoiceServiceError):
        service.edit_voice("preset-james", name="Changed")
    with pytest.raises(VoiceServiceError):
        service.delete_voice("preset-james")


def test_recommended_sort_prefers_language_and_workflow(voice_system):
    *_, service = voice_system
    items = service.browse(project_language="km", project_workflow="news")
    assert items[0].language == "km"
    assert items[0].category == "News Anchor"

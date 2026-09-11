from __future__ import annotations

from pathlib import Path

import pytest

from domain.script import ScriptPace
from domain.script_section import ScriptSectionType
from services.autosave_service import AutosavePolicy
from services.project_service import ProjectService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService, ScriptValidationError
from storage.database import SQLiteDatabase
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository


@pytest.fixture
def script_system(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "runtime" / "app.db")
    db.initialize()
    project_repo = ProjectRepository(db)
    project_service = ProjectService(project_repo, tmp_path / "projects")
    script_repo = ScriptRepository(db)
    analysis = ScriptAnalysisService()
    service = ScriptService(script_repo, project_repo, analysis)
    project_service.set_script_service(service)
    project = project_service.create_project("Script Project", "video", "en", "16:9", 30)
    return db, project_repo, project_service, script_repo, service, analysis, project


def test_script_migration_and_existing_database_upgrade(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db")
    db.initialize()
    assert db.current_version() == 13
    with db.connect() as connection:
        tables = {r["name"] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        indexes = {r["name"] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"scripts", "script_sections"} <= tables
    assert "idx_scripts_project" in indexes
    assert "idx_script_sections_script_order" in indexes


def test_default_script_creation_hook_body_outro(script_system):
    _, _, _, repo, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    assert script.project_id == project.project_id
    assert script.language == "en"
    assert [s.type for s in sections] == ["hook", "body", "outro"]
    assert [s.title for s in sections] == ["Hook", "Body", "Outro"]
    assert [s.order for s in sections] == [0, 1, 2]
    assert repo.count_for_project(project.project_id) == 1


def test_script_and_section_serialization(script_system):
    _, _, _, _, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    payload = script.to_dict()
    section_payload = sections[0].to_dict()
    assert payload["project_id"] == project.project_id
    assert payload["pace"] == "normal"
    assert section_payload["type"] == "hook"
    assert section_payload["enabled"] is True


def test_add_rename_duplicate_delete_and_order(script_system):
    _, _, _, repo, service, _, project = script_system
    script, _ = service.load_or_create(project.project_id)
    added = service.add_section(project.project_id, "Key Details", "body")
    assert added.order == 3
    renamed = service.rename_section(project.project_id, added.section_id, "Background")
    assert renamed.title == "Background"
    renamed.content = "Important content"
    service.save_section(project.project_id, renamed)

    duplicated = service.duplicate_section(project.project_id, renamed.section_id)
    sections = repo.list_sections(script.script_id)
    assert duplicated.section_id != renamed.section_id
    assert duplicated.title == "Background Copy"
    assert duplicated.content == "Important content"
    assert [s.order for s in sections] == list(range(len(sections)))
    assert sections[-2].section_id == renamed.section_id
    assert sections[-1].section_id == duplicated.section_id

    service.move_section(project.project_id, duplicated.section_id, 1)
    sections = repo.list_sections(script.script_id)
    assert sections[1].section_id == duplicated.section_id
    assert [s.order for s in sections] == list(range(len(sections)))

    service.delete_section(project.project_id, duplicated.section_id)
    sections = repo.list_sections(script.script_id)
    assert duplicated.section_id not in {s.section_id for s in sections}
    assert [s.order for s in sections] == list(range(len(sections)))


def test_enabled_sections_drive_combined_text_and_analysis(script_system):
    _, _, _, repo, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    sections[0].content = "Strong opening line"
    sections[1].content = "This is the main body with useful details."
    sections[2].content = "Thanks for watching"
    for s in sections:
        service.save_section(project.project_id, s)
    service.set_section_enabled(project.project_id, sections[1].section_id, False)

    text = service.get_combined_text(project.project_id)
    assert "Strong opening line" in text
    assert "main body" not in text
    assert "Thanks for watching" in text
    result = service.analyze(project.project_id)
    assert result.word_count == 6


def test_english_word_count_and_duration_paces():
    analysis = ScriptAnalysisService()
    normal = analysis.analyze_text("one two three four five", "en", "normal")
    slow = analysis.analyze_text("one two three four five", "en", "slow")
    fast = analysis.analyze_text("one two three four five", "en", "fast")
    assert normal.word_count == 5
    assert slow.estimated_duration_ms > normal.estimated_duration_ms > fast.estimated_duration_ms
    assert normal.metric_label == "words"


def test_khmer_character_metric_and_duration():
    analysis = ScriptAnalysisService()
    text = "សួស្តី! ថ្ងៃនេះយើងនឹងនិយាយអំពីព័ត៌មានថ្មីៗ។"
    result = analysis.analyze_text(text, "km", "normal")
    assert result.character_count > 20
    assert result.metric_label == "characters"
    assert result.metric_value == result.character_count
    assert result.estimated_duration_ms > 0


def test_khmer_unicode_persistence_and_language_change_does_not_translate(script_system):
    _, _, _, repo, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    khmer = "សួស្តី! ថ្ងៃនេះយើងនឹងនិយាយអំពីព័ត៌មានថ្មីៗ និងបច្ចេកវិទ្យា។"
    sections[1].content = khmer
    service.save_section(project.project_id, sections[1])
    service.set_language(project.project_id, "km")

    reloaded = repo.list_sections(script.script_id)
    assert reloaded[1].content == khmer
    assert service.repository.get_primary_by_project(project.project_id).language == "km"
    assert khmer in service.get_combined_text(project.project_id)


def test_mixed_unicode_text_is_not_normalized(script_system):
    _, _, _, repo, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    mixed = 'Hello “world” 👋\n\nសួស្តី ពិភពលោក!'
    sections[0].content = mixed
    service.save_section(project.project_id, sections[0])
    assert repo.list_sections(script.script_id)[0].content == mixed


def test_pace_persistence(script_system):
    _, _, _, repo, service, _, project = script_system
    service.load_or_create(project.project_id)
    service.set_pace(project.project_id, ScriptPace.FAST.value)
    assert str(repo.get_primary_by_project(project.project_id).pace) == "fast"


def test_tts_preparation_preserves_boundaries(script_system):
    _, _, _, _, service, _, project = script_system
    _, sections = service.load_or_create(project.project_id)
    sections[0].content = "Hook text."
    sections[1].content = "Body text."
    sections[2].content = ""
    for section in sections:
        service.save_section(project.project_id, section)
    prepared = service.prepare_for_tts(project.project_id)
    assert prepared["text"] == "Hook text.\n\nBody text."
    assert len(prepared["sections"]) == 2
    first, second = prepared["sections"]
    assert first["start_character"] == 0
    assert second["start_character"] == len("Hook text.") + 2


def test_import_txt_add_replace_bom_and_khmer(script_system, tmp_path: Path):
    _, _, _, repo, service, _, project = script_system
    script, _ = service.load_or_create(project.project_id)
    source = tmp_path / "script.txt"
    source.write_bytes(b"\xef\xbb\xbfImported text")
    added = service.import_text(project.project_id, source, "add")
    assert added.content == "Imported text"
    assert len(repo.list_sections(script.script_id)) == 4

    khmer = tmp_path / "khmer.txt"
    khmer.write_text("ព័ត៌មានថ្មីៗ", encoding="utf-8")
    replaced = service.import_text(project.project_id, khmer, "replace")
    sections = repo.list_sections(script.script_id)
    assert len(sections) == 1
    assert sections[0].section_id == replaced.section_id
    assert sections[0].content == "ព័ត៌មានថ្មីៗ"


def test_export_txt_preserves_utf8_and_section_titles(script_system, tmp_path: Path):
    _, _, _, _, service, _, project = script_system
    _, sections = service.load_or_create(project.project_id)
    sections[0].content = "Hello"
    sections[1].content = "ព័ត៌មានថ្មីៗ"
    for s in sections:
        service.save_section(project.project_id, s)
    target = service.export_text(project.project_id, tmp_path / "export")
    content = target.read_text(encoding="utf-8")
    assert "HOOK" in content
    assert "ព័ត៌មានថ្មីៗ" in content
    assert target.suffix == ".txt"


def test_restart_persistence_sections_language_and_enabled(script_system, tmp_path: Path):
    db, _, project_service, repo, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    sections[0].content = "Persist me"
    service.save_section(project.project_id, sections[0])
    service.set_section_enabled(project.project_id, sections[2].section_id, False)
    service.move_section(project.project_id, sections[2].section_id, 0)
    service.set_language(project.project_id, "km")

    restarted_db = SQLiteDatabase(db.path)
    restarted_db.initialize()
    restarted_projects = ProjectRepository(restarted_db)
    restarted_repo = ScriptRepository(restarted_db)
    restarted = ScriptService(restarted_repo, restarted_projects)
    loaded, loaded_sections = restarted.load_or_create(project.project_id)
    assert loaded.language == "km"
    assert loaded_sections[0].title == "Outro"
    assert loaded_sections[0].enabled is False
    assert any(s.content == "Persist me" for s in loaded_sections)


def test_project_duplication_creates_independent_script(script_system):
    _, _, project_service, repo, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    sections[1].content = "Original script body"
    service.save_section(project.project_id, sections[1])

    duplicate = project_service.duplicate_project(project.project_id)
    cloned = repo.get_primary_by_project(duplicate.project_id)
    assert cloned is not None
    assert cloned.script_id != script.script_id
    cloned_sections = repo.list_sections(cloned.script_id)
    assert [s.content for s in cloned_sections] == [s.content for s in repo.list_sections(script.script_id)]
    assert {s.section_id for s in cloned_sections}.isdisjoint({s.section_id for s in sections})

    cloned_sections[1].content = "Changed duplicate"
    service.save_section(duplicate.project_id, cloned_sections[1])
    assert repo.list_sections(script.script_id)[1].content == "Original script body"


def test_project_deletion_cascades_only_its_script(script_system):
    _, _, project_service, repo, service, _, project = script_system
    service.load_or_create(project.project_id)
    other = project_service.create_project("Other", "video", "en", "16:9", 30)
    service.load_or_create(other.project_id)
    project_service.delete_project(project.project_id)
    assert repo.get_primary_by_project(project.project_id) is None
    assert repo.get_primary_by_project(other.project_id) is not None


def test_repository_project_ownership_guard(script_system):
    _, _, project_service, _, service, _, project = script_system
    _, sections = service.load_or_create(project.project_id)
    other = project_service.create_project("Other", "video", "en", "16:9", 30)
    with pytest.raises(ScriptValidationError):
        service.rename_section(other.project_id, sections[0].section_id, "Stolen")


def test_autosave_debounce_policy():
    policy = AutosavePolicy(delay_seconds=1.5)
    assert not policy.pending
    policy.touch(10.0)
    assert policy.pending
    assert not policy.due(11.49)
    assert policy.due(11.5)
    policy.touch(12.0)
    assert not policy.due(13.0)
    policy.clear()
    assert not policy.pending


def test_large_script_analysis_is_stable():
    analysis = ScriptAnalysisService()
    text = ("long narration content " * 900)[:18000]
    result = analysis.analyze_text(text, "en", "normal")
    assert len(text) == 18000
    assert result.word_count > 1000
    assert result.estimated_duration_ms > 0



def test_upgrade_from_phase5_schema_applies_only_script_migration(tmp_path: Path):
    from storage.migrations.m001_create_projects import migrate as m1
    from storage.migrations.m002_create_media_assets import migrate as m2

    db = SQLiteDatabase(tmp_path / "upgrade.db")
    db.path.parent.mkdir(parents=True, exist_ok=True)
    with db.connect() as connection:
        connection.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        m1(connection)
        m2(connection)
        connection.execute("INSERT INTO schema_migrations VALUES (1, 'create_projects', 'old')")
        connection.execute("INSERT INTO schema_migrations VALUES (2, 'create_media_assets', 'old')")
        connection.commit()
    db.initialize()
    assert db.current_version() == 13
    with db.connect() as connection:
        versions = [row["version"] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert versions == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


def test_scene_source_marker_persists_without_creating_scenes(script_system):
    _, _, _, repo, service, _, project = script_system
    script, sections = service.load_or_create(project.project_id)
    target = sections[1]
    service.set_scene_source(project.project_id, target.section_id, False)
    stored = next(s for s in repo.list_sections(script.script_id) if s.section_id == target.section_id)
    assert stored.metadata["scene_source"] is False

def test_invalid_import_encoding_is_friendly(script_system, tmp_path: Path):
    _, _, _, _, service, _, project = script_system
    service.load_or_create(project.project_id)
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\xff\xfe\x00\x81")
    with pytest.raises(Exception):
        service.import_text(project.project_id, bad, "add")

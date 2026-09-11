from __future__ import annotations

from pathlib import Path

import pytest

from app.bootstrap import build_container
from domain.director_plan import DirectorRequest
from domain.translation import Translation
from domain.translation_segment import TranslationSegment
from engines.llm.deterministic_director import DeterministicDirectorProvider
from engines.llm.errors import DirectorApplyConflict, DirectorInvalidRequest
from services.ai_director_service import AIDirectorService
from services.director_apply_service import DirectorApplyService
from services.director_rule_engine import DirectorRuleEngine
from services.project_service import ProjectService
from services.scene_service import SceneService
from services.script_service import ScriptService
from services.subtitle_preset_service import SubtitlePresetService
from services.voice_service import VoiceService
from storage.database import SQLiteDatabase
from storage.repositories.director_plan_repository import DirectorPlanRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.translation_repository import TranslationRepository


def make_app(tmp_path: Path, monkeypatch, *, create_project: bool = True):
    home = tmp_path / "home"
    data = tmp_path / "xdg"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    c = build_container()
    project = None
    if create_project:
        project = c.resolve(ProjectService).create_project("Director Test", "video", "en", "16:9", 30)
    return c, project


def create_script(c, project_id: str, *, language="en", long=False):
    service = c.resolve(ScriptService)
    script, sections = service.load_or_create(project_id)
    service.set_language(project_id, language)
    for i, section in enumerate(sections):
        section.content = (("technology update " * (50 if long else 8)).strip() + f" section {i}") if language == "en" else ("ព័ត៌មានបច្ចេកវិទ្យាថ្មី " * (40 if long else 8)).strip()
        service.save_section(project_id, section)
    return script, service.repository.list_sections(script.id)


def request(project_id: str, **kwargs):
    values = dict(
        project_id=project_id,
        workflow="shorts",
        content_source_type="idea",
        content_text="Create a short technology explainer using only the information I provide.",
        language="en",
        platform="tiktok",
        target_duration_ms=60_000,
        audience="general",
        style="modern",
        pace="balanced",
        tone="neutral",
    )
    values.update(kwargs)
    return DirectorRequest(**values)


def test_phase14_schema_migration(tmp_path, monkeypatch):
    c, _ = make_app(tmp_path, monkeypatch)
    db = c.resolve(SQLiteDatabase)
    assert db.current_version() == 16
    with db.connect() as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"director_plans", "director_scene_plans"} <= tables
        columns = {r[1] for r in con.execute("PRAGMA table_info(projects)")}
        assert {"active_director_plan_id", "default_subtitle_preset_id"} <= columns


def test_request_validation_rejects_invalid_values():
    with pytest.raises(ValueError): request("p", workflow="batch").validate()
    with pytest.raises(ValueError): request("p", platform="unknown").validate()
    with pytest.raises(ValueError): request("p", target_duration_ms=0).validate()
    with pytest.raises(ValueError): request("p", content_text="").validate()


def test_platform_and_workflow_profiles_are_deterministic():
    rules = DirectorRuleEngine()
    req = request("p")
    assert rules.recommend_aspect_ratio(req) == "9:16"
    assert rules.effective_pace(req) == "fast"
    a = rules.scene_distribution(req)
    b = rules.scene_distribution(req)
    assert a == b
    assert sum(a.durations_ms) == 60_000


def test_sixty_second_shorts_plan(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    plan, scenes = service.create_plan(request(project.id))
    assert plan.aspect_ratio == "9:16"
    assert plan.recommendation("subtitles").value in {"creator", "bold"}
    assert plan.recommendation("hook").value == "Visual Hook"
    assert plan.recommendation("voice").value == "Energetic"
    assert 8 <= len(scenes) <= 30
    assert sum(x.target_duration_ms for x in scenes) == 60_000


def test_news_manual_idea_is_structure_only(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    plan, scenes = c.resolve(AIDirectorService).create_plan(request(
        project.id, workflow="news", platform="youtube_shorts",
        content_text="Plan a technology news update about a topic I will source later.",
    ))
    notices = plan.metadata["notices"]
    assert any("require sources" in x for x in notices)
    serialized = str([s.to_dict() for s in scenes])
    assert "scientists discovered" not in serialized.lower()
    assert plan.recommendation("hook").value == "Direct Summary"


def test_story_plan_has_story_structure(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    plan, scenes = c.resolve(AIDirectorService).create_plan(request(
        project.id, workflow="story", platform="youtube", target_duration_ms=180_000, pace="balanced"
    ))
    titles = [s.title for s in scenes]
    assert titles[0] == "Hook"
    assert "Setup" in titles
    assert "Development" in titles
    assert "Peak" in titles
    assert titles[-1] == "Resolution"
    assert plan.recommendation("transitions").value == "fade"


def test_khmer_plan_is_unicode_safe_and_uses_character_target(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    plan, scenes = c.resolve(AIDirectorService).create_plan(request(
        project.id, language="km", content_text="បង្កើតវីដេអូខ្លីអំពីបច្ចេកវិទ្យា។"
    ))
    target = plan.recommendation("script").value
    assert target["metric"] == "characters"
    assert target["value"] > 0
    assert plan.metadata["idea"].startswith("បង្កើត")
    assert sum(s.target_duration_ms for s in scenes) == 60_000


def test_script_source_reuses_sections_and_duration_analysis(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    script, sections = create_script(c, project.id, long=True)
    service = c.resolve(AIDirectorService)
    plan, scenes = service.create_plan(request(
        project.id, workflow="video", platform="youtube", content_source_type="script",
        content_source_id=script.id, content_text="", target_duration_ms=60_000
    ))
    assert len(scenes) == len([s for s in sections if s.enabled])
    assert [s.script_section_id for s in scenes] == [s.id for s in sections if s.enabled]
    assert any("reducing narration" in x for x in plan.metadata["notices"])


def test_translation_source_planning_does_not_generate_tts(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    repo = c.resolve(TranslationRepository)
    tr = Translation(project.id, "manual_text", "manual-source", "en", "km", "manual", status="approved")
    seg = TranslationSegment(tr.id, 0, "Hello", translated_text="សួស្តី", machine_translation="សួស្តី", reviewed=True)
    repo.create(tr, [seg])
    plan, scenes = c.resolve(AIDirectorService).create_plan(request(
        project.id, workflow="translate", content_source_type="translation", content_source_id=tr.id,
        content_text="", language="km"
    ))
    assert plan.metadata["sourceSummary"]["targetLanguage"] == "km"
    assert plan.recommendation("voice").value == "Professional"
    assert all("audio" not in s.metadata for s in scenes)



def test_edit_scene_count_rebuilds_structured_scene_plan(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id))
    service.edit_recommendation(project.id, plan.id, "scenes", 7)
    loaded, scenes = service.get(project.id, plan.id)
    assert loaded.recommendation("scenes").value == 7
    assert len(scenes) == 7
    assert sum(s.target_duration_ms for s in scenes) == loaded.target_duration_ms

def test_plan_persistence_and_multiple_plans(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    p1, _ = service.create_plan(request(project.id, target_duration_ms=60_000))
    p2, _ = service.create_plan(request(project.id, platform="youtube", target_duration_ms=180_000))
    assert {p.id for p in service.list_plans(project.id)} == {p1.id, p2.id}
    assert service.get(project.id, p1.id)[0].schema_version == 1
    assert service.get(project.id, p1.id)[0].rule_engine_version == "1.0"


def test_lock_and_regenerate_preserves_locked_and_manual_edits(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id))
    service.edit_recommendation(project.id, plan.id, "voice", "Documentary")
    service.lock_recommendation(project.id, plan.id, "format", True)
    before, _ = service.get(project.id, plan.id)
    format_before = before.recommendation("format").value
    refreshed, _, _ = service.regenerate(project.id, plan.id, "all_unlocked")
    assert refreshed.recommendation("format").value == format_before
    assert refreshed.recommendation("format").locked is True
    assert refreshed.recommendation("voice").value == "Documentary"
    assert refreshed.recommendation("voice").user_modified is True


def test_scene_plan_lock_survives_scene_regeneration(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    plan, scenes = service.create_plan(request(project.id))
    first = scenes[0]
    service.update_scene_plan(project.id, plan.id, first.id, title="My Locked Hook", duration_ms=first.target_duration_ms, locked=True)
    _, regenerated, _ = service.regenerate(project.id, plan.id, "scenes")
    assert regenerated[0].title == "My Locked Hook"
    assert regenerated[0].locked is True


def test_plan_approval_active_and_apply_settings(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService); apply = c.resolve(DirectorApplyService)
    plan, _ = service.create_plan(request(project.id))
    service.approve(project.id, plan.id)
    result = apply.apply(project.id, plan.id, mode="settings_only")
    assert result["aspectRatio"] == "9:16"
    assert c.resolve(ProjectService).repository.get_by_id(project.id).aspect_ratio == "9:16"
    assert service.repository.active_id(project.id) == plan.id
    assert service.get(project.id, plan.id)[0].status_code == "applied"


def test_apply_subtitle_preference_uses_existing_registry(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService); apply = c.resolve(DirectorApplyService)
    plan, _ = service.create_plan(request(project.id))
    apply.apply(project.id, plan.id, mode="settings_only")
    assert service.repository.default_subtitle_preset(project.id) == "creator"
    assert "creator" in {x["id"] for x in c.resolve(SubtitlePresetService).list_presets()}


def test_voice_matches_and_explicit_voice_apply(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService); voices = c.resolve(VoiceService)
    plan, _ = service.create_plan(request(project.id, workflow="news", language="en"))
    matches = service.voice_matches(plan, voices)
    assert matches
    chosen = matches[0]["id"]
    c.resolve(DirectorApplyService).apply(project.id, plan.id, mode="settings_only", voice_id=chosen)
    assert voices.project_voice(project.id).id == chosen


def test_create_scenes_from_plan_and_no_silent_replace(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService); apply = c.resolve(DirectorApplyService); scenesvc = c.resolve(SceneService)
    plan, planned = service.create_plan(request(project.id, target_duration_ms=30_000))
    scenesvc.add_scene(project.id, "Manual Scene", 4000)
    apply.apply(project.id, plan.id, mode="settings_only")
    assert [s.name for s in scenesvc.list_scenes(project.id)] == ["Manual Scene"]
    result = apply.apply(project.id, plan.id, mode="add_scenes")
    assert len(result["createdSceneIds"]) == len(planned)
    assert len(scenesvc.list_scenes(project.id)) == len(planned) + 1


def test_replace_scenes_requires_explicit_mode(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService); apply = c.resolve(DirectorApplyService); scenesvc = c.resolve(SceneService)
    scenesvc.add_scene(project.id, "Existing", 5000)
    plan, planned = service.create_plan(request(project.id, target_duration_ms=30_000))
    apply.apply(project.id, plan.id, mode="replace_scenes")
    names = [s.name for s in scenesvc.list_scenes(project.id)]
    assert "Existing" not in names
    assert len(names) == len(planned)


def test_source_fingerprint_marks_script_plan_outdated(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    script, sections = create_script(c, project.id)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id, workflow="video", content_source_type="script", content_source_id=script.id, content_text=""))
    section = sections[0]; section.content += " changed"; c.resolve(ScriptService).save_section(project.id, section)
    loaded, _ = service.get(project.id, plan.id)
    assert loaded.status_code == "outdated"


def test_refresh_source_preserves_locked_recommendation(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    script, sections = create_script(c, project.id)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id, workflow="video", content_source_type="script", content_source_id=script.id, content_text=""))
    service.edit_recommendation(project.id, plan.id, "voice", "Storyteller")
    service.lock_recommendation(project.id, plan.id, "voice", True)
    sections[0].content += " updated"; c.resolve(ScriptService).save_section(project.id, sections[0])
    refreshed, _ = service.refresh_from_source(project.id, plan.id)
    assert refreshed.recommendation("voice").value == "Storyteller"
    assert refreshed.recommendation("voice").locked
    assert refreshed.status_code == "review"


def test_duplicate_and_delete_plan_are_non_destructive(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService); scenesvc = c.resolve(SceneService)
    plan, _ = service.create_plan(request(project.id))
    clone = service.duplicate_plan(project.id, plan.id)
    assert clone.id != plan.id
    assert len(service.repository.scenes(clone.id)) == len(service.repository.scenes(plan.id))
    scenesvc.add_scene(project.id, "Keep Me", 5000)
    service.delete_plan(project.id, clone.id)
    assert scenesvc.list_scenes(project.id)[0].name == "Keep Me"


def test_restart_persists_plan_edits_and_locks(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    plan, scenes = service.create_plan(request(project.id))
    service.edit_recommendation(project.id, plan.id, "voice", "Documentary")
    service.lock_recommendation(project.id, plan.id, "voice", True)
    service.update_scene_plan(project.id, plan.id, scenes[0].id, title="Persistent Hook", duration_ms=scenes[0].target_duration_ms, locked=True)
    # New container, same app data.
    c2 = build_container(); service2 = c2.resolve(AIDirectorService)
    loaded, scene_rows = service2.get(project.id, plan.id)
    assert loaded.recommendation("voice").value == "Documentary"
    assert loaded.recommendation("voice").locked
    assert scene_rows[0].title == "Persistent Hook"
    assert scene_rows[0].locked


def test_project_duplication_remaps_director_script_source(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    script, sections = create_script(c, project.id)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id, workflow="video", content_source_type="script", content_source_id=script.id, content_text=""))
    service.repository.set_active(project.id, plan.id)
    duplicate = c.resolve(ProjectService).duplicate_project(project.id)
    duplicated_plans = service.list_plans(duplicate.id)
    assert len(duplicated_plans) == 1
    copied = duplicated_plans[0]
    assert copied.id != plan.id
    assert copied.source_id != script.id
    copied_script = c.resolve(ScriptRepository).get_primary_by_project(duplicate.id)
    assert copied.source_id == copied_script.id
    copied_scene_plans = service.repository.scenes(copied.id)
    copied_section_ids = {s.id for s in c.resolve(ScriptRepository).list_sections(copied_script.id)}
    assert {x.script_section_id for x in copied_scene_plans if x.script_section_id} <= copied_section_ids
    assert service.repository.active_id(duplicate.id) == copied.id


def test_project_delete_cascades_director_only(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id))
    c.resolve(ProjectService).delete_project(project.id)
    assert service.repository.get(plan.id) is None


def test_provider_is_explicitly_offline_and_structured():
    provider = DeterministicDirectorProvider()
    assert provider.provider.requires_network is False
    assert provider.provider.requires_credentials is False
    assert provider.provider.supports_structured_output is True
    assert "not sent" in provider.provider.privacy_description


def test_same_request_same_rules_produces_same_recommendation_values():
    provider = DeterministicDirectorProvider()
    req = request("project-id")
    context = {"project_aspect_ratio": "16:9", "source_fingerprint": "same"}
    a, a_scenes = provider.create_plan(req, context)
    b, b_scenes = provider.create_plan(req, context)
    assert [(r.category, r.value) for r in a.recommendations] == [(r.category, r.value) for r in b.recommendations]
    assert [(s.title, s.target_duration_ms) for s in a_scenes] == [(s.title, s.target_duration_ms) for s in b_scenes]


def test_director_source_options_include_script_and_existing_scenes(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    create_script(c, project.id)
    c.resolve(SceneService).add_scene(project.id, "Existing", 5000)
    options = c.resolve(AIDirectorService).source_options(project.id)
    assert options["script"]
    assert options["scenes"][0]["id"] == "project-scenes"


def test_upgrade_from_phase13_schema_applies_director_migration_only(tmp_path):
    from storage.migrations import MIGRATIONS
    db = SQLiteDatabase(tmp_path / "upgrade.db")
    db.path.parent.mkdir(parents=True, exist_ok=True)
    with db.connect() as con:
        con.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        for migration in MIGRATIONS:
            if migration.version > 10:
                continue
            migration.apply(con)
            con.execute("INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)", (migration.version,migration.name,"old"))
        con.commit()
    assert db.current_version() == 10
    db.initialize()
    assert db.current_version() == 16
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM director_plans").fetchone()[0] == 0


def test_script_target_reuses_existing_language_rate_profiles():
    rules = DirectorRuleEngine()
    english = request("p", workflow="video", platform="generic", pace="balanced", language="en")
    khmer = request("p", workflow="video", platform="generic", pace="balanced", language="km", content_text="គំនិតវីដេអូ")
    assert rules.script_target(english) == {"metric":"words","value":150,"pace":"balanced"}
    assert rules.script_target(khmer) == {"metric":"characters","value":450,"pace":"balanced"}


@pytest.mark.parametrize("duration", [15_000,30_000,45_000,60_000,90_000,120_000,180_000,300_000])
def test_scene_duration_distribution_matches_target(duration):
    rules = DirectorRuleEngine()
    dist = rules.scene_distribution(request("p", target_duration_ms=duration))
    assert dist.count > 0
    assert sum(dist.durations_ms) == duration
    assert all(ms > 0 for ms in dist.durations_ms)


def test_recommendations_cover_planning_dimensions(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    plan, _ = c.resolve(AIDirectorService).create_plan(request(project.id, workflow="news"))
    categories = {r.category for r in plan.recommendations}
    assert {"format","script","scenes","pacing","voice","subtitles","visuals","music","transitions","hook","outro"} <= categories


def test_existing_scene_source_is_audit_only(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    scene_service = c.resolve(SceneService)
    for i in range(5): scene_service.add_scene(project.id, f"Manual {i+1}", 8_000)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id, workflow="video", content_source_type="scenes", content_source_id="project-scenes", content_text="", target_duration_ms=60_000))
    assert any("Existing project has 5 scenes" in notice for notice in plan.metadata["notices"])
    assert len(scene_service.list_scenes(project.id)) == 5


def test_delete_active_plan_clears_active_reference(tmp_path, monkeypatch):
    c, project = make_app(tmp_path, monkeypatch)
    service = c.resolve(AIDirectorService)
    plan, _ = service.create_plan(request(project.id))
    service.repository.set_active(project.id, plan.id)
    service.delete_plan(project.id, plan.id)
    assert service.repository.active_id(project.id) == ""

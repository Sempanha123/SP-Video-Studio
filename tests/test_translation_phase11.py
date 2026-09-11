from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.media import MediaAsset, MediaType
from domain.model_installation import ModelInstallation, ModelInstallStatus
from domain.project import Project
from domain.script import Script
from domain.script_section import ScriptSection
from domain.transcript import Transcript, TranscriptStatus
from domain.transcript_segment import TranscriptSegment
from domain.translation import TranslationStatus
from domain.translation_segment import TranslationSegmentStatus
from engines.model_registry import ModelRegistry
from engines.translation.errors import TranslationCancelled, TranslationInvalidRequest, TranslationModelNotInstalled
from engines.translation.fake_engine import FakeTranslationEngine
from engines.translation.manager import TranslationEngineManager
from engines.translation.manual_engine import ManualTranslationEngine
from engines.translation.types import TranslationRequest
from services.ai_resource_manager import AIResourceConflict, AIResourceManager
from services.translation_chunking_service import TranslationChunkingService
from services.translation_review_service import TranslationReviewService
from services.translation_service import TranslationService
from storage.database import SQLiteDatabase
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository
from workers.cancellation import CancellationToken


class FakeInstallationRepository:
    def __init__(self, installed: set[str]) -> None:
        self.items = {
            model_id: ModelInstallation(
                model_id=model_id,
                installed=True,
                status=ModelInstallStatus.INSTALLED,
                install_path=model_id,
            )
            for model_id in installed
        }

    def get(self, model_id: str):
        return self.items.get(model_id)


class FakeModelService:
    def __init__(self, root: Path, installed: set[str] | None = None) -> None:
        self.registry = ModelRegistry()
        self.repository = FakeInstallationRepository(installed or {"translation-en-km-opus", "translation-km-en-opus"})
        self.root = root
        self.acquire_calls: list[str] = []
        self.release_calls: list[tuple[str, bool]] = []
        for model_id in self.repository.items:
            self.install_path(self.registry.get(model_id)).mkdir(parents=True, exist_ok=True)

    def install_path(self, model):
        return self.root / model.install_relative_path

    def acquire_model(self, model_id: str, *, loaded: bool = True):
        self.acquire_calls.append(model_id)
        item = self.repository.get(model_id) or ModelInstallation(model_id=model_id)
        item.is_loaded = loaded or item.is_loaded
        item.in_use_count += 1
        return item

    def release_model(self, model_id: str, *, unload: bool = False):
        self.release_calls.append((model_id, unload))
        item = self.repository.get(model_id) or ModelInstallation(model_id=model_id)
        item.in_use_count = max(0, item.in_use_count - 1)
        if unload and item.in_use_count == 0:
            item.is_loaded = False
        return item


class CancellingFakeEngine(FakeTranslationEngine):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def translate(self, request, cancellation=None):
        result = super().translate(request, cancellation)
        self.calls += 1
        if self.calls == 1 and cancellation is not None:
            cancellation.cancel()
        return result


def make_system(tmp_path: Path, *, engine=None, installed=None):
    db = SQLiteDatabase(tmp_path / "data" / "app.db")
    db.initialize()
    projects = ProjectRepository(db)
    media = MediaRepository(db)
    scripts = ScriptRepository(db)
    transcripts = TranscriptRepository(db)
    translations = TranslationRepository(db)

    project_root = tmp_path / "Projects" / "demo"
    project_root.mkdir(parents=True)
    project = Project(title="Demo", workflow="video", language="en", project_path=str(project_root), project_id="project-1")
    projects.create(project)

    script = Script(project_id=project.project_id, title="Demo — Script", language="en", script_id="script-1")
    sections = [
        ScriptSection(script_id=script.script_id, order=0, section_type="hook", title="Hook", content="Welcome to MMO Video Studio." , section_id="sec-1"),
        ScriptSection(script_id=script.script_id, order=1, section_type="body", title="Body", content="RTX 5090 costs $499 in this test {username}.", section_id="sec-2"),
        ScriptSection(script_id=script.script_id, order=2, section_type="outro", title="Outro", content="Thanks for watching.", section_id="sec-3"),
    ]
    scripts.create(script, sections)

    source = project_root / "media" / "audio" / "ព័ត៌មាន.wav"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fake audio")
    asset = MediaAsset(
        asset_id="media-1", project_id=project.project_id, media_type=MediaType.AUDIO,
        name="ព័ត៌មាន.wav", original_path=str(tmp_path / "outside.wav"), project_path=str(source),
        file_size=source.stat().st_size, duration_ms=10000, extension=".wav",
    )
    media.create(asset)
    transcript = Transcript(
        transcript_id="transcript-1", project_id=project.project_id, media_id=asset.asset_id,
        engine="faster-whisper", model_id="whisper-small", model_version="small", language_mode="en",
        detected_language="en", language_probability=0.98, device="cpu", compute_type="int8",
        duration_ms=10000, status=TranscriptStatus.READY, source_fingerprint="fingerprint", active=True,
    )
    transcript_segments = [
        TranscriptSegment(transcript_id=transcript.transcript_id, segment_id="tr-seg-1", order=0, start_ms=0, end_ms=4500, text="Welcome to today's update."),
        TranscriptSegment(transcript_id=transcript.transcript_id, segment_id="tr-seg-2", order=1, start_ms=4500, end_ms=10000, text="The price is $499 in 2026."),
    ]
    transcripts.create_with_segments(transcript, transcript_segments)

    fake_engine = engine or FakeTranslationEngine()
    manager = TranslationEngineManager(local_engine=fake_engine, manual_engine=ManualTranslationEngine())
    model_service = FakeModelService(tmp_path / "models", installed)
    resource_manager = AIResourceManager()
    service = TranslationService(
        translations, projects, transcripts, scripts, model_service, manager,
        TranslationChunkingService(default_max_chars=200), TranslationReviewService(), resource_manager,
    )
    resource_manager.register("translation", service.unload, lambda: service.active_jobs > 0)
    return SimpleNamespace(
        db=db, projects=projects, media=media, scripts=scripts, transcripts=transcripts,
        translations=translations, project=project, script=script, transcript=transcript, asset=asset,
        engine=fake_engine, manager=manager, models=model_service, service=service,
    )


def test_phase11_migration_and_model_registry(tmp_path: Path):
    sys = make_system(tmp_path)
    assert sys.db.current_version() == 13
    with sys.db.connect() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"translations", "translation_segments"} <= tables
    en_km = sys.models.registry.get("translation-en-km-opus")
    km_en = sys.models.registry.get("translation-km-en-opus")
    assert en_km.source_identifier == "Helsinki-NLP/opus-mt-en-mkh"
    assert km_en.source_identifier == "Helsinki-NLP/opus-mt-mkh-en"
    assert en_km.license == km_en.license == "Apache-2.0"
    assert en_km.metadata["targetToken"] == ">>khm<<"


def test_translation_request_validation_and_pair_support():
    req = TranslationRequest(project_id="p", source_language="en", target_language="km", text="Hello")
    req.validate()
    assert FakeTranslationEngine().supports_language_pair("en", "km")
    with pytest.raises(TranslationInvalidRequest):
        TranslationRequest(project_id="p", source_language="en", target_language="en", text="Hello").validate()
    with pytest.raises(TranslationInvalidRequest):
        TranslationRequest(project_id="p", source_language="en", target_language="km", text="  ").validate()


def test_manual_translation_works_without_model(tmp_path: Path):
    sys = make_system(tmp_path, installed=set())
    item = sys.service.create_manual(sys.project.project_id, "Hello", "en", "km")
    assert item.engine_id == "manual"
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    rows = sys.translations.segments(item.translation_id)
    assert rows[0].translated_text == ""
    assert rows[0].status_code == "pending"


def test_transcript_translation_preserves_timestamps_and_source(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    rows = sys.translations.segments(item.translation_id)
    assert [(r.start_ms, r.end_ms) for r in rows] == [(0, 4500), (4500, 10000)]
    assert rows[0].source_text == "Welcome to today's update."
    assert rows[0].translated_text.startswith("ខ្មែរ:")
    assert rows[0].machine_translation == rows[0].translated_text


def test_script_translation_excludes_disabled_and_preserves_order(tmp_path: Path):
    sys = make_system(tmp_path)
    sections = sys.scripts.list_sections(sys.script.script_id)
    sections[1].enabled = False
    sys.scripts.update_section(sys.project.project_id, sections[1])
    item = sys.service.create_from_script(sys.project.project_id, sys.script.script_id, "km")
    rows = sys.translations.segments(item.translation_id)
    assert [r.source_segment_id for r in rows] == ["sec-1", "sec-3"]
    assert [r.order for r in rows] == [0, 1]


def test_machine_output_is_preserved_when_user_edits_and_resets(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    row = sys.translations.segments(item.translation_id)[0]
    machine = row.machine_translation
    edited = sys.service.edit_segment(sys.project.project_id, item.translation_id, row.segment_id, "កែសម្រួលដោយដៃ")
    assert edited.edited and edited.machine_translation == machine and edited.translated_text != machine
    reset = sys.service.reset_segment(sys.project.project_id, item.translation_id, row.segment_id)
    assert not reset.edited and reset.translated_text == machine


def test_review_lock_and_bulk_retranslate_protect_work(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    first, second = sys.translations.segments(item.translation_id)
    sys.service.edit_segment(sys.project.project_id, item.translation_id, first.segment_id, "LOCKED MANUAL")
    sys.service.mark_reviewed(sys.project.project_id, item.translation_id, first.segment_id, True)
    sys.service.set_locked(sys.project.project_id, item.translation_id, first.segment_id, True)
    before = sys.translations.segment(first.segment_id)
    sys.service.edit_segment(sys.project.project_id, item.translation_id, second.segment_id, "MANUAL EDIT")
    # Default bulk translation protects both locked and manually edited rows.
    sys.service.translate_document(sys.project.project_id, item.translation_id, protect_edits=True)
    after = sys.translations.segment(first.segment_id)
    second_after = sys.translations.segment(second.segment_id)
    assert after.translated_text == before.translated_text == "LOCKED MANUAL"
    assert after.locked and after.reviewed
    assert second_after.translated_text == "MANUAL EDIT" and second_after.edited


def test_retranslate_segment_requires_explicit_replace_for_manual_edits(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    row = sys.translations.segments(item.translation_id)[0]
    sys.service.edit_segment(sys.project.project_id, item.translation_id, row.segment_id, "manual")
    with pytest.raises(TranslationInvalidRequest):
        sys.service.retranslate_segment(sys.project.project_id, item.translation_id, row.segment_id)
    replaced = sys.service.retranslate_segment(sys.project.project_id, item.translation_id, row.segment_id, replace_manual=True)
    assert not replaced.edited and replaced.translated_text == replaced.machine_translation


def test_cancel_keeps_completed_rows_and_resume_only_pending(tmp_path: Path):
    token = CancellationToken()
    sys = make_system(tmp_path, engine=CancellingFakeEngine())
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    with pytest.raises(TranslationCancelled):
        sys.service.translate_document(sys.project.project_id, item.translation_id, token)
    rows = sys.translations.segments(item.translation_id)
    assert rows[0].translated_text and rows[1].status_code == "pending"
    token2 = CancellationToken()
    sys.engine.calls = 99  # do not trigger cancellation again
    result = sys.service.resume(sys.project.project_id, item.translation_id, token2)
    rows = sys.translations.segments(item.translation_id)
    assert all(row.translated_text for row in rows)
    assert result.status_code in {"review", "draft"}


def test_placeholder_number_url_and_keep_term_protection():
    review = TranslationReviewService()
    source = "OpenAI sent {username} to https://example.com for $499 in 2026."
    protected = review.protect(source, ["OpenAI"])
    assert "OpenAI" not in protected.text and "{username}" not in protected.text
    restored, missing = review.restore(protected.text, protected)
    assert restored == source and missing == ()
    warnings = review.quality_warnings(source, "តម្លៃគឺ $499 នៅឆ្នាំ 2026.")
    assert not any("numbers" in item.lower() for item in warnings)


def test_chunking_is_lossless_for_english_and_khmer():
    chunker = TranslationChunkingService(default_max_chars=200)
    english = ("Sentence one. Sentence two!\n\n" * 20).strip()
    khmer = ("សួស្តី។ នេះជាការសាកល្បង!\n\n" * 25).strip()
    assert "".join(chunker.chunk(english, "en", 120)) == english
    assert "".join(chunker.chunk(khmer, "km", 120)) == khmer


def test_search_review_progress_approve_and_exports(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    rows = sys.translations.segments(item.translation_id)
    assert sys.service.search(sys.project.project_id, item.translation_id, "price")
    with pytest.raises(TranslationInvalidRequest):
        sys.service.approve(sys.project.project_id, item.translation_id)
    for row in rows:
        sys.service.mark_reviewed(sys.project.project_id, item.translation_id, row.segment_id, True)
    reviewed, total, ratio = sys.service.review_progress(sys.project.project_id, item.translation_id)
    assert (reviewed, total, ratio) == (2, 2, 1.0)
    assert sys.service.approve(sys.project.project_id, item.translation_id).status_code == TranslationStatus.APPROVED.value
    translated = sys.service.export_txt(sys.project.project_id, item.translation_id, tmp_path / "ខ្មែរ.txt")
    bilingual = sys.service.export_txt(sys.project.project_id, item.translation_id, tmp_path / "bilingual.txt", bilingual=True)
    assert "ខ្មែរ:" in translated.read_text(encoding="utf-8")
    assert "EN:" in bilingual.read_text(encoding="utf-8") and "KM:" in bilingual.read_text(encoding="utf-8")


def test_source_sync_only_marks_changed_segment_and_preserves_unchanged_review(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    first, second = sys.translations.segments(item.translation_id)
    sys.service.mark_reviewed(sys.project.project_id, item.translation_id, first.segment_id, True)
    sys.service.mark_reviewed(sys.project.project_id, item.translation_id, second.segment_id, True)
    sys.transcripts.update_segment_text(sys.transcript.transcript_id, "tr-seg-2", "The updated price is $599 in 2026.", edited=True)
    assert sys.service.refresh_outdated(sys.project.project_id, item.translation_id)
    sys.service.sync_source(sys.project.project_id, item.translation_id)
    rows = {row.source_segment_id: row for row in sys.translations.segments(item.translation_id)}
    assert rows["tr-seg-1"].reviewed is True
    assert rows["tr-seg-2"].reviewed is False
    assert rows["tr-seg-2"].status_code == TranslationSegmentStatus.NEEDS_ATTENTION.value
    assert rows["tr-seg-2"].source_text.startswith("The updated price")


def test_script_reorder_sync_preserves_translation_when_text_unchanged(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_script(sys.project.project_id, sys.script.script_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    rows = sys.translations.segments(item.translation_id)
    for row in rows:
        sys.service.mark_reviewed(sys.project.project_id, item.translation_id, row.segment_id, True)
    sections = sys.scripts.list_sections(sys.script.script_id)
    sections = [sections[2], sections[0], sections[1]]
    sys.scripts.save_order(sys.project.project_id, sys.script.script_id, sections)
    sys.service.sync_source(sys.project.project_id, item.translation_id)
    refreshed = {r.source_segment_id: r for r in sys.translations.segments(item.translation_id)}
    assert refreshed["sec-1"].reviewed is True
    assert refreshed["sec-3"].reviewed is True
    assert refreshed["sec-3"].order == 0


def test_missing_local_model_reports_without_download(tmp_path: Path):
    sys = make_system(tmp_path, installed={"translation-km-en-opus"})
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    with pytest.raises(TranslationModelNotInstalled):
        sys.service.translate_document(sys.project.project_id, item.translation_id)


def test_model_in_use_and_cpu_first_resource_policy(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km", device="auto")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    assert sys.models.acquire_calls.count("translation-en-km-opus") >= 2
    assert any(model_id == "translation-en-km-opus" for model_id, _ in sys.models.release_calls)


def test_ai_resource_manager_blocks_cuda_when_other_engine_busy():
    manager = AIResourceManager()
    manager.register("tts", lambda: None, lambda: True)
    with pytest.raises(AIResourceConflict):
        manager.prepare("translation", "cuda")
    manager.prepare("translation", "cpu")


def test_translation_restart_persistence(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    row = sys.translations.segments(item.translation_id)[0]
    sys.service.edit_segment(sys.project.project_id, item.translation_id, row.segment_id, "ការកែប្រែ")
    sys.service.mark_reviewed(sys.project.project_id, item.translation_id, row.segment_id, True)
    sys.service.set_locked(sys.project.project_id, item.translation_id, row.segment_id, True)
    restarted = TranslationRepository(sys.db)
    saved = restarted.get(item.translation_id)
    restored = restarted.segment(row.segment_id)
    assert saved is not None and saved.source_language == "en" and saved.target_language == "km"
    assert restored is not None and restored.machine_translation and restored.translated_text == "ការកែប្រែ"
    assert restored.edited and restored.reviewed and restored.locked


def test_translation_delete_never_deletes_source(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.delete(sys.project.project_id, item.translation_id)
    assert sys.translations.get(item.translation_id) is None
    assert sys.transcripts.get(sys.transcript.transcript_id) is not None
    assert Path(sys.asset.project_path).exists()


def test_project_delete_cascades_translation_records(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_script(sys.project.project_id, sys.script.script_id, "km")
    with sys.db.connect() as connection, connection:
        connection.execute("DELETE FROM projects WHERE id=?", (sys.project.project_id,))
    assert sys.translations.get(item.translation_id) is None


def test_model_registry_has_unique_translation_ids():
    models = [m for m in ModelRegistry().list_all() if m.family == "marian-translation"]
    assert {m.model_id for m in models} == {"translation-en-km-opus", "translation-km-en-opus"}
    assert len({m.model_id for m in models}) == len(models)


def test_source_sync_adds_new_and_orphans_deleted_script_sections(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_script(sys.project.project_id, sys.script.script_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    sections = sys.scripts.list_sections(sys.script.script_id)
    sys.scripts.delete_section(sys.project.project_id, "sec-2")
    from domain.script_section import ScriptSection
    sys.scripts.create_section(sys.project.project_id, ScriptSection(
        script_id=sys.script.script_id, section_id="sec-4", order=3, section_type="body",
        title="New", content="A newly added source section.",
    ))
    sys.service.sync_source(sys.project.project_id, item.translation_id)
    rows = {r.source_segment_id: r for r in sys.translations.segments(item.translation_id)}
    assert rows["sec-2"].status_code == "orphaned"
    assert rows["sec-4"].status_code == "pending" and not rows["sec-4"].translated_text


def test_project_translation_duplication_remaps_source_and_preserves_review_state(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_script(sys.project.project_id, sys.script.script_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    row = sys.translations.segments(item.translation_id)[0]
    sys.service.edit_segment(sys.project.project_id, item.translation_id, row.segment_id, "manual reviewed")
    sys.service.mark_reviewed(sys.project.project_id, item.translation_id, row.segment_id, True)
    sys.service.set_locked(sys.project.project_id, item.translation_id, row.segment_id, True)

    target_root = tmp_path / "Projects" / "copy"
    target_root.mkdir(parents=True)
    target = Project(title="Copy", workflow="video", language="en", project_path=str(target_root), project_id="project-2")
    sys.projects.create(target)
    count = sys.service.duplicate_project_translations(
        sys.project.project_id, target.project_id,
        script_map={"script-1": "script-copy"},
        script_section_map={"sec-1": "sec-copy-1", "sec-2": "sec-copy-2", "sec-3": "sec-copy-3"},
    )
    assert count == 1
    clone = sys.translations.list_for_project(target.project_id)[0]
    assert clone.translation_id != item.translation_id and clone.source_id == "script-copy"
    clone_rows = sys.translations.segments(clone.translation_id)
    assert clone_rows[0].segment_id != row.segment_id
    assert clone_rows[0].source_segment_id == "sec-copy-1"
    assert clone_rows[0].translated_text == "manual reviewed"
    assert clone_rows[0].edited and clone_rows[0].reviewed and clone_rows[0].locked


def test_khmer_to_english_local_pair_uses_registered_model(tmp_path: Path):
    sys = make_system(tmp_path)
    # Make the script Khmer to exercise reverse model resolution.
    script = sys.scripts.get_by_id(sys.script.script_id)
    script.language = "km"
    sys.scripts.update_script(script)
    section = sys.scripts.get_section("sec-1")
    section.content = "សួស្តី! នេះជាព័ត៌មានថ្មី។"
    sys.scripts.update_section(sys.project.project_id, section)
    item = sys.service.create_from_script(sys.project.project_id, sys.script.script_id, "en")
    assert item.model_id == "translation-km-en-opus"
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    assert sys.translations.segments(item.translation_id)[0].translated_text.startswith("English:")


def test_downstream_reviewed_and_dubbing_apis_keep_timing(tmp_path: Path):
    sys = make_system(tmp_path)
    item = sys.service.create_from_transcript(sys.project.project_id, sys.transcript.transcript_id, "km")
    sys.service.translate_document(sys.project.project_id, item.translation_id)
    first = sys.translations.segments(item.translation_id)[0]
    sys.service.mark_reviewed(sys.project.project_id, item.translation_id, first.segment_id, True)
    reviewed = sys.service.get_reviewed_translation_segments(sys.project.project_id, item.translation_id)
    dubbing = sys.service.get_dubbing_segments(sys.project.project_id, item.translation_id)
    assert reviewed == [{
        "segment_id": first.segment_id, "source_segment_id": "tr-seg-1", "start_ms": 0,
        "end_ms": 4500, "target_text": first.translated_text,
    }]
    assert dubbing[0]["start_ms"] == 0 and dubbing[0]["end_ms"] == 4500 and dubbing[0]["language"] == "km"


def test_manual_khmer_unicode_text_persists(tmp_path: Path):
    sys = make_system(tmp_path)
    text = "សួស្តី! ឆ្នាំ 2026 មានបច្ចេកវិទ្យាថ្មីៗ។"
    item = sys.service.create_manual(sys.project.project_id, text, "km", "en")
    restored = TranslationRepository(sys.db).segments(item.translation_id)[0]
    assert restored.source_text == text

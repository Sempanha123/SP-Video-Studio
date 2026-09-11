from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.media import MediaAsset, MediaType
from domain.model_installation import ModelInstallation, ModelInstallStatus
from domain.project import Project
from domain.settings import PerformanceProfile
from domain.system_readiness import SystemReadiness
from domain.transcript import TranscriptStatus
from engines.model_registry import ModelRegistry
from engines.stt.errors import STTCancelled, STTModelNotInstalled, STTResourceConflict
from engines.stt.fake_engine import FakeSTTEngine
from engines.stt.manager import STTEngineManager
from engines.stt.types import STTOutput, STTTranscriptionInfo, TranscriptionRequest
from services.ai_resource_manager import AIResourceConflict, AIResourceManager
from services.transcript_analysis_service import TranscriptAnalysisService, format_timestamp_ms, seconds_to_ms
from services.transcription_service import TranscriptionService
from storage.database import SQLiteDatabase
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.transcript_repository import TranscriptRepository
from workers.cancellation import CancellationToken


class FakeInstallationRepository:
    def __init__(self, installed: set[str]) -> None:
        self.installed = installed
        self.items: dict[str, ModelInstallation] = {}
        for model_id in installed:
            self.items[model_id] = ModelInstallation(
                model_id=model_id, installed=True, status=ModelInstallStatus.INSTALLED, install_path=model_id
            )

    def get(self, model_id: str):
        return self.items.get(model_id)


class FakeModelService:
    def __init__(self, root: Path, installed: set[str]) -> None:
        self.registry = ModelRegistry()
        self.repository = FakeInstallationRepository(installed)
        self.root = root
        self.acquire_calls: list[str] = []
        self.release_calls: list[tuple[str, bool]] = []
        for model_id in installed:
            model = self.registry.get(model_id)
            self.install_path(model).mkdir(parents=True, exist_ok=True)

    def install_path(self, model):
        return self.root / model.install_relative_path

    def acquire_model(self, model_id: str, *, loaded: bool = True):
        self.acquire_calls.append(model_id)
        return self.repository.get(model_id) or ModelInstallation(model_id=model_id)

    def release_model(self, model_id: str, *, unload: bool = False):
        self.release_calls.append((model_id, unload))
        return self.repository.get(model_id) or ModelInstallation(model_id=model_id)


class FakeMediaService:
    def __init__(self, assets: dict[str, MediaAsset]) -> None:
        self.assets = assets

    def get_media(self, project_id: str, media_id: str) -> MediaAsset:
        item = self.assets[media_id]
        if item.project_id != project_id:
            raise KeyError(media_id)
        return item


class FakeReadiness:
    def __init__(self, cuda_status: str = "unavailable") -> None:
        self.value = SystemReadiness(cuda_status=cuda_status)

    def detect(self):
        return self.value


class EmptySTTEngine(FakeSTTEngine):
    def transcribe(self, request: TranscriptionRequest) -> STTOutput:
        self.validate_request(request)
        return STTOutput(iter(()), STTTranscriptionInfo(language="en", language_probability=0.9, duration_seconds=1.0))


def make_system(tmp_path: Path, *, language="en", installed=None, engine=None, profile="balanced"):
    installed = installed or {"whisper-small", "whisper-medium"}
    db = SQLiteDatabase(tmp_path / "data" / "app.db")
    db.initialize()
    project_repo = ProjectRepository(db)
    media_repo = MediaRepository(db)
    transcript_repo = TranscriptRepository(db)

    project_root = tmp_path / "Projects" / "demo"
    project_root.mkdir(parents=True)
    project = Project(title="Demo", workflow="video", project_path=str(project_root), project_id="project-1")
    project_repo.create(project)
    source = project_root / "media" / "audio" / "ព័ត៌មាន.wav"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fake audio source")
    asset = MediaAsset(
        asset_id="media-1",
        project_id=project.project_id,
        media_type=MediaType.AUDIO,
        name="ព័ត៌មាន.wav",
        original_path=str(tmp_path / "outside.wav"),
        project_path=str(source),
        file_size=source.stat().st_size,
        duration_ms=4500,
        extension=".wav",
    )
    media_repo.create(asset)

    fake_media = FakeMediaService({asset.asset_id: asset})
    model_service = FakeModelService(tmp_path / "models", installed)
    stt_engine = engine or FakeSTTEngine(language=language)
    manager = STTEngineManager(stt_engine)
    settings = SimpleNamespace(current=SimpleNamespace(performance_profile=profile))
    service = TranscriptionService(
        transcript_repo,
        fake_media,
        model_service,
        manager,
        FakeReadiness(),
        settings,
        TranscriptAnalysisService(),
    )
    return db, project, asset, transcript_repo, model_service, stt_engine, service


def request(asset: MediaAsset, *, language="auto", model_id="whisper-small", **kwargs):
    return TranscriptionRequest(
        project_id=asset.project_id,
        media_id=asset.asset_id,
        model_id=model_id,
        source_path=asset.project_path,
        language=language,
        **kwargs,
    )


def test_phase10_database_migration_tables(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db")
    db.initialize()
    assert db.current_version() == 16
    with db.connect() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"transcripts", "transcript_segments", "transcript_words"} <= tables


def test_seconds_to_ms_and_timestamp_format_are_consistent():
    assert seconds_to_ms(1.2345) == 1234
    assert seconds_to_ms(-1) == 0
    assert format_timestamp_ms(3723004) == "01:02:03.004"
    assert format_timestamp_ms(4820) == "00:04.820"


def test_fake_engine_transcription_persists_language_segments_and_words(tmp_path: Path):
    _, _, asset, repo, _, engine, service = make_system(tmp_path)
    transcript, segments = service.transcribe(request(asset, word_timestamps=True), CancellationToken())
    assert transcript.status_code == "ready"
    assert transcript.detected_language == "en"
    assert transcript.language_probability == pytest.approx(0.99)
    assert len(segments) == 2
    assert segments[0].start_ms == 0 and segments[0].end_ms == 2000
    assert segments[0].words[0].text == "Hello"
    assert engine.transcribe_count == 1
    active = repo.active_for_media(asset.project_id, asset.asset_id)
    assert active and active.transcript_id == transcript.transcript_id
    assert repo.segments(transcript.transcript_id)[1].end_ms == 4500


def test_khmer_language_and_unicode_persist(tmp_path: Path):
    db, _, asset, repo, *_rest, service = make_system(tmp_path, language="km")
    transcript, segments = service.transcribe(request(asset, language="km"))
    assert transcript.detected_language == "km"
    assert "សួស្តី" in segments[0].text
    restarted = TranscriptRepository(db)
    restored = restarted.segments(transcript.transcript_id)
    assert "សួស្តី" in restored[0].text


def test_no_speech_is_ready_empty_transcript(tmp_path: Path):
    _, _, asset, repo, _, _, service = make_system(tmp_path, engine=EmptySTTEngine())
    transcript, segments = service.transcribe(request(asset))
    assert transcript.status_code == "ready"
    assert segments == []
    assert repo.active_for_media(asset.project_id, asset.asset_id) is not None


def test_generator_is_consumed_and_progress_reaches_end(tmp_path: Path):
    _, _, asset, _, _, engine, service = make_system(tmp_path)
    progress = []
    service.transcribe(request(asset), progress=lambda *args: progress.append(args))
    assert engine.transcribe_count == 1
    assert any(item[0] == "transcribing" for item in progress)
    assert progress[-1][0] == "completed" and progress[-1][1] == 1.0


def test_cancellation_discards_incomplete_transcript(tmp_path: Path):
    _, _, asset, repo, _, engine, service = make_system(tmp_path)
    engine.cancel_after_segments = 1
    with pytest.raises(STTCancelled):
        service.transcribe(request(asset))
    assert repo.list_for_media(asset.project_id, asset.asset_id) == []


def test_model_not_installed_does_not_download(tmp_path: Path):
    _, _, asset, _, _, _, service = make_system(tmp_path, installed={"whisper-small"})
    with pytest.raises(STTModelNotInstalled):
        service.transcribe(request(asset, model_id="whisper-medium"))


def test_model_recommendation_respects_performance_profile(tmp_path: Path):
    *_, service = make_system(tmp_path, installed={"whisper-small", "whisper-medium", "whisper-large-v3"}, profile=PerformanceProfile.LOW_MEMORY.value)
    assert service.recommended_model_id() == "whisper-small"
    service.settings.current.performance_profile = PerformanceProfile.BALANCED.value
    assert service.recommended_model_id() == "whisper-medium"
    service.settings.current.performance_profile = PerformanceProfile.MAXIMUM_QUALITY.value
    assert service.recommended_model_id() == "whisper-large-v3"


def test_cpu_and_cuda_compute_selection(tmp_path: Path, monkeypatch):
    *_, service = make_system(tmp_path)
    monkeypatch.setattr(service, "_supported_compute_types", lambda device: {"int8", "float32"} if device == "cpu" else {"float16", "int8_float16"})
    assert service.resolve_compute_type("auto", "cpu") == "int8"
    assert service.resolve_compute_type("float16", "cuda") == "float16"
    assert service.resolve_device("cuda") == "cuda"


def test_transcript_edit_reset_search_and_utf8_export(tmp_path: Path):
    _, _, asset, repo, _, _, service = make_system(tmp_path, language="km")
    transcript, segments = service.transcribe(request(asset, language="km"))
    first = segments[0]
    service.update_segment(asset.project_id, transcript.transcript_id, first.segment_id, "កែសម្រួល")
    edited = repo.segments(transcript.transcript_id)[0]
    assert edited.edited is True and edited.text == "កែសម្រួល"
    assert service.search(asset.project_id, transcript.transcript_id, "កែ")[0].segment_id == first.segment_id
    service.reset_segment(asset.project_id, transcript.transcript_id, first.segment_id)
    restored = repo.segments(transcript.transcript_id)[0]
    assert restored.edited is False and restored.text == restored.original_text
    destination = tmp_path / "ចម្លង.txt"
    service.export_txt(asset.project_id, transcript.transcript_id, destination)
    text = destination.read_text(encoding="utf-8")
    assert "[00:00.000 - 00:02.000]" in text
    assert "សួស្តី" in text


def test_source_fingerprint_marks_transcript_outdated_without_deleting(tmp_path: Path):
    _, _, asset, repo, _, _, service = make_system(tmp_path)
    transcript, _ = service.transcribe(request(asset))
    path = Path(asset.project_path)
    path.write_bytes(b"changed media bytes are different")
    os.utime(path, None)
    active, segments = service.get_active(asset.project_id, asset.asset_id)
    assert active and active.status_code == TranscriptStatus.OUTDATED.value
    assert segments
    assert repo.get(transcript.transcript_id) is not None


def test_failed_regeneration_keeps_previous_active_transcript(tmp_path: Path):
    _, _, asset, repo, _, engine, service = make_system(tmp_path)
    first, _ = service.transcribe(request(asset))
    engine.cancel_after_segments = 0
    with pytest.raises(STTCancelled):
        service.transcribe(request(asset))
    active = repo.active_for_media(asset.project_id, asset.asset_id)
    assert active and active.transcript_id == first.transcript_id


def test_successful_regeneration_creates_new_active_and_keeps_history(tmp_path: Path):
    _, _, asset, repo, _, _, service = make_system(tmp_path)
    first, _ = service.transcribe(request(asset))
    second, _ = service.transcribe(request(asset, language="en"))
    history = repo.list_for_media(asset.project_id, asset.asset_id)
    assert len(history) == 2
    assert repo.active_for_media(asset.project_id, asset.asset_id).transcript_id == second.transcript_id
    assert repo.get(first.transcript_id) is not None


def test_delete_transcript_never_removes_source_media(tmp_path: Path):
    _, _, asset, repo, _, _, service = make_system(tmp_path)
    transcript, _ = service.transcribe(request(asset))
    source = Path(asset.project_path)
    service.delete(asset.project_id, transcript.transcript_id)
    assert source.is_file()
    assert repo.get(transcript.transcript_id) is None


def test_duplicate_project_transcripts_get_new_ids_and_media_mapping(tmp_path: Path):
    _, project, asset, repo, _, _, service = make_system(tmp_path)
    source_transcript, source_segments = service.transcribe(request(asset))
    target_root = tmp_path / "Projects" / "copy"
    target_root.mkdir(parents=True)
    target_asset_path = target_root / "media" / "audio" / "copy.wav"
    target_asset_path.parent.mkdir(parents=True)
    target_asset_path.write_bytes(Path(asset.project_path).read_bytes())
    target_project = Project(title="Copy", workflow="video", project_path=str(target_root), project_id="project-2")
    ProjectRepository(repo.database).create(target_project)
    target_asset = MediaAsset(
        asset_id="media-2", project_id=target_project.project_id, media_type="audio", name="copy.wav",
        original_path=asset.original_path, project_path=str(target_asset_path), file_size=target_asset_path.stat().st_size,
        duration_ms=4500, extension=".wav"
    )
    MediaRepository(repo.database).create(target_asset)
    service.media_service.assets[target_asset.asset_id] = target_asset
    assert service.duplicate_project_transcripts(project.project_id, target_project.project_id, {asset.asset_id: target_asset.asset_id}) == 1
    copied = repo.active_for_media(target_project.project_id, target_asset.asset_id)
    assert copied and copied.transcript_id != source_transcript.transcript_id
    copied_segments = repo.segments(copied.transcript_id)
    assert copied_segments[0].segment_id != source_segments[0].segment_id
    assert copied.media_id == target_asset.asset_id


def test_ai_resource_manager_unloads_idle_other_engine_and_blocks_busy():
    calls = []
    manager = AIResourceManager()
    busy = {"tts": False}
    manager.register("tts", lambda: calls.append("unload-tts"), lambda: busy["tts"])
    manager.register("stt", lambda: calls.append("unload-stt"), lambda: False)
    manager.prepare("stt", "cuda")
    assert calls == ["unload-tts"]
    busy["tts"] = True
    with pytest.raises(AIResourceConflict):
        manager.prepare("stt", "cuda")


def test_transcription_service_maps_resource_conflict(tmp_path: Path):
    _, _, asset, _, _, _, service = make_system(tmp_path)
    manager = AIResourceManager()
    manager.register("tts", lambda: None, lambda: True)
    manager.register("stt", service.unload, lambda: False)
    service.resource_manager = manager
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(service, "_supported_compute_types", lambda device: {"float16"} if device == "cuda" else {"int8"})
    try:
        with pytest.raises(STTResourceConflict):
            service.load("whisper-small", device="cuda", compute_type="float16")
    finally:
        monkeypatch.undo()


def test_request_defaults_keep_word_timestamps_and_vad_enabled(tmp_path: Path):
    _, _, asset, _, _, engine, service = make_system(tmp_path)
    req = request(asset)
    assert req.word_timestamps is True
    assert req.vad_enabled is True
    caps = engine.get_capabilities()
    assert caps.supports_word_timestamps is True
    assert caps.supports_vad is True
    assert caps.supports_language_detection is True


def test_previous_transcript_can_be_reactivated_after_regeneration(tmp_path: Path):
    _, _, asset, repo, _, _, service = make_system(tmp_path)
    first, _ = service.transcribe(request(asset))
    second, _ = service.transcribe(request(asset, language="en"))
    assert repo.active_for_media(asset.project_id, asset.asset_id).transcript_id == second.transcript_id
    service.set_active(asset.project_id, asset.asset_id, first.transcript_id)
    assert repo.active_for_media(asset.project_id, asset.asset_id).transcript_id == first.transcript_id


def test_project_deletion_cascades_transcript_rows_only(tmp_path: Path):
    _, project, asset, repo, _, _, service = make_system(tmp_path)
    transcript, segments = service.transcribe(request(asset))
    assert segments and segments[0].words
    source = Path(asset.project_path)
    ProjectRepository(repo.database).delete(project.project_id)
    assert repo.get(transcript.transcript_id) is None
    # Repository-level cascade only removes project-owned database rows; filesystem
    # deletion is still coordinated by ProjectService and never touches originals.
    assert source.is_file()

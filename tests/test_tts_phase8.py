from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from domain.generated_audio import GeneratedAudio
from domain.model_installation import ModelInstallation, ModelInstallStatus
from domain.settings import PerformanceProfile
from domain.system_readiness import SystemReadiness
from domain.voice_config import VoiceConfig
from engines.model_registry import ModelRegistry
from engines.tts.errors import (
    TTSCancelled,
    TTSInvalidRequest,
    TTSModelNotInstalled,
    TTSOutOfMemory,
)
from engines.tts.fake_engine import FakeTTSEngine
from engines.tts.manager import TTSEngineManager
from engines.tts.types import TTSEngineState, TTSRequest
from engines.tts.voxcpm2_engine import CFG_MAX, CFG_MIN, VoxCPM2Engine
from services.narration_service import NarrationService, narration_text_hash
from services.project_service import ProjectService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from services.tts_chunking_service import TTSChunkingService
from services.tts_service import TTSService
from storage.database import SQLiteDatabase
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository
from workers.cancellation import CancellationToken
from workers.tts_worker import TTSWorker


class FakeTTSService:
    def __init__(self) -> None:
        self.engine = FakeTTSEngine()
        self.loaded_device = ""

    def load(self, device: str = "auto") -> str:
        self.loaded_device = device
        self.engine.load(device)
        return device

    def unload(self) -> None:
        self.engine.unload()

    def generate(self, request: TTSRequest, cancellation: CancellationToken | None = None):
        return self.engine.generate(request, cancellation)

    @staticmethod
    def validate_reference(path: str | Path) -> Path:
        value = Path(path)
        if not value.is_file() or value.stat().st_size <= 0:
            raise TTSInvalidRequest("Invalid reference")
        return value


@pytest.fixture
def narration_system(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "runtime" / "app.db")
    db.initialize()
    project_repo = ProjectRepository(db)
    project_service = ProjectService(project_repo, tmp_path / "projects")
    script_repo = ScriptRepository(db)
    script_service = ScriptService(script_repo, project_repo, ScriptAnalysisService())
    project_service.set_script_service(script_service)
    generated_repo = GeneratedAudioRepository(db)
    fake_tts = FakeTTSService()
    narration = NarrationService(
        generated_repo,
        project_repo,
        script_service,
        fake_tts,  # type: ignore[arg-type]
        TTSChunkingService(max_characters=140),
    )
    project_service.set_narration_service(narration)
    project = project_service.create_project("Narration Test", "video", "en", "16:9", 30)
    script, sections = script_service.load_or_create(project.project_id)
    sections[0].content = "A clear opening sentence."
    sections[1].content = "This is the main narration body with enough detail for a useful voice test."
    sections[2].content = "Thanks for listening."
    for section in sections:
        script_service.save_section(project.project_id, section)
    return db, project_repo, project_service, script_service, generated_repo, fake_tts, narration, project


def test_phase8_database_migration_and_table(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db")
    db.initialize()
    assert db.current_version() == 9
    with db.connect() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        indexes = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "generated_audio" in tables
    assert "idx_generated_audio_project_created" in indexes


def test_voice_config_keeps_seed_and_reference_metadata():
    config = VoiceConfig(mode="reference", reference_audio_path="សំឡេង.wav", consent_confirmed=True, seed=42)
    payload = config.to_dict()
    assert payload["mode"] == "reference"
    assert payload["seed"] == 42
    assert payload["referenceAudioPath"] == "សំឡេង.wav"


def test_voxcpm_capabilities_include_english_khmer_cpu_cuda(tmp_path: Path):
    engine = VoxCPM2Engine(tmp_path / "model")
    caps = engine.get_capabilities()
    assert caps.supports_voice_design is True
    assert caps.supports_reference_voice is True
    assert caps.supports_cpu is True
    assert caps.supports_cuda is True
    assert {"en", "km"} <= set(caps.supported_languages)
    assert caps.output_sample_rate == 48_000


def test_voxcpm_request_validation_bounds_and_design(tmp_path: Path):
    engine = VoxCPM2Engine(tmp_path / "model")
    request = TTSRequest("p", "Hello", "en", tmp_path / "out.wav")
    request.voice_config.cfg_value = CFG_MIN - 0.01
    with pytest.raises(TTSInvalidRequest):
        engine.validate_request(request)
    request.voice_config.cfg_value = CFG_MAX
    request.voice_config.inference_timesteps = 0
    with pytest.raises(TTSInvalidRequest):
        engine.validate_request(request)
    request.voice_config.inference_timesteps = 10
    request.voice_config.mode = "designed"
    with pytest.raises(TTSInvalidRequest):
        engine.validate_request(request)
    request.voice_config.description = "Warm narrator"
    engine.validate_request(request)


def test_reference_mode_requires_consent_and_existing_file(tmp_path: Path):
    engine = VoxCPM2Engine(tmp_path / "model")
    ref = tmp_path / "authorized.wav"
    ref.write_bytes(b"test")
    request = TTSRequest("p", "Hello", "en", tmp_path / "out.wav")
    request.voice_config = VoiceConfig(mode="reference", reference_audio_path=str(ref), consent_confirmed=False)
    with pytest.raises(TTSInvalidRequest):
        engine.validate_request(request)
    request.voice_config.consent_confirmed = True
    engine.validate_request(request)


def test_chunking_english_respects_sentences():
    chunks = TTSChunkingService(max_characters=120).chunk_text(
        "First sentence. Second sentence! Third sentence?", "en"
    )
    assert chunks
    assert "First sentence." in chunks[0].text
    assert all(chunk.order == index for index, chunk in enumerate(chunks))


def test_chunking_khmer_uses_khmer_sentence_punctuation():
    text = "សួស្តី។ ថ្ងៃនេះយើងនិយាយអំពីបច្ចេកវិទ្យា។ នេះជាការសាកល្បង!"
    chunks = TTSChunkingService(max_characters=120).chunk_text(text, "km")
    assert chunks
    assert "។" in chunks[0].text
    assert "សួស្តី" in " ".join(item.text for item in chunks)


def test_full_narration_fake_engine_persists_valid_wav(narration_system):
    _, _, _, _, repo, fake_tts, narration, project = narration_system
    generated = narration.generate_full(project.project_id, VoiceConfig(device="cpu"))
    assert generated.active is True
    assert generated.status == "completed"
    assert Path(generated.file_path).is_file()
    assert generated.duration_ms > 0
    assert generated.sample_rate == fake_tts.engine.sample_rate
    assert repo.active_for_project(project.project_id).generated_audio_id == generated.generated_audio_id


def test_section_generation_references_section_and_is_not_active(narration_system):
    _, _, _, script_service, repo, _, narration, project = narration_system
    _, sections = script_service.load_or_create(project.project_id)
    generated = narration.generate_section(project.project_id, sections[0].section_id, VoiceConfig())
    assert generated.section_id == sections[0].section_id
    assert generated.active is False
    assert repo.get(generated.generated_audio_id) is not None


def test_generated_narration_becomes_out_of_date_after_script_change(narration_system):
    _, _, _, script_service, _, _, narration, project = narration_system
    generated = narration.generate_full(project.project_id, VoiceConfig())
    assert narration.narration_is_current(project.project_id, generated) is True
    _, sections = script_service.load_or_create(project.project_id)
    sections[1].content += " A new sentence changes the narration hash."
    script_service.save_section(project.project_id, sections[1])
    assert narration.narration_is_current(project.project_id, generated) is False
    assert Path(generated.file_path).exists()


def test_disabled_section_excluded_from_hash_and_generation(narration_system):
    _, _, _, script_service, _, _, narration, project = narration_system
    _, sections = script_service.load_or_create(project.project_id)
    script_service.set_section_enabled(project.project_id, sections[1].section_id, False)
    script, loaded = script_service.load_or_create(project.project_id)
    expected = narration_text_hash(script.language, loaded)
    generated = narration.generate_full(project.project_id, VoiceConfig())
    assert generated.text_hash == expected


def test_worker_cancellation_cleans_partial_output(narration_system):
    _, _, _, _, repo, _, narration, project = narration_system
    token = CancellationToken()
    token.cancel()
    worker = TTSWorker(narration, project.project_id, VoiceConfig(), cancellation=token)
    with pytest.raises(TTSCancelled):
        worker.run()
    assert repo.list_for_project(project.project_id) == []
    narration_dir = Path(project.project_path) / "audio" / "narration"
    assert not narration_dir.exists() or not list(narration_dir.glob("*.wav"))


def test_preview_generation_is_project_cache_only(narration_system):
    _, _, _, _, _, _, narration, project = narration_system
    path = narration.generate_preview(project.project_id, "Short preview", "en", VoiceConfig())
    assert path.is_file()
    assert (Path(project.project_path) / "cache" / "tts" / "previews") in path.parents


def test_reference_audio_is_copied_without_changing_original(narration_system, tmp_path: Path):
    _, _, _, _, _, _, narration, project = narration_system
    source = tmp_path / "សំឡេង reference.wav"
    source.write_bytes(b"authorized-reference")
    before = source.read_bytes()
    managed = narration.prepare_reference_audio(project.project_id, source)
    assert managed.is_file()
    assert managed != source
    assert managed.read_bytes() == before
    assert source.read_bytes() == before
    assert (Path(project.project_path) / "audio" / "references") in managed.parents


def test_generated_audio_delete_guard_keeps_outside_file(narration_system, tmp_path: Path):
    _, _, _, _, repo, _, narration, project = narration_system
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"outside")
    item = GeneratedAudio(
        project_id=project.project_id,
        engine="fake",
        model_id="voxcpm2",
        language="en",
        voice_mode="default",
        text_hash="x",
        file_path=str(outside),
    )
    repo.create(item)
    with pytest.raises(TTSInvalidRequest):
        narration.delete_generated(project.project_id, item.generated_audio_id)
    assert outside.exists()
    assert repo.get(item.generated_audio_id) is not None


def test_project_duplication_copies_narration_with_new_ids(narration_system):
    _, _, project_service, _, repo, _, narration, project = narration_system
    original = narration.generate_full(project.project_id, VoiceConfig())
    duplicate = project_service.duplicate_project(project.project_id)
    copied = repo.list_for_project(duplicate.project_id)
    assert len(copied) == 1
    assert copied[0].generated_audio_id != original.generated_audio_id
    assert Path(copied[0].file_path).is_file()
    assert Path(copied[0].file_path).resolve().is_relative_to(Path(duplicate.project_path).resolve())
    assert Path(original.file_path).exists()
    duplicate_narration = Path(duplicate.project_path) / "audio" / "narration"
    assert len(list(duplicate_narration.glob("*.wav"))) == 1
    assert narration.narration_is_current(duplicate.project_id, copied[0]) is True


def test_project_delete_cleans_generated_rows_and_keeps_other_project(narration_system):
    _, project_repo, project_service, _, repo, _, narration, project = narration_system
    generated = narration.generate_full(project.project_id, VoiceConfig())
    other = project_service.create_project("Other", "video", "en", "16:9", 30)
    project_service.delete_project(project.project_id)
    assert repo.get(generated.generated_audio_id) is None
    assert project_repo.get_by_id(other.project_id) is not None


class _InstallationRepo:
    def __init__(self, item: ModelInstallation | None):
        self.item = item

    def get(self, model_id: str):
        return self.item

    def upsert(self, item):
        self.item = item
        return item


class _ModelService:
    def __init__(self, path: Path, installed: bool = True):
        self.registry = ModelRegistry()
        self.repository = _InstallationRepo(
            ModelInstallation(model_id="voxcpm2", installed=True, status=ModelInstallStatus.INSTALLED)
            if installed
            else None
        )
        self.path = path
        self.in_use = 0

    def install_path(self, model):
        return self.path

    def acquire_model(self, model_id: str, loaded: bool = True):
        self.in_use += 1
        return self.repository.item

    def release_model(self, model_id: str, unload: bool = False):
        self.in_use = max(0, self.in_use - 1)
        return self.repository.item


class _Readiness:
    def __init__(self, cuda: str = "unavailable", vram: int | None = None):
        self.value = SystemReadiness(cuda_status=cuda, gpu_memory_available=vram)

    def detect(self):
        return self.value


class _Settings:
    class Current:
        performance_profile = PerformanceProfile.AUTO.value

    current = Current()


def test_tts_service_model_missing(tmp_path: Path):
    manager = TTSEngineManager()
    manager.register("voxcpm2", FakeTTSEngine())
    service = TTSService(manager, _ModelService(tmp_path / "missing", installed=False), _Readiness(), _Settings())  # type: ignore[arg-type]
    with pytest.raises(TTSModelNotInstalled):
        service.ensure_model_ready()


def test_tts_service_auto_device_cpu_and_cuda(tmp_path: Path):
    model_path = tmp_path / "model"
    model_path.mkdir()
    manager = TTSEngineManager(); manager.register("voxcpm2", FakeTTSEngine())
    model_service = _ModelService(model_path)
    cpu = TTSService(manager, model_service, _Readiness("unavailable"), _Settings())  # type: ignore[arg-type]
    assert cpu.resolve_device("auto") == "cpu"
    cuda = TTSService(manager, model_service, _Readiness("available", 12 * 1024**3), _Settings())  # type: ignore[arg-type]
    assert cuda.resolve_device("auto") == "cuda"
    assert cuda.resolve_device("cpu") == "cpu"


def test_tts_service_reuses_loaded_engine_and_releases_in_use(tmp_path: Path):
    model_path = tmp_path / "model"; model_path.mkdir()
    engine = FakeTTSEngine()
    manager = TTSEngineManager(); manager.register("voxcpm2", engine)
    model_service = _ModelService(model_path)
    service = TTSService(manager, model_service, _Readiness(), _Settings())  # type: ignore[arg-type]
    output1 = tmp_path / "one.wav"; output2 = tmp_path / "two.wav"
    service.generate(TTSRequest("p", "Hello", "en", output1, VoiceConfig(device="cpu")))
    service.generate(TTSRequest("p", "Again", "en", output2, VoiceConfig(device="cpu")))
    assert engine.load_count == 1
    assert model_service.in_use == 1  # one persistent load ownership remains
    service.unload()
    assert model_service.in_use == 0
    assert engine.is_loaded() is False


def test_fake_engine_preserves_khmer_unicode_path(tmp_path: Path):
    engine = FakeTTSEngine()
    output = tmp_path / "សំឡេង ព័ត៌មាន.wav"
    result = engine.generate(TTSRequest("p", "សួស្តី! ថ្ងៃនេះយើងនិយាយអំពីបច្ចេកវិទ្យា។", "km", output))
    assert result.output_path == output
    assert output.is_file()
    assert result.duration_ms > 0


def test_text_hash_ignores_storage_ids_but_tracks_order_and_text():
    from services.narration_service import stable_text_hash
    first = stable_text_hash("en", [(0, "section-a", "Hello"), (1, "section-b", "World")])
    duplicated = stable_text_hash("en", [(0, "new-a", "Hello"), (1, "new-b", "World")])
    changed = stable_text_hash("en", [(0, "new-a", "Hello changed"), (1, "new-b", "World")])
    assert first == duplicated
    assert first != changed


def test_voxcpm_oom_is_mapped_to_typed_error(tmp_path: Path):
    class OOMModel:
        class Inner:
            sample_rate = 48000
        tts_model = Inner()
        def generate(self, **kwargs):
            raise RuntimeError("CUDA out of memory")

    engine = VoxCPM2Engine(tmp_path / "model")
    engine._model = OOMModel()
    engine.state = TTSEngineState.LOADED
    request = TTSRequest("p", "Hello", "en", tmp_path / "out.wav")
    with pytest.raises(TTSOutOfMemory):
        engine.generate(request)
    assert not (tmp_path / "out.wav").exists()

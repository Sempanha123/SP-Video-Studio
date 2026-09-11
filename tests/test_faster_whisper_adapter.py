from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from engines.stt.errors import STTInvalidRequest, STTOutOfMemory, STTUnsupportedDevice
from engines.stt.faster_whisper_engine import FasterWhisperEngine
from engines.stt.types import TranscriptionRequest


class FakeWhisperModel:
    instances = []

    def __init__(self, model_path, **kwargs):
        self.model_path = model_path
        self.kwargs = kwargs
        self.calls = []
        type(self).instances.append(self)

    def transcribe(self, path, **kwargs):
        self.calls.append((path, kwargs))
        word = SimpleNamespace(start=0.1, end=0.7, word=" Hello", probability=0.97)
        segment = SimpleNamespace(
            start=0.0,
            end=1.25,
            text=" Hello world.",
            avg_logprob=-0.1,
            no_speech_prob=0.01,
            temperature=0.0,
            words=[word],
        )
        info = SimpleNamespace(
            language="en",
            language_probability=0.98,
            duration=1.25,
            duration_after_vad=1.1,
        )
        return iter([segment]), info


class FakeBatchPipeline:
    instances = []

    def __init__(self, model):
        self.model = model
        self.calls = []
        type(self).instances.append(self)

    def transcribe(self, path, batch_size, **kwargs):
        self.calls.append((path, batch_size, kwargs))
        return self.model.transcribe(path, **kwargs)


def _request(media: Path, *, batch=False, **kwargs):
    values = {
        "project_id": "p1",
        "media_id": "m1",
        "model_id": "whisper-small",
        "source_path": media,
        "language": "auto",
        "batch_mode": batch,
    }
    values.update(kwargs)
    return TranscriptionRequest(**values)


def _install_fake_runtime(monkeypatch):
    module = SimpleNamespace(WhisperModel=FakeWhisperModel, BatchedInferencePipeline=FakeBatchPipeline)
    monkeypatch.setattr(FasterWhisperEngine, "is_available", lambda self: True)
    monkeypatch.setattr(
        "engines.stt.faster_whisper_engine.importlib.import_module",
        lambda name: module if name == "faster_whisper" else (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )


def test_adapter_loads_local_model_only_and_forwards_current_api_options(tmp_path: Path, monkeypatch):
    _install_fake_runtime(monkeypatch)
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    media = tmp_path / "clip.wav"
    media.write_bytes(b"fixture")
    engine = FasterWhisperEngine()
    engine.load(model_path=str(model_dir), device="cpu", compute_type="int8")

    loaded = FakeWhisperModel.instances[-1]
    assert loaded.kwargs == {"device": "cpu", "compute_type": "int8", "local_files_only": True}

    output = engine.transcribe(
        _request(
            media,
            word_timestamps=True,
            vad_enabled=True,
            vad_settings={"min_silence_duration_ms": 500},
            initial_prompt="SP Video Studio",
            hotwords="OpenAI, Cambodia",
            beam_size=5,
        )
    )
    segments = list(output.segments)
    assert len(segments) == 1
    assert segments[0].words[0].text == " Hello"
    assert output.info.language == "en"
    _, forwarded = loaded.calls[-1]
    assert forwarded["task"] == "transcribe"
    assert forwarded["language"] is None
    assert forwarded["word_timestamps"] is True
    assert forwarded["vad_filter"] is True
    assert forwarded["vad_parameters"]["min_silence_duration_ms"] == 500
    assert forwarded["initial_prompt"] == "SP Video Studio"
    assert forwarded["hotwords"] == "OpenAI, Cambodia"


def test_adapter_batched_pipeline_uses_requested_batch_size(tmp_path: Path, monkeypatch):
    _install_fake_runtime(monkeypatch)
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    media = tmp_path / "clip.wav"
    media.write_bytes(b"fixture")
    engine = FasterWhisperEngine()
    engine.load(model_path=str(model_dir), device="cuda", compute_type="float16", batch_mode=True)
    output = engine.transcribe(_request(media, batch=True, batch_size=4))
    assert len(list(output.segments)) == 1
    pipeline = FakeBatchPipeline.instances[-1]
    assert pipeline.calls[-1][1] == 4


def test_adapter_reuses_identical_loaded_configuration(tmp_path: Path, monkeypatch):
    _install_fake_runtime(monkeypatch)
    FakeWhisperModel.instances.clear()
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    engine = FasterWhisperEngine()
    engine.load(model_path=str(model_dir), device="cpu", compute_type="int8")
    engine.load(model_path=str(model_dir), device="cpu", compute_type="int8")
    assert len(FakeWhisperModel.instances) == 1
    engine.unload()
    assert engine.is_loaded() is False


def test_adapter_validates_beam_batch_and_language(tmp_path: Path):
    media = tmp_path / "clip.wav"
    media.write_bytes(b"fixture")
    engine = FasterWhisperEngine()
    with pytest.raises(STTInvalidRequest):
        engine.validate_request(_request(media, beam_size=0))
    with pytest.raises(STTInvalidRequest):
        engine.validate_request(_request(media, batch_size=0))
    with pytest.raises(STTInvalidRequest):
        engine.validate_request(_request(media, language="xx"))


def test_adapter_maps_cuda_runtime_and_oom_errors():
    assert isinstance(FasterWhisperEngine._map_exception(RuntimeError("CUDA out of memory")), STTOutOfMemory)
    mapped = FasterWhisperEngine._map_exception(RuntimeError("cuDNN library not found for CUDA"))
    assert isinstance(mapped, STTUnsupportedDevice)

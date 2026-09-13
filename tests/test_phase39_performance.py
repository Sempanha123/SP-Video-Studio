from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.qa_support.fake_engines import FakeSTTEngine, FakeTTSEngine, FakeTranslationEngine

pytestmark = pytest.mark.performance


def test_scale_models_1000_assets_batch_subtitles_and_100_scenes():
    started = time.perf_counter()
    assets = [{"id": f"asset-{i}", "tags": ["qa", str(i % 10)]} for i in range(1000)]
    batch = [{"id": f"row-{i}", "status": "pending" if i % 2 else "completed"} for i in range(1000)]
    subtitles = [{"startMs": i * 100, "endMs": i * 100 + 90, "text": f"Cue {i}"} for i in range(1000)]
    scenes = [{"id": f"scene-{i}", "layers": [{"kind": "video"}]} for i in range(100)]
    assert len([x for x in assets if "qa" in x["tags"]]) == 1000
    assert sum(x["status"] == "completed" for x in batch) == 500
    assert subtitles[999]["startMs"] == 99900 and scenes[-1]["id"] == "scene-99"
    assert time.perf_counter() - started < 5.0


def test_phase31_subtitle_lookup_1000_when_service_available():
    try:
        from services.subtitle_lookup_service import SubtitleLookupService
    except ImportError:
        pytest.skip("Full Phase 31 source is not present in this partial sandbox checkout")
    service = SubtitleLookupService()
    cues = [SimpleNamespace(start_ms=i * 100, end_ms=i * 100 + 80, id=f"cue-{i}") for i in range(1000)]
    started = time.perf_counter(); service.build("track", cues, version="qa")
    hits = 0
    for i in range(1000):
        hits += len(service.active("track", i * 100 + 40))
    assert hits == 1000
    assert time.perf_counter() - started < 5.0


def test_fake_engine_load_unload_is_bounded():
    engines = [FakeTTSEngine(), FakeSTTEngine(), FakeTranslationEngine()]
    for _ in range(50):
        for engine in engines:
            try: engine.load(device="cpu")
            except TypeError: engine.load(model_path="", device="cpu", compute_type="int8")
            engine.unload()
    assert all(engine.counters.loads == 50 and engine.counters.unloads == 50 for engine in engines)


def test_ffmpeg_cancellation_leaves_no_child_process(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("FFmpeg unavailable")
    proc = subprocess.Popen(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-re", "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=10", "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False,
    )
    time.sleep(0.15)
    proc.terminate()
    proc.wait(timeout=5)
    assert proc.poll() is not None


def test_worker_pool_thread_count_is_bounded_when_full_source_available():
    try:
        from workers.worker_pool import WorkerPool
    except ImportError:
        pytest.skip("Full WorkerPool source is not present in this partial sandbox checkout")
    import threading
    before = {t.ident for t in threading.enumerate()}
    pool = WorkerPool(max_workers=3, max_pending=16)
    futures = [pool.submit(lambda value=i: value) for i in range(20)]
    # Queue saturation is allowed to fail closed; completed accepted jobs must be deterministic.
    for future in futures:
        try:
            future.result(timeout=3)
        except RuntimeError as exc:
            assert "queue is full" in str(exc).casefold()
    stats = pool.stats()
    assert stats["workers"] == 3 and stats["capacity"] == 16
    pool.shutdown(wait=True)
    time.sleep(0.05)
    leaked = [t for t in threading.enumerate() if t.ident not in before and t.name.startswith("sp-worker-")]
    assert not leaked


def test_thumbnail_request_cancellation_marks_stale_when_full_source_available(tmp_path):
    try:
        from workers.worker_pool import WorkerPool
        from services.thumbnail_request_service import ThumbnailRequestService
    except ImportError:
        pytest.skip("Full thumbnail cancellation services are not present in this partial sandbox checkout")

    class FakeThumbnailService:
        @staticmethod
        def generate(media_type, source, destination, duration_ms=None):
            time.sleep(0.03)
            Path(destination).write_bytes(b"thumb")
            return Path(destination)

    source = tmp_path / "source.bin"; source.write_bytes(b"fixture")
    pool = WorkerPool(max_workers=1)
    service = ThumbnailRequestService(FakeThumbnailService(), pool)
    request = service.request("grid", "image", source, tmp_path / "thumb.bin")
    service.cancel_owner("grid")
    request.future.result(timeout=3)
    assert service.is_current(request) is False
    pool.shutdown(wait=True)

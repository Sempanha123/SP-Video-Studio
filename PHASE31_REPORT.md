# PHASE 31 STATUS

Completed:

* Implemented Phase 31 only as a performance layer over Phase 30; no Phase 32 work was started.
* Added measured optimizations for Asset search, subtitle playback lookup, Batch summaries, FFprobe reuse, waveform reuse, worker scheduling, preview staleness, large-list QML behavior, database indexes, AI resource lifecycle, and performance settings.
* Preserved final render quality and authoritative project/timeline/audio data.

Performance baseline:

* Measured unoptimized hot paths before applying Phase 31 behavior in the reconstructed Phase 30/31 test environment.
* 1,000-asset tag search: 550.746 ms baseline.
* 5,000 subtitle cues × 3,000 playback lookups: 449.754 ms baseline.
* 1,000 Batch-item summary by materializing rows: 9.819 ms baseline.
* Repeated unchanged media metadata inspection conceptually required 20 FFprobe subprocesses before cache reuse.
* Repeated same waveform request conceptually required 10 decodes before Phase 31 dedup/cache reuse.
* Full Windows/PySide6 launch-to-window baseline could not be measured because PySide6 is unavailable in this sandbox.

Startup:

* Retained the existing single QML page Loader and layered Phase 31 runtime so heavy workflow pages are not all instantiated by Phase 31.
* Heavy AI models are not preloaded by Phase 31 startup.
* Asset controller initialization reads a bounded DB page and does not force the library filesystem scan.
* Exact launch-to-usable-window timing is not claimed in this environment.

Project opening:

* No new full-library/media scan is added to project open.
* Existing canonical project records remain lazy; performance services avoid probing/decoding media unless requested.
* Live Qt small/medium/stress project-open timing was not measurable without PySide6.

Lazy loading:

* Existing QML Loader remains the page-instantiation boundary.
* Asset thumbnails are asynchronous and bounded by card source size.
* Waveforms are generated lazily and by requested resolution level.
* AI resources remain job/workflow acquired rather than startup warmed.

Database:

* Added migration 26 performance indexes for hot Asset, Asset usage, Batch, Subtitle, Scene, SpeechBlock and Transcript access paths when those schemas exist.
* Collapsed Asset Library N+1 metadata reads to four bulk SQLite queries.
* Added aggregate Batch summary query and paged item listing.

QML models:

* Asset Grid and Batch Queue remain virtualized with delegate reuse.
* Added Asset incremental load-more behavior and 220 ms search debounce.
* Batch search is debounced and queue refresh is throttled.
* Images use asynchronous bounded source sizes instead of loading full-size card media.

Timeline:

* Timeline clip delegates are filtered to the visible time window plus margin rather than instantiating all offscreen clips.
* Drag persistence remains release-based; Phase 31 adds no mouse-move DB write loop.
* Waveform zoom uses cached density levels rather than regenerating every zoom tick.
* No final-render timing or quality behavior changed.

Preview:

* Added request/version IDs so stale preview result A cannot replace newer preview B.
* Added Auto / Performance / Quality editor preview policies with bounded proxy height/decoder guidance.
* Preview policy never mutates export RenderSettings.

Subtitle performance:

* Added bounded per-track subtitle indexes and active-cue lookup using binary search/cached versioning.
* Measured 5,000 cues × 3,000 lookups: 449.754 ms → 9.186 ms (~49.0× faster).

Thumbnail system:

* Added in-flight thumbnail request deduplication, priorities and owner versioning/stale-result rejection.
* Ten simultaneous identical thumbnail requests generate once in tests.
* Offscreen owner cancellation invalidates the stale request token.

FFprobe caching:

* Added bounded LRU metadata cache keyed by canonical path, size, mtime, expected type and executable.
* Added concurrent in-flight deduplication and explicit invalidation.
* 20 same-file requests now execute one mocked FFprobe subprocess; changed files reprobe.

Waveform system:

* Phase 30 waveform generation now deduplicates concurrent same-key work.
* Added low/medium/high peak-summary levels for Timeline zoom.
* Ten repeated requests decode once and return nine cache hits in benchmark.

Asset Library:

* 1,000-asset tag search measured 550.746 ms → 68.576 ms (~8.0× faster).
* Initial controller page is bounded; Load More expands in chunks.
* Search/filter preserves multilingual Unicode normalization.

Batch Factory:

* Batch summary uses one aggregate query instead of loading all items for counters.
* 1,000-item summary measured 9.819 ms → 0.466 ms (~21.1× faster).
* Queue remains virtualized and UI refresh is throttled/coalesced.

Audio Mixer:

* Phase 30 waveform cache is reused and now deduplicated/multi-resolution.
* Phase 31 does not change the FFmpeg audio mix/final renderer.
* Meter/preview performance policies are bounded at the UI/service layer.

Autosave/recovery:

* Phase 27 incremental normal persistence remains authoritative.
* Phase 31 does not add whole-project serialization to hot interactions.
* Recovery behavior and periodic snapshots are not weakened for speed.

AI model lifecycle:

* Added profile-aware AIResourceManager behavior for heavy resource acquisition/release/reuse.
* Compatible current resources are reused; incompatible inactive heavy resources can be released before acquisition.
* OOM recovery releases inactive resources and retries exactly once.

VoxCPM reuse:

* Resource-manager tests verify repeat acquisition of the same TTS resource does not unload/reload it.
* Real VoxCPM weights are unavailable in this sandbox, so native load/VRAM timings are not claimed.

Whisper lifecycle:

* Heavy STT is treated as an incompatible heavy resource when appropriate and can release inactive TTS under constrained profiles.
* No Whisper preload is added at startup.
* Real faster-whisper weights/runtime lifecycle measurements are not available in this sandbox.

Translation lifecycle:

* Translation remains lazily owned by its existing workflow/provider path.
* Phase 31 adds no startup model warmup and keeps shared heavy-resource coordination available.
* Real local translation model memory timing is not claimed in this environment.

Worker scheduling:

* WorkerPool now uses a bounded priority queue: Interactive / Normal / Background.
* Worker count and pending queue are bounded; saturation fails a Future immediately instead of blocking submitter/UI.
* Runtime active-worker limit can be changed from Settings without rebuilding threads.

Memory management:

* Bounded caches are used for FFprobe and subtitle indexes; worker queue is bounded.
* 20-cycle service stress: thread count 1 → 1 and ~2,096 bytes traced allocation delta after GC; peak traced Python allocation ~303 KB for that synthetic run.
* This does not claim native Qt/decoder/model memory was measured.

Performance profiles:

* Added persisted Auto / Low Memory / Balanced / Maximum Quality profiles.
* Added Auto / Performance / Quality preview modes and advanced worker limit.
* Low Memory reduces editor resource pressure and enables aggressive idle heavy-model release without changing explicitly selected model quality or final render output.

New files:

* `domain/performance.py`
* `services/performance_profile_service.py`
* `services/performance_telemetry_service.py`
* `services/preview_request_service.py`
* `services/subtitle_lookup_service.py`
* `services/thumbnail_request_service.py`
* `app/phase31_runtime.py`
* `storage/migrations/m026_performance_indexes.py`
* `ui/controllers/performance_controller.py`
* `tests/test_phase31_performance.py`
* `docs/performance.md`
* `docs/performance_benchmarks.json`
* `PHASE31_REPORT.md`

Modified files:

* `main.py`
* `pyproject.toml`
* `media/probe.py`
* `services/ai_resource_manager.py`
* `services/asset_search_service.py`
* `services/audio_waveform_service.py`
* `workers/worker_pool.py`
* `storage/migrations/__init__.py`
* `storage/repositories/asset_repository.py`
* `storage/repositories/batch_item_repository.py`
* `ui/controllers/asset_library_controller.py`
* `ui/controllers/batch_controller.py`
* `ui/qml/assets/AssetCard.qml`
* `ui/qml/assets/AssetFilterBar.qml`
* `ui/qml/assets/AssetGrid.qml`
* `ui/qml/assets/AssetLibraryPage.qml`
* `ui/qml/batch/BatchQueue.qml`
* `ui/qml/pages/SettingsPage.qml`
* `ui/qml/timeline/TimelineEditor.qml`
* `ui/qml/timeline/TimelineTrack.qml`
* `README.md`

Tests run:

* Phase 31 focused performance suite: 34/34 passed.
* Phase 22–31 cumulative regression: 319/319 passed.
* Phase 21 Translate & Dub regression: 19/19 passed.
* Python compilation and QML structural/token checks run before packaging.

Startup benchmark:

* Exact process launch → usable QML main shell was not measurable because PySide6/QML runtime is not installed in this sandbox.
* Structural verification confirms the single page Loader, no Phase 31 model warmup, no Asset filesystem scan in controller construction, and lazy heavyweight services.

1,000-asset test:

* Passed bulk-search/no-N+1 test.
* Measured tag search: 550.746 ms baseline → 68.576 ms after Phase 31 (~8.0× faster), returning the same 100 matching rows.

1,000-Batch-item test:

* Passed aggregate-summary test.
* Measured 9.819 ms baseline row materialization/summary → 0.466 ms grouped query (~21.1× faster).
* Queue QML is virtualized/reused and refresh is throttled.

Timeline stress test:

* Verified visible-time-range clip delegate windowing and release-based persistence structurally.
* Final render/timing path remains unchanged.
* Live Qt scroll/zoom FPS cannot be measured in this non-PySide6 sandbox.

1,000-subtitle test:

* Passed indexed lookup with 5,000 cues, exceeding the mandatory 1,000-cue target.
* 3,000 lookups improved from 449.754 ms to 9.186 ms (~49.0× faster).

Thumbnail-dedup test:

* Passed: 10 identical concurrent requests result in one generation call.
* Offscreen/stale owner token test passed.

Timeline-write-coalescing test:

* Passed structural guard: Phase 31 does not persist Timeline movement on content/mouse hot loops; drag persistence remains release-oriented.

Preview-stale-job test:

* Passed: Preview A completing after Preview B is rejected as stale and cannot become current.

Waveform-dedup test:

* Passed concurrent dedup and resolution-level tests.
* 10 repeated same-file requests produced 1 decode + 9 cache hits.

FFprobe-cache test:

* Passed concurrent/repeated dedup, mtime/size invalidation and bounded-cache tests.
* 20 same-file requests produced one mocked subprocess call.

Model-reuse test:

* Passed: compatible TTS resource is reused without reload; incompatible STT resource is released when required.

OOM-recovery test:

* Passed: inactive heavy resource released and operation retried exactly once; no retry loop.

Memory-stability test:

* 20 service open/work/close cycles ended at the original thread count (1 → 1) with ~2 KB traced Python allocation delta after GC.
* Native Qt/GPU/model memory remains a target-machine manual test.

Thread/subprocess leak test:

* WorkerPool bounded/shutdown tests passed and repeated cycle thread count returned to baseline.
* FFprobe dedup reduces subprocess creation; no live orphan-process cancellation test is claimed because real GUI/project shutdown is not available here.

CPU-only test:

* Passed: performance profile/telemetry and worker policies operate without CUDA.
* No Phase 31 optimization makes GPU/CUDA mandatory.

Performance comparison:

* Asset search: ~8.0× faster on measured 1,000-item tag workload.
* Subtitle playback lookup: ~49.0× faster on measured 5,000-cue workload.
* Batch summary: ~21.1× faster on measured 1,000-item workload.
* FFprobe repeat work: 20 calls → 1 subprocess.
* Waveform repeat work: 10 decodes → 1 decode.
* Export quality and final renderer are unchanged.

Known issues:

* PySide6/qmllint are unavailable in the sandbox, so live QML launch/page FPS/object-retention measurements were not possible.
* CUDA, real VoxCPM2, faster-whisper and local translation model weights are unavailable, so GPU/VRAM/native model-lifecycle timings are not claimed.
* The reconstructed test workspace does not contain the complete production media corpus; target-machine benchmarks should be repeated with real 4K/long-form projects.
* Performance policies are conservative editor guidance; they do not attempt to replace OS/native decoder scheduling.

Architecture decisions:

* Optimize measured hot paths rather than rewrite stable architecture.
* Keep final renderer authoritative and unchanged; performance preview is editor-only.
* Keep Timeline/Scene/SpeechBlock/Asset/Batch/Audio models authoritative; add indexes, bulk fetches, bounded caches and request scheduling around them.
* Prefer bounded threads/caches and stale-result rejection over unsafe multiprocessing.
* Correctness/invalidation keys include file size/mtime/version where relevant before cache reuse.
* Keep performance telemetry local; no telemetry upload was added.

Recommended next phase:
Phase 32 — Keyboard Shortcuts and Editing Productivity

Suggested Git commit:
perf: optimize MMO Video Studio for large creator projects

Do not automatically begin Phase 32.

# Phase 31 — Performance Optimization

Phase 31 improves editor responsiveness and resource behavior without changing final render quality, project data semantics, or the established Timeline/Scene/AI architecture. The work was profile-driven: optimize measured hot paths, preserve correctness, and keep caches/work queues bounded.

## Measurement environment and limits

Measurements below were collected in the Phase 31 sandbox with Python `time.perf_counter`, SQLite fixtures, `tracemalloc`, and deterministic mocked subprocess responses where the benchmark is about call-count/deduplication rather than FFmpeg decode speed. The sandbox does **not** provide PySide6/QML runtime profiling, a real Windows desktop compositor, CUDA, or the user's production media library. Therefore launch-to-first-window, live Timeline FPS, Qt object retention, GPU VRAM, and subjective page-open latency are not invented here. Those remain recommended manual measurements on the target Windows machine.

The raw repeatable service measurements are saved in `docs/performance_benchmarks.json`.

## Baseline → Phase 31 measurements

| Workload | Baseline | Phase 31 | Result |
| --- | ---: | ---: | ---: |
| Asset search, 1,000 assets, tag query | 550.746 ms | 68.576 ms | 8.0× faster |
| Subtitle playback lookup, 5,000 cues × 3,000 lookups | 449.754 ms | 9.186 ms | 49.0× faster |
| Batch status/progress summary, 1,000 items | 9.819 ms | 0.466 ms | 21.1× faster |
| Same-file FFprobe inspection ×20 | 20 subprocess calls | 1 subprocess call | 95% subprocess elimination |
| Same waveform request ×10 | 10 decodes | 1 decode + 9 cache hits | 90% decode elimination |

A service-level 20-cycle worker/preview/subtitle-index stress run ended with the same thread count it started with (1 → 1) and ~2 KB of traced allocation delta after GC. This is evidence for the bounded services exercised by the test; it is **not** a claim that native Qt/decoder/model allocations were profiled in this sandbox.

## Startup strategy

The app continues to use the existing QML `Loader` page shell rather than instantiating every heavy workflow page at startup. Phase 31 adds a lightweight performance runtime layer over Phase 30 and keeps model acquisition out of startup. Asset Library initialization loads a bounded first page from SQLite and does not force a filesystem validation scan. Heavy AI models are still lazy.

Target startup sequence remains:

1. create the application shell;
2. load lightweight settings/recent project metadata;
3. show the current page through the existing Loader;
4. perform readiness/background work after the shell is usable;
5. acquire heavy AI/model resources only for a workflow/job that needs them.

Because PySide6 is not installed in the sandbox, process-launch → rendered-main-window time is recorded as **not measured here**, rather than fabricating a number.

## Database optimizations

Migration 26 adds indexes only when the corresponding table/schema exists, keeping older databases safe. Indexed hot paths include Asset ordering/usage, Batch `(batch_id,status,row_index)`, subtitle playback ranges, subtitle word order, Scene project order, SpeechBlock order, and transcript segment time ranges.

The Asset Library's former per-row tags/collections/usage lookup was collapsed into four bulk queries through `AssetRepository.list_with_metadata()`. Search still preserves Unicode NFKC/casefold behavior and the same domain `Asset` objects.

Batch queue summaries use one grouped aggregate query instead of materializing every `BatchItem` simply to calculate counters/progress. Item listing supports bounded pages.

## Asset Library and large lists

The Asset controller exposes an initial bounded page (160 items) and incremental `loadMore`. QML continues to use `GridView` with delegate reuse. Search input is debounced (220 ms), card images request bounded `sourceSize`, and image loading is asynchronous.

The thumbnail request layer deduplicates identical in-flight requests, assigns Interactive/Normal/Background priority, and marks owner requests stale when a card/page moves offscreen. Completed stale work may populate safe cache, but its request token is not accepted as the current UI result.

## Batch Factory

The Batch queue remains virtualized and uses reusable delegates. Search is debounced and status/progress refresh is throttled rather than pushing a model refresh for every worker progress event. Summary counters come from a grouped database query. This avoids loading all 1,000 rows just to repaint queue totals.

The Phase 26 scheduler remains authoritative for execution and checkpointing; Phase 31 does not change output semantics.

## Timeline

Phase 31 keeps Timeline timing/canonical records unchanged. Timeline clip delegates are windowed to the visible project-time range with a small margin rather than rendering every offscreen clip. Dragging remains visual during interaction and persists on release; playhead movement does not add a new hot-loop database write path.

The optimization does not regenerate thumbnails/waveforms on every zoom tick. Phase 30 waveforms are multi-resolution cached summaries, so zoomed-out UI can use low-density peaks.

A live Qt Timeline FPS benchmark cannot be executed in this sandbox. The structural stress test verifies visible-range delegate filtering and no per-mouse-event persistence was introduced.

## Subtitle playback

Playback previously had a full-list active-cue scan in the reconstructed Timeline mapping path. Phase 31 introduces `SubtitleLookupService`, a bounded per-track interval index using binary search/cached track versions. A track index is rebuilt only when the subtitle track version changes.

Measured workload: 5,000 cues and 3,000 playback lookups improved from 449.754 ms to 9.186 ms.

## FFprobe metadata cache

`FFprobeService` now has:

- cache key: canonical path + file size + mtime + expected media type + FFprobe executable;
- bounded LRU entries;
- in-flight deduplication across concurrent requests;
- explicit invalidation;
- automatic reprobe when size/mtime changes.

Ten concurrent requests plus ten subsequent requests for one unchanged file produce one subprocess invocation in the regression test.

## Waveform system

Phase 30 waveform generation remains authoritative. Phase 31 adds concurrent per-cache-key deduplication and low/medium/high summary levels. The file cache remains managed by Phase 29 under the waveform cache category. Missing/deleted cache regenerates on demand.

The same waveform requested ten times decodes once and serves nine cache hits in the benchmark.

## Preview request correctness

`PreviewRequestService` assigns monotonically increasing request versions per owner. If Preview A finishes after the user has requested Preview B, A is rejected as stale. This protects correctness while allowing old work to finish/cancel safely without overwriting the current scene preview.

Performance profiles expose preview-only proxy policies (Auto / Performance / Quality). These policies can reduce temporary preview resolution/effects/decoder count but never modify export `RenderSettings` or the final FFmpeg renderer.

## Worker scheduling

`WorkerPool` is now a bounded priority queue with three classes:

- Interactive — visible thumbnail/current preview work;
- Normal — existing default jobs;
- Background — offscreen metadata/storage-like work.

The number of worker threads and pending jobs is bounded. Queue saturation returns a failed `Future` immediately instead of blocking the UI submitter. A runtime active limit can be adjusted from Settings without recreating threads.

## AI model lifecycle

`AIResourceManager` coordinates heavy resource ownership. It supports profile-aware release, reuse of the currently compatible model, idle release for Low Memory, and one OOM recovery retry after releasing inactive resources. It does not repeatedly retry OOM and does not preload models at startup.

The tests verify that requesting the same TTS resource twice does not unload/reload it and that switching to an incompatible heavy resource releases the inactive one first. The reconstructed environment does not contain real VoxCPM/Whisper/CUDA runtime weights, so native GPU memory measurements are not claimed.

## Performance profiles

Settings > Performance exposes persisted:

- Profile: Auto / Low Memory / Balanced / Maximum Quality;
- Preview Quality: Auto / Performance / Quality;
- Background Worker Limit.

`Auto` uses available RAM/CPU for a conservative effective profile. Low Memory uses fewer workers/preview decoders and permits aggressive idle heavy-model release. Maximum Quality does not change final export quality; it only allows more editor-side resources when available.

## Memory/cache bounds

New in-memory caches are explicitly bounded:

- FFprobe metadata cache: bounded LRU;
- subtitle track indexes: bounded track count;
- worker queue: bounded pending tasks;
- thumbnail requests: current request/version ownership;
- waveform persistent cache: Phase 29 bounded disk policy and multi-resolution keys.

No unbounded thread-per-request or subprocess-per-card design is introduced.

## Final render parity

Phase 31 does not modify `rendering/renderer.py`. Preview performance policies are editor-only. Final render resolution, codec, quality, audio mix, subtitles, effects, and project timing remain authoritative and unchanged.

## Recommended target-machine profiling

On the real Windows deployment, repeat these measurements with production data:

- process launch → usable main window;
- Assets / Timeline / Batch first usable content;
- Timeline scroll/zoom FPS on the 100-scene stress project;
- Qt object counts after 20 page/project open-close cycles;
- RAM/VRAM before/after VoxCPM2 and Whisper acquire/release;
- active FFmpeg/FFprobe process count after cancellation;
- first-visible 20 thumbnail latency on HDD/SATA SSD/NVMe where relevant.

Use those results for later tuning; do not replace the measured service results above with guessed numbers.

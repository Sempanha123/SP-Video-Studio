# PHASE 15 STATUS

Completed:

* Production FFmpeg rendering engine consuming stable Phase 13 render specifications.
* Schema v12 render-job/output persistence, render history, functional Render workspace, progress/cancel/retry/result playback, guarded temp/output cleanup, and output validation.
* Image/video/background scene composition, overlays, narration/source-audio mixing, subtitles, bilingual subtitles, Cut/Fade/Crossfade/Slide transitions, aspect/resolution/FPS normalization, and software/hardware encoder discovery.

FFmpeg version tested:

* FFmpeg/FFprobe `7.1.5-0+deb13u1`.
* Build includes libx264, AAC, libass, HarfBuzz/FriBidi, NVENC and QSV encoder entries; AMF is absent.

Renderer architecture:

* `SceneService` snapshot → `RenderPlan` → scene FFV1/PCM NUT intermediates → transition composition → optional ASS subtitle burn → final H.264/AAC MP4 → FFprobe validation.
* Render plan/spec schema is versioned and isolated from QML state.
* One render job at a time through the existing WorkerPool.

Scene rendering:

* Enabled scenes render in project order from immutable snapshot data.
* Background-only, image and video scene inputs are supported.
* Scene-local timing is mapped deterministically into expected project duration, including crossfade/slide overlap.

Image handling:

* Centralized Fit/Fill/Stretch filters preserve aspect ratio unless Stretch is explicitly selected.
* Still images loop only for the requested scene duration.
* Transparent image/logo inputs remain alpha-capable during overlay composition.

Video handling:

* Source start/range, output canvas scaling, output FPS normalization, source-audio preference and normal FFmpeg rotation metadata handling are supported.
* Validation blocks unresolved video-shorter-than-scene ranges instead of silently looping/freezing.

Overlay rendering:

* Logos use FFmpeg overlay filters with normalized coordinates, scale, opacity and timing.
* Text/headline/lower-third overlays use generated ASS/libass for consistent Unicode shaping.
* No QML screenshots or UI pixels are used by the renderer.

Khmer text rendering:

* Actual render with `ព័ត៌មានថ្មីថ្ងៃនេះ` completed through libass/Noto Sans Khmer.
* Extracted output frame was manually inspected: Khmer glyphs were visible and no tofu/missing boxes were observed.

Audio mixing:

* Source video audio and generated narration use stored normalized volumes.
* Inputs normalize to 48 kHz stereo; two-source mixes use `amix` + limiter.
* Silent scenes receive a compatible silence stream to keep sequence composition stable.

Subtitle rendering:

* Phase 12 tracks are exported to render-resolution ASS and burned through libass.
* English + Khmer bilingual subtitle output was rendered and the extracted frame was manually inspected with both lines visible and Unicode intact.
* Windows/Unicode/Khmer subtitle paths use centralized filter escaping.

Transitions:

* Cut: no overlap / stream-copy concat where possible.
* Fade: documented per-scene fade-out/fade-in behavior.
* Crossfade: FFmpeg `xfade` + `acrossfade`, with overlap duration subtracted from project duration.
* Slide: one restrained directional `xfade` slide family; real right-slide composition smoke passed.

Encoder detection:

* Safe `ffmpeg -encoders` parser detects libx264/NVENC/QSV/AMF from the configured build and caches runtime state per FFmpeg path.
* Listed hardware encoders receive a tiny runtime encode probe before Auto can select them.

Software encoding:

* `libx264` is present, runtime-tested and is the verified production fallback.
* Final output defaults to MP4/H.264/yuv420p + AAC/48 kHz stereo + faststart.

Hardware encoding:

* Current FFmpeg build lists NVENC and QSV, but both runtime probes fail in this container because suitable hardware/runtime is unavailable.
* AMF is not compiled into this FFmpeg build.
* Hardware integration test therefore skips honestly; explicit hardware selection can refuse fallback, while Auto safely uses libx264.

Progress:

* Uses `-progress pipe:1`, not human console parsing.
* Handles `out_time_us`, legacy microsecond-valued `out_time_ms`, temporary `N/A`, frames and speed.
* Deterministic weighted stages: scene render 70%, combine 15%, final encode 15%.

Cancellation:

* CancellationToken stops at the active FFmpeg process, terminate is attempted first, then kill after timeout.
* Partial final output/temp are removed and job is marked Cancelled.
* Real 20-second `-re` synthetic render cancellation test passed without leaving the worker thread running.

Output validation:

* FFprobe requires non-empty video, expected dimensions/FPS, duration within tolerance, readable codec and expected audio before Completed.
* Existing ThumbnailService generates the render thumbnail.

Render history:

* Successful outputs persist in `render_outputs` with dimensions/FPS/duration/codecs/file size/thumbnail/actual encoder/FFmpeg metadata.
* Restart/repository reopen test loads the previous output successfully.
* Output Play reuses the Phase 5 playback stack; folder reveal uses PlatformService.

New files:

* `domain/render_output.py`
* `domain/render_preset.py`
* `domain/render_settings.py`
* `media/ffmpeg_escape.py`
* `media/filters.py`
* `rendering/audio_renderer.py`
* `rendering/encoder_registry.py`
* `rendering/errors.py`
* `rendering/hardware.py`
* `rendering/output_validator.py`
* `rendering/overlay_renderer.py`
* `rendering/progress.py`
* `rendering/render_graph.py`
* `rendering/render_plan.py`
* `rendering/scene_renderer.py`
* `rendering/subtitle_renderer.py`
* `rendering/temp_manager.py`
* `rendering/transition_renderer.py`
* `services/render_service.py`
* `services/render_validation_service.py`
* `storage/migrations/m012_create_rendering.py`
* `storage/repositories/render_job_repository.py`
* `storage/repositories/render_output_repository.py`
* `tests/test_render_ffmpeg_integration.py`
* `tests/test_render_phase15.py`
* `ui/controllers/render_controller.py`
* `ui/qml/render/RenderDialog.qml`
* `ui/qml/render/RenderProgress.qml`
* `ui/qml/render/RenderResult.qml`
* `ui/qml/render/RenderSettings.qml`
* `PHASE15_REPORT.md`

Modified files:

* `README.md`
* `app/bootstrap.py`
* `domain/render_job.py`
* `media/ffmpeg.py`
* `media/subtitles/ass_style_builder.py`
* `rendering/renderer.py`
* `services/project_service.py`
* `services/scene_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/__init__.py`
* migration-version assertions in prior regression tests
* `ui/controllers/playback_controller.py`
* `ui/qml/pages/ProjectWorkspacePage.qml`

Tests run:

* Full automated suite: **384 passed, 7 skipped**.
* `python -m compileall -q app domain engines media rendering services storage ui workers` passed.
* Static QML delimiter audit passed for **97 QML files**.
* Expected skips: two PySide6 live-runtime checks unavailable in this sandbox; existing opt-in VoxCPM/faster-whisper/translation integrations; hardware encoder runtime test because no usable hardware encoder is present; normal-suite 60-second performance test because it is opt-in.

Basic render test:

* Real 2-scene image + video render with source audio and a 300 ms crossfade passed using libx264/AAC.
* Output: 320×180, 30 fps, expected/actual duration 2.700 s.

Khmer render test:

* Real Khmer headline render passed; manually inspected extracted frame showed shaped Khmer glyphs without missing boxes.

Bilingual subtitle render test:

* Real English + Khmer ASS/libass burn passed; manually inspected frame showed both lines in the intended order with intact Unicode.

Cancellation test:

* Real 20-second `-re` FFmpeg job cancelled during execution; process stopped and test thread exited cleanly.

Hardware encoder test:

* FFmpeg lists NVENC/QSV, but runtime probe reports neither usable in this container; test skipped instead of claiming hardware support.
* libx264 software encode is mandatory and passed.

60-second performance test:

* Separate real 1920×1080/30 fps test with six alternating 10-second image/video scenes, libx264 Fast: **24.73 s elapsed (~2.43× realtime)**.
* FFprobe duration: **59.966667 s**; Python process reported ~104112 KiB peak RSS.
* Synthetic/simple-source smoke only; not a universal performance benchmark.

Restart persistence test:

* RenderService created a real output/history record; reopening the SQLite repository loaded the same metadata and managed deletion removed only the project-owned render.

Known issues:

* PySide6 is not installed in this packaging sandbox, so live QML launch/runtime smoke remains skipped; static QML wiring/delimiter tests pass.
* Hardware H.264 support is system/build/driver dependent; encoder listing alone is intentionally not treated as readiness.
* Phase 15 targets SDR/yuv420p and does not claim HDR preservation.
* Final audio mixing is intentionally basic explicit-volume mixing; no automatic ducking/mastering yet.
* Phase 16 will provide the polished export/preset experience; Phase 15 exposes the functional Render workspace only.

Architecture decisions:

* FFmpeg receives argv lists with `shell=False`; QML never builds command strings.
* Lossless FFV1 + PCM **NUT** scene intermediates were selected because NUT preserves constant-frame-rate metadata required by FFmpeg 7 `xfade`, while avoiding repeated lossy H.264 encodes.
* ASS/libass is the unified text/subtitle burn strategy for robust Khmer/complex-script shaping.
* Every render uses an immutable RenderPlan snapshot; project edits during rendering cannot mutate the active render.
* Render temp/output deletion is path-guarded.
* Project duplication excludes `renders/` and render cache/history by default because renders are large derived artifacts.

Recommended next phase:
Phase 16 — Export Experience and Export Presets

Suggested Git commit:
`feat: add production FFmpeg rendering engine`

Do not automatically begin Phase 16.

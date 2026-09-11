PHASE 26 STATUS

Completed:

* Implemented Phase 26 only: a resilient local multilingual Batch Factory layered on the existing project/template/asset/language/voice/TTS/subtitle/render/export architecture.
* Added persistent Batch/item/mapping/variant/stage-checkpoint storage through migration 023.
* Added deterministic input mapping, variants, asset assignment, queue execution, retry, pause/resume, cancellation, crash recovery, disk safety, output security, results/history UI, and final documentation.

Batch architecture:

* Batch Factory is an orchestration layer, not a second editor/renderer/TTS/template engine.
* `BatchController → BatchService/Validation → BatchScheduler → existing WorkerPool → BatchWorker → BatchExecutionService → existing Phase 24/25/22/8/11/12/15/16 services`.
* Generated outputs are ordinary SP Video Studio projects and normal Phase 16 exports.

Input formats:

* Manual table rows, CSV, JSON, JSONL/NDJSON.
* UTF-8/Unicode safe, 64 MiB input-file guard, 100,000-row guard, bounded JSON depth.

CSV:

* UTF-8 BOM supported.
* Requires unique non-empty headers and preserves Unicode values including Khmer/Thai/Vietnamese.

JSON:

* JSON requires an array of objects; JSONL requires one object per non-empty line.
* Malformed shape/deep nesting is rejected before queue creation.

Mapping:

* Supports columns, constants, defaults, empty, allow-listed system values, generated filenames, asset mappings, and voice mappings.
* Only allow-listed transforms are supported; no `eval`/arbitrary code execution.
* Safe output filenames/path resolution prevent traversal outside the Batch output root.

Template integration:

* Reuses Phase 24 `TemplateApplyService` to create ordinary derived projects.
* Batch captures an immutable template snapshot so an installed template update does not change an already-created Batch.

Asset integration:

* Reuses Phase 25 Asset Library by ID, unique name, and collection.
* Supports deterministic first-available, round-robin, and SHA-256-seeded-random collection selection.
* Missing/ambiguous/not-ready assets fail validation before rendering.

Language variants:

* Deterministic expansion across central Phase 22 language codes plus voice/platform/aspect/template-option dimensions.
* Unicode paths/data preserved for Khmer, Thai, Vietnamese and other registry-supported languages.

Voice mapping:

* Fixed, column, by-language and by-role voice resolution.
* Voice engine/language capability is validated before TTS.

Multi-speaker:

* Reuses Phase 22 `SpeakerService`, `SpeechBlockService`, and `MultiSpeakerTTSService` for reporter/interview rows.
* Reporter/guest/narrator/presenter speech data remains canonical Phase 22 data; there is no Batch-specific TTS queue.

Translation:

* Supports reviewed-only, configured-machine-translation, and skip policies.
* Reviewed-only requires actual reviewed translated content/reference; machine translation is never mislabeled as reviewed.
* Existing `TranslationService.translate_document(project_id, translation_id, ...)` contract is used.

TTS:

* Reuses existing `NarrationService` for single-speaker narration and `MultiSpeakerTTSService` for multi-speaker blocks.
* TTS is resource-capped at one heavy job at a time by default.

Subtitles:

* Reuses Phase 12 `SubtitleService` and real transcript/translation timing sources.
* Arbitrary CSV text without trustworthy timings does not fabricate subtitle timestamps.

Scene generation:

* Phase 24 template application creates canonical project scenes/layers; Phase 26 does not create a Batch scene model.
* `PREPARE_SCENES` is a checkpoint around the already-materialized canonical project state.

Rendering:

* Reuses Phase 15 renderer/layer compositor through Phase 16 `ExportService`.
* No `BatchRenderer` or second FFmpeg pipeline was added.

Export:

* Platform variants map to existing Phase 16 presets.
* Output path is resolved under the configured Batch output root and validated again after render.
* Keep Both creates deterministic unique intra-Batch names; Fail Item blocks collisions; Replace never permits silent multi-item overwrite collisions.

Variant expansion:

* Stable SHA-256-derived item/variant keys make expansion reproducible across restarts.
* 1,000-item warning threshold and 5,000-item confirmation threshold implemented.

Scheduler:

* Lightweight coordinator feeds existing `WorkerPool`; it does not create another heavy-job queue.
* Scheduler groups compatible work by stage/language/voice while preserving row/output identity.
* SQLite lease/heartbeat prevents duplicate scheduler ownership.

Concurrency:

* Balanced defaults: project=2, light=2, translation=1, TTS=1, render=1.
* Low-memory/auto/maximum-throughput profiles supported.
* TTS and render/export are hard-capped at 1 in Phase 26; lightweight/project stages can overlap safely.

Pause/resume:

* Pause stops new scheduling and lets an already-running atomic stage settle before the Batch reports idle/paused.
* Resume continues from persisted stage checkpoints without rerunning completed stages.

Cancellation:

* Pending items can be cancelled without deleting completed work.
* Optional current-stage cancellation uses the existing cancellation token.

Retry:

* Failed items can be retried individually or as a group.
* Retry restarts from the failed/invalidated stage; completed upstream TTS/translation/project stages remain checkpointed when still valid.

Crash recovery:

* Startup clears stale scheduler locks, converts interrupted running work to paused/interrupted state, and checks completed output existence.
* Missing completed outputs become `output_missing` instead of silently staying completed.

Disk protection:

* Scheduler checks output-volume free space before starting new work.
* Batch pauses on low disk; default reserve is 512 MiB and is configurable in Batch settings.

News safety:

* Topic-only News rows that would require invented facts are blocked.
* Grounded/user-supplied News script/source attribution is allowed.
* No web research automation, social posting, account automation, captcha bypass, cloud workers, or scheduled future Batch jobs were added.

New files:

* `PHASE26_REPORT.md`
* `docs/PHASE26_BATCH_FACTORY.md`
* `app/phase26_runtime.py`
* `domain/batch.py`
* `domain/batch_errors.py`
* `domain/batch_input.py`
* `domain/batch_item.py`
* `domain/batch_mapping.py`
* `domain/batch_stage.py`
* `domain/batch_variant.py`
* `services/batch_asset_service.py`
* `services/batch_execution_service.py`
* `services/batch_import_service.py`
* `services/batch_mapping_service.py`
* `services/batch_recovery_service.py`
* `services/batch_service.py`
* `services/batch_validation_service.py`
* `services/batch_variant_service.py`
* `storage/migrations/m023_create_batch_factory.py`
* `storage/repositories/batch_item_repository.py`
* `storage/repositories/batch_repository.py`
* `tests/test_phase26_batch.py`
* `ui/controllers/batch_controller.py`
* `ui/qml/batch/BatchDetails.qml`
* `ui/qml/batch/BatchErrorPanel.qml`
* `ui/qml/batch/BatchFactory.qml`
* `ui/qml/batch/BatchInputTable.qml`
* `ui/qml/batch/BatchItemRow.qml`
* `ui/qml/batch/BatchMapping.qml`
* `ui/qml/batch/BatchProgress.qml`
* `ui/qml/batch/BatchQueue.qml`
* `ui/qml/batch/BatchSetup.qml`
* `ui/qml/batch/BatchVariantPanel.qml`
* `workers/batch_scheduler.py`
* `workers/batch_worker.py`

Modified files:

* `main.py` — starts Phase 26 runtime.
* `pyproject.toml` — console entry points Phase 26 runtime.
* `storage/migrations/__init__.py` — registers migration 023.
* `ui/qml/pages/BatchPage.qml` — replaces placeholder Batch page with the Phase 26 Batch Factory UI.

Tests run:

* Phase 26 targeted suite: 48/48 passed.
* Phase 22 + 23 + 24 + 25 + 26 combined regression: 128/128 passed.
* Phase 21 dubbing regression: 19/19 passed.
* Python `compileall`: passed.
* Phase 26 QML structural brace audit: 11/11 files passed; `qmllint`/`qmlformat` were not installed in this environment.
* Static architecture/security scan: no Batch renderer, no Batch TTS queue, and no `eval`/`exec` in Phase 26 implementation.

Normal-video Batch test:

* Passed: a no-AI 10-row Batch completed through injected existing-style project/render/export handlers and produced 10 independent outputs.

Reporter Batch test:

* Passed: Reporter/News row fields, grounded attribution, reporter/guest text, and reporter/guest voice assignments survive mapping/resolution correctly.
* Full VoxCPM2 reporter audio generation was not run because optional AI model runtimes/weights are not installed in this sandbox.

Multi-speaker Batch test:

* Passed: multi-role reporter/guest voice/text mapping is preserved, and runtime wiring reuses Phase 22 `SpeechBlockService`/`MultiSpeakerTTSService` rather than a Batch-specific audio queue.
* Heavy real-model TTS was not downloaded/run in the sandbox.

Combined-variant test:

* Passed: deterministic language/platform/aspect/template-option combinations expand to the expected item count and stable variant keys.

Asset-rotation test:

* Passed: collection round-robin and seeded-random strategies are deterministic and restart-reproducible.

Pause/restart/resume test:

* Passed: paused/interrupted work resumes from persisted checkpoints without duplicating completed stages.

Failed-render retry test:

* Passed: a render failure retries from render and does not rerun already-completed TTS.

Template-version test:

* Passed: a Batch created from an older template snapshot remains bound to that captured template version after the installed template changes.

Output-path security test:

* Passed: traversal/escape attempts cannot resolve outside the configured Batch output directory.
* Keep-Both duplicate names resolve deterministically to `name.mp4`, `name (2).mp4`, `name (3).mp4`.

News safety test:

* Passed: topic-only News generation is blocked; grounded script/source-attribution input is allowed.

Khmer Batch test:

* Passed: Khmer Unicode content persists correctly through input/mapping/queue persistence.

Thai Batch test:

* Passed: Thai Unicode content persists correctly through input/mapping/queue persistence.

Vietnamese Batch test:

* Passed: Vietnamese Unicode/diacritics persist correctly through input/mapping/queue persistence.

1,000-item performance test:

* Passed: 1,000 queue items persisted, searched by text, and paged correctly without loading a second queue system.

Restart persistence test:

* Passed: prepared Batch/item/checkpoint state reloads from SQLite and preserves deterministic item identity/output mapping.

Known issues:

* Real local translation/VoxCPM2 end-to-end tests require optional installed model runtimes/weights; sandbox tests use deterministic service doubles for expensive providers.
* Reporter/multi-speaker automated coverage validates mapping/orchestration/wiring rather than downloading and running large AI models.
* `qmllint` and `qmlformat` were unavailable; QML received structural checks plus Python/UI integration assertions instead.
* Phase 26 is intentionally an interactive local queue and does not implement future scheduled Batch runs or cloud workers.

Architecture decisions:

* Reuse canonical Project/Template/Asset/Speaker/SpeechBlock/Subtitle/Renderer/Export models and services; no parallel Batch media model or second renderer.
* Snapshot template/input at Batch creation for reproducibility.
* Persist per-stage fingerprints/checkpoints so retry/recovery is idempotent and dependency-aware.
* Use existing WorkerPool with resource buckets instead of a new heavy background queue.
* Keep generated projects and outputs by default; never automatically delete successful user work.
* Enforce deterministic asset/variant/output behavior and path safety before expensive work.
* News automation remains grounded-input-only; Phase 26 never invents facts.

Recommended next phase:
Phase 27 — Autosave + Recovery

Suggested Git commit:
feat: add resilient multilingual Batch Factory

Do not automatically begin Phase 27.

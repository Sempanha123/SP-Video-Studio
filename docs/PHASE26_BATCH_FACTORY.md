# Phase 26 — Resilient Multilingual Batch Factory

## Scope

Phase 26 adds a local production Batch Factory above the existing SP Video Studio architecture. It does **not** introduce a second renderer, TTS engine, template engine, subtitle engine, or project format. Batch rows are expanded into ordinary projects and then move through the existing Phase 24 template flow, Phase 25 asset library, Phase 22 language/speaker system, Phase 8 TTS, Phase 11 translation, Phase 12 subtitles, Phase 13/22 scene composition, and Phase 15/16 render/export pipeline.

The core user flow is:

`Template → Data → Map → Review → Run`

## Architecture

```text
QML Batch Factory
    ↓
BatchController
    ↓
BatchService ─────────────── BatchValidationService
    │                               │
    ├─ BatchImportService           ├─ BatchMappingService
    ├─ BatchVariantService          ├─ BatchAssetService
    └─ SQLite repositories          └─ language / voice capability checks
            ↓
    BatchScheduler → existing WorkerPool
            ↓
       BatchWorker
            ↓
BatchExecutionService checkpoints
            ↓
existing Template / Script / Translation / TTS / Subtitle / Scene / Export services
```

Batch metadata is persistent SQLite state. Generated projects remain normal SP Video Studio projects, so they can be opened and edited independently after generation.

## Batch state machine

Batch-level states cover draft/ready/running/paused/completed/completed-with-errors/cancelled/failed flows. Item-level states expose pending, validating, project setup, translation, TTS, subtitles, scene setup, rendering, exporting, completed, failed, skipped, cancelled, interrupted, review-required, and output-missing conditions.

Every item is also checkpointed by explicit ordered stages. Completed/skipped stages are persisted and are not rerun unless a setting change invalidates that stage or an earlier dependency.

## Input formats

Phase 26 accepts:

- Manual rows entered in the Batch UI.
- UTF-8 CSV, including BOM.
- JSON arrays of objects.
- JSONL/NDJSON objects, one per line.

Input guards include a 64 MiB file limit, 100,000-row limit, JSON shape validation, and a bounded JSON nesting depth. Unicode text is preserved for English, Khmer, Thai, Vietnamese, and other supported language-registry entries.

## CSV and JSON import

CSV requires a non-empty unique header row. Missing cells become empty strings instead of failing the entire import.

JSON must be an array of objects. JSONL must contain an object on every non-empty line. Deep or malformed data is rejected before queue creation.

## Placeholder mapping

`BatchMappingService` resolves structured values without `eval` or arbitrary Python execution. Supported mapping sources include:

- source columns
- constants
- defaults
- empty values
- safe system values (`row_number`, `batch_name`, `current_date`, `project_name`)
- generated filenames
- fixed/column/collection asset references
- fixed/column/language/role voice references

Only allow-listed text transforms are accepted: trim, upper/lower case, prefix, and suffix. Unknown transforms and unknown system keys fail validation.

## Template snapshots

A Batch stores an immutable snapshot of the selected Phase 24 template and the selected input rows. If the installed template is later edited or upgraded, an already-created Batch can continue from its captured version. Generated projects use `TemplateApplyService`; Batch Factory does not own a separate template renderer or scene model.

## Variant expansion

`BatchVariantService` deterministically expands rows across configured dimensions:

- language
- voice
- platform
- aspect ratio
- template option

Item keys include row index plus a stable SHA-256-derived variant suffix. Expansion reports warnings at 1,000 generated items and requires explicit confirmation at 5,000 items. Variant generation is deterministic across restarts.

## Language variants

Language codes come from the Phase 22 central language registry. Batch validation checks template compatibility and provider capability rather than hardcoding only English/Khmer. Khmer, Thai, Vietnamese, and other supported registry languages preserve Unicode through import, persistence, mapping, queue display, and result export.

## Voice mapping and multi-speaker

Voice assignment supports fixed IDs, source columns, by-language maps, and by-role maps. Before TTS, the selected voice engine is checked against the central language capability registry.

Reporter/interview templates reuse Phase 22 `SpeakerService`, `SpeechBlockService`, and `MultiSpeakerTTSService`. Reporter, guest, narrator, and presenter roles stay ordinary speaker/speech-block data. Phase 26 does not create a separate multi-speaker audio pipeline.

## Translation policy

Translation is explicit and conservative:

- `reviewed_only`: requires an actual reviewed translation value or reviewed translation reference before the item can claim reviewed output.
- `allow_machine_translation`: uses the configured existing TranslationService/provider only after checking the language pair.
- `skip_translation`: leaves the source-language content unchanged.

Machine translation is never mislabeled as human-reviewed translation.

## TTS and subtitles

TTS reuses the existing narration service for single-speaker rows and the Phase 22 multi-speaker service when multiple speech blocks are present. Batch scheduling limits TTS to one heavy generation at a time by default.

Subtitle generation reuses SubtitleService. Transcript/translation timing can create real subtitle tracks; arbitrary CSV text without trustworthy timings does not fabricate timestamps.

## Asset assignment

Phase 25 global assets can be resolved by stable ID, unique name, or collection. Collection strategies are deterministic:

- first available
- round robin by row index
- seeded random using SHA-256-derived seed material

Missing, ambiguous, or not-ready assets are validation errors before rendering. Batch assets remain references to the Phase 25 library and are integrated into the ordinary Phase 24 resolution map.

## Scheduler and resource control

The Batch coordinator is lightweight. Actual stage work is submitted to the existing application `WorkerPool`. Phase 26 adds per-stage resource buckets rather than a second heavy-job queue.

Balanced defaults:

- project preparation: 2
- lightweight stages: 2
- translation: 1
- TTS: 1
- render/export: 1

Low-memory/auto/maximum-throughput profiles can alter safe lightweight/project limits. TTS and render remain capped at one in Phase 26 even when malformed settings request more.

## Pause, resume, cancellation, and retry

Pause prevents new work from being scheduled. An already-running atomic stage may settle first, after which the Batch reports paused.

Cancellation stops pending work and can optionally signal the current stage using the existing cancellation token. Completed items/checkpoints are preserved.

Retry resets only the failed stage and downstream dependencies. Previously completed TTS or earlier stages remain checkpointed when a render-only failure is retried.

## Stage invalidation

Stage fingerprints include the item fingerprint, template version, project ID, relevant language/source-language settings, voice selection, and asset choices. Changing a dependency invalidates the affected stage and all dependent stages rather than silently reusing stale work.

Examples:

- voice change → restart at TTS
- language/source-language change → restart at translation
- asset change → restart at scene preparation

## Crash recovery

On startup Phase 26 clears stale Batch scheduler leases, converts an interrupted running Batch to paused, marks in-flight items interrupted, and verifies that completed output paths still exist. Missing outputs become `output_missing` and can be repaired/retried instead of silently appearing complete.

The Batch lease prevents two schedulers in the same local database from processing the same Batch concurrently.

## Output naming and path security

All Batch outputs are rooted under the configured output directory. Placeholder-based filenames are Unicode-normalized, strip Windows-invalid characters, guard reserved device names, remove traversal segments, and are resolved again before export.

Collision policies:

- Keep Both: deterministic `name.mp4`, `name (2).mp4`, ... during dry run/queue preparation.
- Fail Item: duplicate target names are validation failures.
- Replace: supported only through the existing export overwrite policy; Phase 26 never allows multiple Batch items to silently target the same replacement path.

No Batch output may escape the configured output root.

## Disk protection

Before scheduling new work, the scheduler checks free space on the output volume. If free space falls below the configured reserve (512 MiB default), the Batch pauses with a low-disk reason instead of starting another render.

## Generated project policy

Phase 26 keeps generated projects by default. They can be opened in the normal editor, and opening a generated project marks the item as manually modified. Batch record deletion is separate from generated project/output deletion so completed work is not automatically removed.

## News safety

Batch Factory never researches or invents News facts. A News/Reporter template cannot run from a topic-only row that would require unsupported fact generation. News rows must supply grounded source/script/claim data or explicit user-provided attribution required by the selected template/policy.

Phase 26 does not add browser automation, platform account automation, social posting, captcha bypass, cloud workers, or scheduled future Batch runs.

## Large Batch behavior

Queue persistence and search use indexed SQLite tables and paged repository reads. A 1,000-item persistence/search/page test is included. Very large variant expansions are previewed before queue creation, and thresholds warn/require confirmation rather than silently creating an unbounded queue.

## Rendering and export

Batch Factory does not implement `BatchRenderer`. `ExportService` creates the existing immutable render plan and invokes the existing Phase 15 renderer/compositor. Platform variants resolve to existing Phase 16 export presets. The explicit Batch render stage performs export; the following export checkpoint verifies the output file.

A real FFmpeg smoke test creates three independent Batch outputs through the existing layered scene compositor, then probes the final videos to confirm the expected dimensions.

## Phase 26 limits

- Real VoxCPM2/translation-model end-to-end jobs depend on the optional local runtimes/models being installed; automated tests use deterministic service doubles for those expensive providers.
- Reporter/multi-speaker tests validate mapping/orchestration and reuse wiring without downloading AI models.
- QML lint tools were not installed in the test environment; all 11 Phase 26 QML files passed structural brace checks and the Python/UI integration tests passed.
- Phase 26 intentionally does not schedule future Batch runs. It is a local interactive production queue only.

## Next phase

Recommended next phase: **Phase 27 — Autosave + Recovery**.

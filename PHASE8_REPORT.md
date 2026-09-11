# PHASE 8 STATUS

## Completed:

- Official VoxCPM2 adapter architecture with lazy dependency loading
- Default, designed, reference, and continuation-capable request model
- CPU / CUDA / Auto device selection through System Readiness
- Model Manager install/readiness/in-use integration
- Load/reuse/unload lifecycle for one shared VoxCPM2 instance
- Typed dependency/model/load/generation/OOM/device/cancellation errors
- English and Khmer-safe text pipeline
- Paragraph/sentence-aware TTS chunking including Khmer punctuation
- Preview, selected-section, and full enabled-script narration generation
- Background worker progress and safe-boundary cancellation
- Project-managed WAV output + generated-audio SQLite persistence
- SHA-256 narration freshness detection
- Safe generated-audio deletion and shared Phase 5 playback preview
- Authorized reference-audio project copy without changing the original
- Generated narration duplication/deletion compatibility
- Functional compact Narration panel inside Script workspace
- Python 3.11–3.14 base-application support retained

## VoxCPM version tested:

- Adapter/API contract targets official `voxcpm` **2.0.3**.
- Official current repository/PyPI API was rechecked during implementation.
- Standard CI does not install/load the 2B model.

## Model identifier:

- `openbmb/VoxCPM2`
- Model files come from the Phase 7 managed installation directory.
- Runtime loading uses local-files-only behavior and does not intentionally create a second hidden model download.

## TTS engine:

- `TTSEngine` upgraded to reusable load/unload/generate/capabilities/request-validation lifecycle.
- `TTSEngineManager` owns one engine instance per ID.
- `VoxCPM2Engine` lazily imports `torch`, `voxcpm`, and `soundfile`.
- Current official `VoxCPM.from_pretrained(hf_model_id=..., local_files_only=True, device=...)` contract is isolated inside the adapter.
- Current official generation controls used: CFG, inference timesteps, normalization, seed, prompt/reference audio.
- Voice design uses the official `(control)text` convention.
- `FakeTTSEngine` is test-only and cannot be selected by production bootstrap.

## Device support:

- Auto
- CPU
- CUDA
- Explicit CUDA validates the active PyTorch runtime.
- Auto uses System Readiness and performance profile.
- Low Memory profile can prefer CPU when reported VRAM is insufficient.
- No dtype-specific unsupported flags are invented by the app.

## English generation:

- English Unicode input, chunking, persistence and valid WAV generation are covered with the fake engine.
- Real English VoxCPM2 synthesis is available through the opt-in integration test when the official runtime/model is installed.
- A real listening check was not possible in this packaging sandbox.

## Khmer generation:

- Khmer Unicode survives request/chunk/storage/path pipeline.
- Khmer sentence punctuation (`។`, `!`, `?`) participates in safe chunking.
- Valid Khmer-path WAV creation is covered with the fake engine.
- Real Khmer listening/intelligibility must be checked on the target VoxCPM2 runtime and was not claimed from file creation alone.

## Voice Design:

- Designed mode is supported by typed `VoiceConfig`.
- User voice description is passed through the current official VoxCPM control convention.
- Description is never hardcoded in the engine.
- Normal UI keeps advanced controls compact; full Voice Studio remains Phase 9.

## Reference voice:

- Reference mode requires explicit permission confirmation.
- Supported project input path is validated before use.
- Authorized source audio is copied into project-managed `audio/references/`; original files remain unchanged.
- Engine request keeps reference and continuation prompt-audio concepts separate.
- No celebrity/public-figure voice presets are included.

## Script integration:

- Generate Preview
- Generate Selected Section Voice
- Generate Full Narration
- Full narration uses enabled sections only and respects stored script order/language.
- Pending script edits are saved before section/full generation.
- Script saves refresh narration freshness state.
- Stable SHA-256 text hash excludes storage IDs so copied narration remains valid after project duplication.

## Generated audio storage:

- Database schema upgraded from 4 to **5** in place.
- New `generated_audio` table stores metadata only; audio stays on disk.
- Final files: `project/audio/narration/<id>.wav`
- Temporary chunks: `project/cache/tts/<job>/`
- Reference files: `project/audio/references/`
- WAV validity, duration, sample rate and channels are checked before completion.
- Regeneration creates a new file/record before changing active narration.

## Model lifecycle:

- Model Manager installation state is checked before load.
- Model Manager in-use count prevents removal while VoxCPM2 is loaded/in use.
- One loaded model instance is reused across generation requests.
- Explicit Unload releases references and CUDA cache where applicable.
- App shutdown requests narration cancellation and unloads the TTS model before worker shutdown.

## Memory/OOM handling:

- Common CUDA OOM errors map to typed `TTSOutOfMemory`.
- Failed outputs are removed.
- CUDA cache cleanup runs after OOM/unload where appropriate.
- UI shows a user-oriented retry suggestion rather than a raw traceback.

## Cancellation:

- Queued/pre-generation work can cancel immediately.
- Multi-chunk generation checks cancellation between every safe stage/chunk.
- If upstream VoxCPM inference is already inside one model call, cancellation completes after that segment returns.
- Temporary chunk directories and incomplete final WAVs are cleaned.

## New files:

- `domain/generated_audio.py`
- `domain/narration.py`
- `domain/voice_config.py`
- `engines/tts/errors.py`
- `engines/tts/fake_engine.py`
- `engines/tts/manager.py`
- `engines/tts/types.py`
- `engines/tts/voxcpm2_engine.py`
- `services/narration_service.py`
- `services/tts_chunking_service.py`
- `services/tts_service.py`
- `storage/migrations/m005_create_generated_audio.py`
- `storage/repositories/generated_audio_repository.py`
- `workers/tts_worker.py`
- `ui/controllers/tts_controller.py`
- `ui/qml/editor/TTSPanel.qml`
- `tests/test_tts_phase8.py`
- `tests/test_tts_qml_structure.py`
- `tests/test_voxcpm_integration.py`
- `PHASE8_REPORT.md`

## Modified files:

- `app/bootstrap.py`
- `engines/model_registry.py`
- `engines/tts/base.py`
- `pyproject.toml`
- `services/model_service.py`
- `services/project_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/controllers/playback_controller.py`
- `ui/controllers/project_controller.py`
- `ui/qml/editor/ScriptEditor.qml`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- `tests/test_database.py`
- `tests/test_media_phase4.py`
- `tests/test_model_phase7.py`
- `tests/test_script_phase6.py`
- `README.md`

## Tests run:

- `python -m compileall -q app domain engines services storage workers ui`
- `pytest -q`
- **170 passed**
- **3 skipped**: 2 PySide6 runtime smoke tests unavailable in the packaging sandbox + 1 opt-in real VoxCPM2 integration test
- Existing Phase 0–7 regression suite remains green.
- Temporary runtime bootstrap smoke upgraded a fresh database to schema v5 and resolved `TTSService` / `NarrationService` successfully.

## Fake-engine tests:

- Valid WAV generation
- English and Khmer Unicode
- Section/full generation
- Preview generation
- Persistence/metadata
- Cancellation cleanup
- Script freshness/out-of-date behavior
- Stable duplicated-project hash behavior
- Generated-audio safe deletion guard
- Project duplication/deletion compatibility
- Model load reuse/in-use release
- CPU/CUDA Auto device policy
- OOM mapping

## Real VoxCPM integration test:

- Added as opt-in `integration` + `voxcpm` pytest test.
- Requires `SPVS_RUN_VOXCPM_INTEGRATION=1`, a real managed model path, and compatible installed VoxCPM/PyTorch dependencies.
- Not executed in the packaging sandbox because the multi-GB model/runtime is intentionally not installed there.

## English listening check:

- Not performed in this sandbox.
- Must be listened to on the target machine; automated WAV creation alone is not reported as an audio-quality result.

## Khmer listening check:

- Not performed in this sandbox.
- Khmer pipeline/encoding tests pass, but intelligibility/voice quality must be evaluated by listening on the target machine.

## Restart persistence test:

- Generated-audio records are SQLite-persistent and WAV files are project-owned.
- Repository/list/current-hash behavior is covered by reopened database/project service tests from the existing persistence architecture.
- No playback position or active inference job is restored after restart.

## Known issues:

- Live QML runtime smoke remains skipped in this sandbox because PySide6 is not installed.
- Real VoxCPM2 synthesis/listening is an opt-in hardware/model integration test, not part of standard CI.
- Upstream VoxCPM/PyTorch/transitive wheel support can vary by Python/platform; the base application remains Python 3.11–3.14 compatible and TTS failure is isolated from app startup.
- Running VoxCPM inference may not be interruptible inside a single upstream inference call; cancellation is guaranteed at safe chunk boundaries.
- Full Voice Studio management, reusable global voice library, mastering and richer reference-voice UX are intentionally deferred to Phase 9.

## Architecture decisions:

- Heavy TTS dependencies are always lazy imports.
- VoxCPM-specific API details live only in `VoxCPM2Engine`.
- Model Manager remains the single owner of installed model files/state.
- Generated narration is a separate project-owned domain from imported media but reuses the shared playback system.
- Narration is section/chunk aware for future subtitles/scenes while no subtitle/scene implementation is added.
- Lossless WAV concatenation is used with centralized small chunk/section pauses.
- Reference recordings are copied only after explicit permission confirmation.
- Project duplication copies generated WAVs to independent IDs and remaps managed reference paths.
- No Phase 9 Voice Studio, Whisper, translation, subtitles, scenes, timeline or rendering code is included.

## Recommended next phase:
Phase 9 — Voice Studio UX

## Suggested Git commit:
`feat: integrate VoxCPM2 text-to-speech engine`

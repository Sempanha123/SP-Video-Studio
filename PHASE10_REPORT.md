# PHASE 10 STATUS

## Completed:

- Official faster-whisper adapter isolated behind the generic STT engine interface
- Lazy faster-whisper/CTranslate2 imports so missing STT dependencies never break app startup
- Audio/video transcription from Phase 4 project-managed media paths
- Auto Detect / English (`en`) / Khmer (`km`) language modes
- Timestamped segments plus optional word-level timestamps
- VAD, standard inference and optional batched inference controls
- CPU/CUDA/Auto device and safe compute-type policy
- Background transcription jobs with progress and cancellation at safe segment boundaries
- Persistent editable transcripts, original-text reset, search and UTF-8 TXT export
- Segment playback through the existing Phase 5 player
- Source fingerprinting and Out of Date transcript detection
- Safe regeneration that preserves a previous successful active transcript until replacement succeeds
- Model-manager loaded/in-use integration and TTS/STT GPU resource coordination
- Project duplication remaps transcripts to duplicated media IDs
- Project deletion cleans project-owned transcript rows without touching external originals
- Database schema upgraded in place to version 7

## faster-whisper version tested:

- Official current API target verified: `faster-whisper 1.2.1`
- Adapter behavior tested with deterministic current-API fakes in the standard suite
- Real package/model execution is opt-in and was not run in this packaging sandbox because faster-whisper is not installed here

## CTranslate2 version:

- Project optional dependency targets `ctranslate2>=4.8.2,<5`
- Current device capability is queried at runtime through CTranslate2 rather than inferred only from PyTorch CUDA state
- CTranslate2 is not installed in this packaging sandbox, so real CUDA/CPU runtime loading was not executed here

## Supported models:

- Whisper Small (`whisper-small`)
- Whisper Medium (`whisper-medium`)
- Whisper Large V3 (`whisper-large-v3`)
- Models are the managed Phase 7 faster-whisper/CTranslate2 variants only
- Transcription never auto-downloads a missing model

## Device support:

- Auto
- CPU
- CUDA where CTranslate2 reports a usable runtime
- CUDA readiness is validated separately from PyTorch/VoxCPM readiness

## Compute types:

- CPU prefers `int8` when supported
- CUDA prefers `float16`
- Low Memory CUDA may prefer `int8_float16` when supported
- Advanced UI also permits explicit supported compute selection
- Unsupported device/compute combinations fail with a typed, user-friendly message

## English transcription:

- Explicit `en` request path covered by fake-engine/service tests
- Auto-detected English language/probability persistence covered
- UTF-8 editing/export and timestamped segment persistence covered
- Real English audio transcription remains an opt-in target-machine integration check

## Khmer transcription:

- Explicit `km` path covered
- Khmer Unicode segments persist through SQLite/restart-safe repository access
- Khmer TXT export remains UTF-8
- Real Khmer recognition quality requires target-machine audio review and is not claimed from fake-engine tests

## Language detection:

- Auto mode passes `language=None` to faster-whisper
- Detected language and probability are persisted on the Transcript record
- Manual English/Khmer selections are preserved without translation behavior

## Word timestamps:

- Enabled by default in the Phase 10 request/UI
- Persisted as separate `transcript_words` rows with integer millisecond start/end values
- Word timestamps remain generated data; Phase 10 does not expose manual per-word timing edits

## VAD:

- Enabled by default in normal UI
- Uses the current faster-whisper VAD integration
- Optional VAD settings flow through the request adapter
- No-speech output completes cleanly with a ready empty transcript instead of a fabricated transcript

## Batched transcription:

- Current `BatchedInferencePipeline` path supported
- Batch size is explicit/conservative and validated
- Standard mode remains available and is the safe fallback
- Adapter test confirms requested batch size reaches the current API

## Transcript editor:

- Timestamped segment rows
- Plain-text segment editing with debounced autosave
- Generated original text preserved separately
- Reset to Generated Text
- Search
- Copy Full Transcript
- UTF-8 TXT export
- Re-transcribe flow retains earlier good transcript until success

## Playback integration:

- Segment Play reuses Phase 5 `PlaybackController`
- Playback seeks the selected project media to `segment.start_ms`
- No second media-player stack was introduced

## AI resource coordination:

- Lightweight `AIResourceManager` tracks heavy TTS/STT engine use
- Idle conflicting CUDA engine can be unloaded before loading another
- Active TTS work blocks a conflicting Whisper CUDA load instead of silently overcommitting GPU resources
- Whisper model loaded/in-use state flows through Phase 7 Model Manager

## Cancellation:

- Cancellation is checked while consuming the faster-whisper segment generator
- UI reports “Stopping transcription…” rather than promising instant interruption
- Incomplete Phase 10 transcripts are discarded by default
- Existing successful active transcript remains intact after a cancelled regeneration

## New files:

- `domain/transcript.py`
- `domain/transcript_segment.py`
- `domain/transcript_word.py`
- `engines/stt/errors.py`
- `engines/stt/fake_engine.py`
- `engines/stt/faster_whisper_engine.py`
- `engines/stt/manager.py`
- `engines/stt/types.py`
- `services/ai_resource_manager.py`
- `services/transcript_analysis_service.py`
- `services/transcription_service.py`
- `storage/migrations/m007_create_transcripts.py`
- `storage/repositories/transcript_repository.py`
- `ui/controllers/transcription_controller.py`
- `ui/models/transcript_segment_model.py`
- `ui/qml/editor/TranscriptionPanel.qml`
- `ui/qml/editor/TranscriptEditor.qml`
- `ui/qml/editor/TranscriptSegmentRow.qml`
- `ui/qml/editor/TranscriptToolbar.qml`
- `tests/test_stt_phase10.py`
- `tests/test_faster_whisper_adapter.py`
- `tests/test_stt_qml_structure.py`
- `tests/test_faster_whisper_integration.py`
- `PHASE10_REPORT.md`

## Modified files:

- `.gitignore` (anchor runtime `/models/` ignore so `ui/models/` Python files are trackable)
- Previously local-but-Git-ignored `ui/models/` files are included in the patch so the pushed repository gains the QML list-model package used by Phases 4/6/7/9/10
- `app/bootstrap.py`
- `engines/stt/__init__.py`
- `engines/stt/base.py`
- `pyproject.toml`
- `services/media_service.py`
- `services/project_service.py`
- `services/tts_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- migration-version assertions in existing Phase 2/4/6/7/8/9 regression tests
- `README.md`

## Tests run:

- `python -m compileall -q app domain engines services storage ui workers media rendering workflows`
- `git diff --check` passed
- `pytest -q`
- Dedicated Phase 10 service tests: 21 passed
- faster-whisper adapter/QML tests: 8 passed
- Real faster-whisper integration test: opt-in/skip by default
- Full suite: **220 passed, 4 skipped**

## Fake-engine tests:

- Deterministic English/Khmer segments and word timestamps
- Generator consumption/progress
- Cancellation/partial discard
- No-speech completion
- Persistence/restart repository reads
- Edit/reset/search/export
- Source staleness
- Regeneration history/activation
- Project duplication/deletion
- AI resource conflicts

## Real faster-whisper integration test:

- Added as `tests/test_faster_whisper_integration.py`
- Requires `SPVS_RUN_FASTER_WHISPER_INTEGRATION=1`
- Requires an installed managed Whisper model path and authorized short media fixture
- Not executed in this sandbox because faster-whisper/CTranslate2 are not installed

## English listening/transcription check:

- Current adapter flow and English text persistence were verified with fake/current-API tests
- No real Whisper model/audio listening/transcription quality check was performed in this sandbox
- Target-machine release testing should transcribe and manually review a short original/authorized English clip

## Khmer transcription check:

- Khmer request code, Unicode storage, segment editing and UTF-8 export are automated and passing
- Real Khmer model accuracy was not evaluated in this sandbox
- Target-machine release testing should run both Auto Detect and explicit `km` on original/authorized Khmer audio

## Restart persistence test:

- Transcript/segments/word rows are stored in SQLite and reopened by a fresh repository instance in automated tests
- Detected language, edits, original text and timestamps persist
- Source fingerprint is re-evaluated on reload and marks changed media Out of Date without deleting transcript text

## Known issues:

- Earlier GitHub pushes omitted `ui/models/` because the unanchored `models/` ignore rule matched nested source directories; this patch anchors it to `/models/` and re-includes the existing UI model source files
- PySide6 is unavailable in this packaging sandbox, so live QML runtime smoke remains skipped
- faster-whisper/CTranslate2 are not installed here; the real-model integration test is therefore opt-in and skipped
- CUDA success depends on the target CTranslate2/CUDA/cuDNN runtime, not merely GPU/PyTorch detection
- Batched inference can require substantially more memory; standard mode remains available
- Khmer/other-language recognition quality depends on Whisper model/audio quality and is not guaranteed equal to English
- Phase 10 intentionally does not implement speaker diarization, translation or final subtitle export/styling

## Architecture decisions:

- faster-whisper-specific API calls are isolated to `FasterWhisperEngine`
- Heavy STT dependencies are lazy-imported
- Phase 7 Model Manager remains the only model installation source
- Phase 4 project-managed media is the STT source of truth; originals are never modified
- Segment/word timestamps are normalized to integer milliseconds for future subtitle/timeline precision
- A successful previous transcript remains active until regeneration fully completes
- Incomplete cancelled transcripts are discarded in Phase 10
- Transcript text edits never mutate generated timestamps or `original_text`
- TTS and STT share a small resource coordinator instead of independently occupying conflicting GPU memory
- Translation mode in Whisper is not exposed as product translation

## Recommended next phase:
Phase 11 — Translation Engine and Translation Review

## Suggested Git commit:
`feat: integrate faster-whisper speech-to-text and transcript editor`

Do not automatically begin Phase 11.

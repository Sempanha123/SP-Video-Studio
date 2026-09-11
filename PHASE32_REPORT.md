# PHASE 32 STATUS

Completed:

* Added the reusable Manual Speech & TTS Editor without creating a second TTS system, subtitle system, timeline, or mixer.
* Extended canonical SpeechBlock with project ownership, absolute timing, active take, text hash, audio/timing statuses, and user-modified state while preserving legacy fields.
* Added direct text editing, explicit outdated/regenerate behavior, bulk assignment, split/merge, Unicode find/replace, editable timecodes, take history, duration fit actions, transcript/translation/subtitle adapters, and multi-workflow reuse.
* Reused existing Voice Studio profiles, MultiSpeakerTTSService, TTSService/AIResourceManager, Timeline, Phase 27 save state, and Phase 30 Audio Mixer.

Data/migration:

* Added migration 27 with backward-compatible SpeechBlock columns and project/timing/status indexes.
* Existing `audio_id` and non-scene `start_offset_ms` remain mirrored for Phase 22/30 compatibility.
* Project duplication clears generated take pointers while preserving text, timing, speaker, voice, and language configuration.

Manual editing:

* Text edits calculate a new SHA-256 text hash, preserve the current take, mark it Outdated, and never auto-regenerate.
* Start/End remain canonical integer milliseconds and are editable as `mm:ss.mmm` / `hh:mm:ss.mmm`.

Multi-speaker / voice:

* Per-row speaker, VoiceProfile, and language are independent.
* Bulk Set Speaker / Set Voice / Set Language works only on selected rows.
* Resolution order remains block override → speaker voice → project default → unresolved.
* Voice filters cover language, role/category, style, tone, energy, and favorites.

Generation/takes:

* Generate Selected, Generate Outdated, and Generate All reuse existing multi-speaker TTS and model lifecycle.
* Source-audio rows are never sent to TTS.
* Previous successful takes remain available; an older take can be reactivated.
* Failure/cancellation preserves the prior active take.

Timeline / mixer:

* Timed SpeechBlocks appear on the existing Voice/Source Audio Timeline tracks.
* Table timing and Timeline drag/resize write the same SpeechBlock timing fields.
* Timeline timing commits integrate with the existing command stack.
* Generated SpeechBlock audio continues through the existing Phase 30 mixer compatibility path.

Subtitle/transcript/translation:

* Subtitle synchronization is explicit and protects manually edited subtitle cues.
* Transcript → Speech preserves segment timing and speaker metadata when present.
* Translation → Speech preserves reviewed/machine-translated state in metadata.
* Existing real word timestamps remain untouched; no fabricated TTS/translated word timestamps are produced.

Workflow integration:

* News Studio: shared Speech/Voice Script stage.
* Story Studio: shared Narrator/Character speech stage.
* Translate & Dub: shared editor is available without removing the source/translation comparison UI.
* Shorts: shared voiceover Speech/TTS workspace.
* Timeline: shared Speech/TTS side panel and two-way timing sync.

Performance:

* Virtualized/reused ListView delegates; text editor instantiated only for the current editing row.
* Designed for 1,000 SpeechBlocks without 1,000 active text editors.

New files:

* `app/manual_speech_runtime.py`
* `services/manual_speech_editor_service.py`
* `storage/migrations/m027_manual_speech_editor.py`
* `ui/controllers/manual_speech_controller.py`
* `ui/qml/speech/SpeechEditor.qml`
* `ui/qml/speech/SpeechInspector.qml`
* `ui/qml/speech/SpeechRow.qml`
* `docs/PHASE32_MANUAL_SPEECH_TTS_EDITOR.md`
* `tests/test_phase32_manual_speech.py`
* `PHASE32_REPORT.md`

Modified files:

* `domain/speech_block.py`
* `services/speech_block_service.py`
* `services/multispeaker_tts_service.py`
* `services/timeline_mapping_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/generated_audio_repository.py`
* `storage/repositories/phase22_repository.py`
* `ui/qml/timeline/TimelineTrack.qml`
* `ui/qml/timeline/TimelineEditor.qml`
* `ui/qml/news/NewsStudio.qml`
* `ui/qml/story/StoryStudio.qml`
* `ui/qml/dubbing/TranslateDubStudio.qml`
* `ui/qml/shorts/ShortsStudio.qml`
* `main.py`
* `pyproject.toml`
* `README.md`

Tests run:

* Existing Phase 31 baseline before Phase 32: 319/319 passed.
* During the original Phase 32 implementation pass in this chat: focused Phase 32 37/37 passed; cumulative Phase 22–32 356/356 passed; separate Phase 21 Dub 19/19 passed.
* The transient cumulative workspace later disappeared from the execution environment, so the final reconstructed patch was revalidated with **50/50 Phase 32 model/contract tests**, Python compile, idempotent SQLite migration/backfill, QML structure, and Phase 28 theme-token checks rather than falsely claiming a second cumulative run on unavailable files.

Mandatory acceptance scenario:

* Covered by the Phase 32 design/tests: Reporter Khmer, Guest English/source audio, Reporter Thai, Narrator Vietnamese; manual edits, different voices/languages, timing edits, split/merge, selected generation, Outdated preservation/regeneration, Timeline/Mixer refresh, and persistent canonical database fields.

Known issues:

* PySide6/qmllint and real VoxCPM2 weights are unavailable in this sandbox, so live desktop interaction and real TTS listening are not claimed here.
* Voice preview button selects the Voice Studio profile and hands previewing to the existing Voice Studio flow rather than creating another preview engine.

Architecture decisions:

* SpeechBlock is the only speech segment model.
* GeneratedAudio is the only generated-take store.
* Existing Phase 22 TTS / AIResourceManager own model lifecycle.
* Existing Timeline owns visual timing; SpeechBlock owns speech timing data shown there.
* Existing Phase 30 mixer owns audio routing.
* Legacy fields are mirrored to avoid breaking earlier phase code.

Suggested Git commit:

`feat: add manual multi-speaker speech and TTS editor`

Do not automatically begin another phase.

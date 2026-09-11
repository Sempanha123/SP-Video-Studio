# PHASE 12 STATUS

Completed:

* Professional project-owned subtitle foundation and Subtitle Studio workspace
* Transcript, reviewed translation, bilingual, imported, and manual subtitle tracks
* Editable Unicode cue text and integer-millisecond timing
* Add/delete/split/merge/shift/order normalization
* Source-safe synchronization that protects subtitle edits
* Live playback overlay using the existing Phase 5 player
* Word-timestamp highlighting where real source timings exist
* Versioned built-in styles plus global user presets
* SRT, VTT, and ASS export plus SRT/VTT/basic ASS import
* Short FFmpeg/libass subtitle burn-in preview job
* Schema v9 in-place migration from previous databases

Subtitle architecture:

* Format-neutral `SubtitleTrack`, `SubtitleCue`, `SubtitleWord`, and `SubtitleStyle` domain models
* SQLite rows remain the editable source of truth; SRT/VTT/ASS are import/export formats only
* `SubtitleRepository` owns subtitle SQL and project-ownership guards
* `SubtitleGenerationService` builds tracks from transcript/translation relationships
* `SubtitleTimingService`, `SubtitleValidationService`, `SubtitlePresetService`, `SubtitleImportService`, and `SubtitlePreviewService` keep concerns separate
* `SubtitleController` and `SubtitleCueListModel` expose the feature to QML without SQL in QML

Source integrations:

* Phase 10 transcripts provide edited segment text, source timing, and optional real word timings
* Phase 11 translations provide human-reviewed `translated_text` and source-segment alignment
* Phase 5 PlaybackService is reused for seek/play/live overlay
* Phase 3/4 FFmpeg path discovery is reused for short burn-in preview rendering
* Source transcript/translation data is never modified by subtitle editing

Transcript subtitles:

* One initial cue per transcript segment
* Edited transcript text becomes the initial caption text
* Segment start/end milliseconds are preserved
* Real `TranscriptWord` rows are copied into `SubtitleWord` rows
* Transcript source hashes support later explicit source synchronization

Translated subtitles:

* Uses Phase 11 `translated_text`, preserving human corrections instead of raw machine output
* Translation segment timing is retained
* Unreviewed translation sources are allowed with warning metadata rather than blocked
* No fake target-language word timestamps are generated

Bilingual subtitles:

* Source and target text remain separate as `text` and `secondary_text`
* Alignment uses stable `source_segment_id`, never row number
* Primary/secondary language order is configurable at creation
* Missing alignment is recorded instead of silently pairing the wrong rows
* Project duplication remaps both translation and transcript relationships

Word highlighting:

* Playback position resolves active cue and word from in-memory ordered data
* Karaoke/Creator presets can enable a highlight style
* Highlighting uses genuine transcript word timings only
* Translated-target karaoke is intentionally unavailable without target-language timing

Subtitle presets:

* Versioned built-ins: Clean, News, Bold, Minimal, Creator, Karaoke, Documentary
* Presets live in `resources/subtitles/presets.json`, not QML
* Applying a preset copies effective values into the project style for reproducibility
* Global user presets can be saved/deleted; built-ins cannot be deleted

Style editor:

* Font family, reference font size, weight, primary/secondary colors, outline, background, shadow, alignment, vertical position, margins, line limits, highlight colors, and bilingual scale are domain settings
* Live QML overlay responds to cue/style/playhead changes without generating a video on every edit
* Preferred default font is Noto Sans Khmer when available; font fallback remains platform-dependent
* Safe-area guides are represented in normalized preview space

SRT:

* Dedicated exporter with correct comma-millisecond timestamps
* UTF-8 English/Khmer and multiline text supported
* SRT import creates an independent editable subtitle track

VTT:

* Dedicated WebVTT exporter; not an SRT string replacement
* Correct period-millisecond timestamps and UTF-8 text
* VTT import supports normal cue timing/text and ignores unsupported metadata safely

ASS:

* Dedicated ASS exporter with Script Info, V4+ Styles, and Events sections
* Domain styles are converted by the exporter rather than stored as raw ASS tags
* Correct ASS BGR/alpha color conversion, alignment, newline and brace escaping
* Bilingual rows export as separate ASS lines within the event text
* Basic ASS event import is supported; arbitrary third-party override-tag preservation is not claimed

Khmer support:

* Khmer survives database persistence, SRT/VTT/ASS import/export, filenames, and paths as UTF-8
* Readability validation uses a character-rate heuristic rather than pretending English word boundaries apply
* FFmpeg path escaping preserves Khmer Unicode
* A real libass burn test displayed Khmer glyphs using Noto Sans Khmer without missing-box rendering in the inspected frame

FFmpeg/libass preview:

* `SubtitlePreviewService` renders only a short project-cache preview clip in the worker pool
* Filter path escaping is centralized for Windows drive colons, spaces, quotes, brackets, and Unicode paths
* Validation run used FFmpeg 7.1.5 and produced a valid 2.52-second H.264/AAC preview
* This is a visual test/debug path, not final production video rendering

Validation:

* Errors: negative or invalid cue timing
* Warnings: overlap, sub-300 ms cues, unusually long cues, excessive lines, fast reading rate, and safe-margin concerns
* English and Khmer use different readability heuristics
* Export is blocked only for hard timing errors, not every stylistic warning
* Active cue lookup uses binary search; model playhead changes update only affected active rows

Source synchronization:

* SHA-based source links detect changed transcript/translation rows
* Unchanged cues preserve subtitle edits
* Changed source marks `sourceChanged` instead of overwriting user caption text
* New source rows add cues
* Removed/missing source rows remain editable/exportable and are flagged rather than cascade-deleted

New files:

* `PHASE12_REPORT.md`
* `domain/subtitle_cue.py`
* `domain/subtitle_preset.py`
* `domain/subtitle_style.py`
* `domain/subtitle_word.py`
* `media/subtitles/__init__.py`
* `media/subtitles/base.py`
* `media/subtitles/srt_exporter.py`
* `media/subtitles/vtt_exporter.py`
* `media/subtitles/ass_exporter.py`
* `media/subtitles/ass_style_builder.py`
* `resources/subtitles/presets.json`
* `services/subtitle_generation_service.py`
* `services/subtitle_import_service.py`
* `services/subtitle_preset_service.py`
* `services/subtitle_preview_service.py`
* `services/subtitle_service.py`
* `services/subtitle_timing_service.py`
* `services/subtitle_validation_service.py`
* `storage/migrations/m009_create_subtitles.py`
* `storage/repositories/subtitle_repository.py`
* `ui/controllers/subtitle_controller.py`
* `ui/models/subtitle_cue_model.py`
* `ui/qml/editor/SubtitleCueRow.qml`
* `ui/qml/editor/SubtitlePreviewOverlay.qml`
* `ui/qml/editor/SubtitleStudio.qml`
* `ui/qml/editor/SubtitleStylePanel.qml`
* `ui/qml/editor/SubtitleToolbar.qml`
* `tests/test_subtitle_phase12.py`
* `tests/test_subtitle_qml_structure.py`

Modified files:

* `README.md`
* `app/bootstrap.py`
* `domain/subtitle.py`
* `services/project_service.py`
* `services/translation_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/__init__.py`
* `ui/qml/pages/ProjectWorkspacePage.qml`
* Existing migration/QML regression tests updated for schema v9 and the now-functional Subtitles module

Tests run:

* `python -m compileall -q app domain engines media services storage ui workers`
* `pytest -q`
* 281 passed
* 5 expected skips: two PySide6 runtime smokes unavailable in this sandbox plus the opt-in faster-whisper, translation, and VoxCPM real-model integration tests
* Phase 0-11 regression suite remains green

SRT round-trip:

* Passed: cue count/timing/text/newlines survive SRT export then import within supported format semantics
* Khmer UTF-8 export is covered

VTT round-trip:

* Passed: WebVTT timing/text survives export then import within supported format semantics
* Khmer UTF-8 export is covered

ASS render check:

* Passed with FFmpeg 7.1.5/libass using a generated three-second test video and exported ASS
* Short render completed and FFprobe reported 2.52 seconds
* Rendered frame was visually inspected

Khmer render check:

* Passed using installed Noto Sans Khmer fonts
* Khmer characters were visible in the inspected burn-in frame with no tofu/missing-box glyphs
* Exact typography can still vary by target machine/font installation

Large-track test:

* Passed with 1,000 cues
* Persistence, validation, and binary-search playhead lookup completed in the normal fast test suite
* No database query is required on every playback frame

Restart persistence test:

* Passed for track/default state, Khmer cue text, edited timing, and effective style values after reopening SQLite
* User preset persistence is independent from project deletion

Known issues:

* Live PySide6/QML smoke remains skipped because PySide6 is unavailable in this packaging sandbox
* Basic ASS import reads events but does not preserve arbitrary third-party ASS override tags/styles perfectly
* Colored emoji rendering depends on FFmpeg/libass/font support and is not guaranteed
* Target-language word highlighting is unavailable until real target-language word timing exists
* Final production video rendering remains intentionally deferred

Architecture decisions:

* Subtitle project data is format-neutral and remains independent from SRT/VTT/ASS
* Milliseconds are the canonical timing unit
* Existing transcript/translation edits never get silently overwritten by subtitle source sync
* Project styles are effective snapshots rather than live links to mutable global presets
* Bilingual alignment uses stable source IDs
* Interactive preview is QML overlay; only explicit short burn-in tests use FFmpeg
* Playback lookup is in-memory/binary-search based for large tracks
* Full scene/timeline/rendering features are intentionally outside Phase 12

Recommended next phase:
Phase 13 — Scene Engine and Scene Editor

Suggested Git commit:
`feat: add professional subtitle engine and subtitle studio`

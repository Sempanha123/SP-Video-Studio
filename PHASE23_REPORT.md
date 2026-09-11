PHASE 23 STATUS

Completed:
* Reusable Shorts Maker workflow on the existing Project, Media, Transcript, Scene, Timeline, Subtitle, Dub, Renderer and Export architecture.
* Manual-first candidate selection, transcript/scene ranges, multi-range assembly, manual reframe, captions, hook polish, derived project isolation, Dub-range audio and Timeline silence removal.

Shorts architecture:
* Shorts-only persistence stores workflow metadata, candidates and source ranges. Editable output uses normal Scene/Timeline records; no ShortTimeline, ShortScene, ShortRenderer or Short subtitle engine was created.

Manual highlights:
* Timeline playhead Set In / Set Out creates valid video candidates without AI or transcription.
* Multi-range selections are stored independently and assemble with source gaps removed.

Transcript highlights:
* User can load transcript segments, select exact segments, create a candidate from the selected timing range, or request deterministic timing-boundary suggestions.

Multi-range Shorts:
* Ordered ShortSegment ranges preserve source offsets and assemble sequentially without modifying original media.

Vertical reframing:
* Existing Scene metadata stores non-destructive 9:16/1:1/16:9 manual reframe state with center/left/right/top/bottom presets, zoom, crop and fit/fill behavior.
* Existing layered compositor consumes the same generic render graph; no face tracking is used.

Captions:
* Reuses Phase 12 SubtitleService and subtitle styles. Creator, Bold, Karaoke and Clean presets are exposed.
* Candidate captions are non-destructively regrouped from real transcript words.

Word highlighting:
* Preserved only when real source word timestamps exist. No translated target-word timing is fabricated.

Multilingual support:
* Uses Phase 22 Language Registry rather than hardcoded en/km lists.

English:
* Whitespace-aware caption grouping and existing font/export behavior retained.

Khmer:
* Existing transcript tokens/word timestamps are used; no naive character slicing.

Thai:
* Existing timed tokens are grouped without assuming whitespace boundaries; Unicode is preserved.

Vietnamese:
* Diacritics and word spacing are preserved through caption grouping/persistence.

Multi-speaker:
* Independent derived project duplication retains existing Phase 22 SpeakerProfile/SpeechBlock mappings. Shorts do not create a separate speaker model.

B-roll:
* Reuses Phase 22 V2 layered visual editing and existing Timeline controls.

Picture-in-picture:
* Reuses Phase 22 PIP/presenter visual layers; no Shorts-specific compositor was created.

News integration:
* Scene candidates from News are tagged as News sources. Independent project duplication retains News visual/provenance records before selected scenes are isolated.
* User-authored hooks are supported; Shorts Maker does not invent unsupported factual News claims.

Story integration:
* Selected Story scenes can be derived into independent Shorts while retaining normal Scene/Timeline editing.

Dub integration:
* Ready Phase 21 final dub mixes are detected for manual ranges. Selected dub-audio ranges are assembled into a project-owned Short WAV and applied through the existing generic primary-audio override.
* Duplicated subtitle tracks are trimmed/re-timed to selected contiguous/multi ranges and preserve real word timing where present.

Timeline integration:
* Shorts Maker is a panel inside the existing Phase 17/22 Timeline editor.
* Long-silence suggestions use transcript timing; accepted removals use existing command-backed Timeline split/delete operations so the source media remains unchanged and Undo/Redo stays authoritative.

Export integration:
* Recommended preset IDs are resolved from the existing Phase 16 export registry: TikTok, YouTube Shorts, Instagram Reels, Facebook and Generic variants.
* Export remains the normal ExportService/Renderer path.

New files:
* PHASE23_REPORT.md
* app/phase23_runtime.py
* docs/PHASE23_SHORTS_MAKER.md
* domain/short_candidate.py
* domain/short_project.py
* domain/short_segment.py
* domain/short_style.py
* domain/shorts_errors.py
* services/short_audio_service.py
* services/short_candidate_service.py
* services/short_caption_service.py
* services/short_materialization_service.py
* services/short_reframe_service.py
* services/short_subtitle_range_service.py
* services/short_validation_service.py
* services/shorts_service.py
* storage/migrations/m020_create_shorts.py
* storage/repositories/short_repository.py
* tests/test_phase23_shorts.py
* ui/controllers/shorts_controller.py
* ui/qml/shorts/ShortCandidateCard.qml
* ui/qml/shorts/ShortCandidateList.qml
* ui/qml/shorts/ShortCaptionPanel.qml
* ui/qml/shorts/ShortEditor.qml
* ui/qml/shorts/ShortReadiness.qml
* ui/qml/shorts/ShortReframePanel.qml
* ui/qml/shorts/ShortsSetup.qml
* ui/qml/shorts/ShortsSourcePicker.qml
* ui/qml/shorts/ShortsStudio.qml

Modified files:
* main.py
* pyproject.toml
* rendering/layer_compositor.py
* services/composition_service.py
* storage/migrations/__init__.py
* ui/qml/timeline/TimelineEditor.qml

Tests run:
* Phase 23 targeted suite: 18 passed.
* Phase 22 + Phase 23 combined regression: 33 passed.
* Phase 21 regression: 19 passed.
* Python compileall: passed.
* Full historical repository suite was not available because this execution environment used the GitHub connector plus phase patch workspaces rather than a complete network clone.

Manual Short test:
* Passed manual In/Out candidate, no-AI architecture, target duration validation and vertical FFmpeg reframe coverage.

Multi-range test:
* Passed ordered 3-range assembly metadata with source gaps removed and source media unchanged.

News Short test:
* News source typing/project-isolation path is implemented and structurally covered through generic scene duplication/provenance retention; full News GUI automation was not available in this sandbox.

Story Short test:
* Story source typing/selected-scene independent derivation path is implemented; full Story GUI automation was not available in this sandbox.

Dub Short test:
* Real local FFmpeg range assembly test passed for project-owned dub audio; generic audio-override wiring and subtitle range retiming are implemented.

Thai caption test:
* Passed Thai token grouping/Unicode behavior without character slicing.

Vietnamese caption test:
* Passed Vietnamese spacing/diacritic preservation.

B-roll render test:
* Phase 22 layered compositor regression remained green in the combined suite; Shorts reuses it unchanged for B-roll/PIP.

Word-highlight test:
* Short captions preserve real source word timing; subtitle range trimming also shifts real word timing with the Short.

Silence-removal test:
* Passed command-backed Timeline split/delete ripple path; source media is never modified.

Restart persistence test:
* SQLite reopen persistence passed for Shorts metadata/candidates/ranges and Unicode content.

Known issues:
* Qt multi-video real-time preview remains best-effort; final FFmpeg render is authoritative, consistent with Phase 22.
* Full GUI end-to-end automation and the complete historical repository test suite were unavailable in this patch-only execution environment.
* Scene-selection subtitle re-timing is conservative; precise subtitle range rebuilding is applied to video/transcript/manual/Dub ranged Shorts.
* No social uploading, automatic posting, face tracking, copyrighted-music downloading, cloud highlight AI or engagement prediction is implemented by design.

Architecture decisions:
* Store only Shorts metadata/candidates/ranges in migration 20.
* Derive editable Shorts through authoritative ProjectService duplication, then isolate ordinary Scene/Timeline state.
* Reuse Phase 22 transforms/layers, Phase 12 subtitles, Phase 21 audio override, Phase 17 command stack and Phase 16 export presets.
* Keep deterministic suggestions explicitly labeled Suggested; never store fake viral/retention/engagement scores.
* Preserve original source projects/media as immutable references after derived Short creation.

Recommended next phase:
Phase 24 — Template System

Suggested Git commit:
feat: add multilingual Shorts Maker and highlight workflow

Do not automatically begin Phase 24.

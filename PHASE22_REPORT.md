# PHASE 22 STATUS

Completed:
* Universal manual video-editing architecture on existing Scene/Timeline/Media/Renderer/Export systems.
* Multilingual registry, engine capability matrix, speakers/speech blocks, layered composition, chroma key, word timing and frame snapping.
* Missing root `PHASE21_REPORT.md` included in this delivery.

Universal Video Studio:
* Existing `video` workflow now uses Timeline as the advanced manual studio; Media supports Add-at-Playhead and drag to Timeline.

Language Registry:
* Central JSON-backed registry plus `LanguageService`; registry membership is separate from AI-engine support.

Languages registered:
* English, Khmer, Thai, Vietnamese, Chinese, Japanese, Korean, Indonesian, Malay, Spanish, French, German, Portuguese, Italian and Hindi.

Engine language capabilities:
* faster-whisper reads its installed language mapping; VoxCPM2 uses verified official capability metadata; translation pairs come from providers/models.

English:
* Registered; legacy compatibility retained.

Khmer:
* Registered; legacy compatibility retained.

Thai:
* Registered with Thai font fallbacks, Unicode persistence, STT/TTS capability validation.

Vietnamese:
* Registered with Unicode/diacritic persistence and engine capability validation.

Additional languages:
* 11 additional initial catalog languages; architecture can expand through resource updates/plugins.

Speakers:
* Project SpeakerProfile with narrator/reporter/host/interviewer/guest/character/expert/speaker/custom roles and independent Voice assignment.

Speech blocks:
* Per-section ordered SpeechBlock with speaker, language, voice override, pauses, source type and scene/timeline mapping.

Multi-speaker TTS:
* Per-block voice resolution priority and TTS generation metadata; source/manual-audio blocks are not automatically replaced.

Manual video editing:
* Video/image/audio Add-at-Playhead; media drag; text remains existing Scene overlay; AI/script is optional.

Layered video:
* Existing SceneLayer upgraded with normalized transforms, crop, opacity, rotation, flip, timing, z-order, role, audio and metadata.

Picture-in-picture:
* Top-left, top-right, bottom-left, bottom-right and center presets plus manual transforms.

B-roll:
* V2 B-roll layers; source audio off by default.

Presenter/Character video:
* Presenter/reporter/host/interview/character roles with optional speaker identity and source audio behavior.

Green screen:
* Non-destructive green/blue/custom chroma settings; runtime FFmpeg filter validation; final renderer implementation.

Interview workflow:
* Multiple speakers, independent voices, SpeechBlocks, interview visual roles and source-audio-safe behavior.

Word-level editing:
* Edit real transcript words, millisecond timing, split/merge service, safe text reconstruction and transcript-backed subtitle-word synchronization.

Frame snapping:
* Deterministic millisecond/frame conversion and HH:MM:SS:FF helper; Timeline frame-step shortcuts.

News manual media:
* Generic SceneLayer/Timeline path is workflow-independent; News scenes can use B-roll/presenter/interview media without News-only render logic.

News reporter workflow:
* Generic reporter/presenter roles + speaker relation + chroma/PIP/lower-third existing overlays support the reporter composition pattern.

Renderer integration:
* Existing Phase 15 SceneRenderer is wrapped, not forked. Layer order, transforms, crop, opacity, rotation, flip, chroma and opted-in layer audio map to FFmpeg.

Timeline integration:
* V1 Main, V2 B-roll/Graphics and V3 Presenter/Overlay are functional projections; different tracks may overlap.

Legacy migration:
* Migration 19 is additive. Existing en/km projects, scripts, Scenes and Timelines remain valid; old ScriptSection content lazily becomes one speech block.

New files:
* PHASE21_REPORT.md, app/phase22_runtime.py, docs/PHASE22_UNIVERSAL_VIDEO_STUDIO.md, domain/chroma_key.py, domain/manual_audio_clip.py, domain/phase22_errors.py, domain/speaker_profile.py, domain/speech_block.py, rendering/layer_compositor.py, resources/languages.json, services/composition_service.py, services/frame_time_service.py, services/language_service.py, services/multispeaker_tts_service.py, services/speaker_service.py, services/speech_block_service.py, services/universal_video_service.py, services/visual_layer_service.py, services/word_timing_service.py, storage/migrations/m019_create_universal_video_studio.py, storage/repositories/phase22_repository.py, tests/test_phase22_universal_video.py, ui/controllers/language_controller.py, ui/controllers/video_studio_controller.py, ui/controllers/word_timing_controller.py, ui/qml/components/LanguagePicker.qml, ui/qml/editor/WordTimingEditor.qml, ui/qml/video/SpeakerManager.qml, ui/qml/video/SpeechBlockEditor.qml, ui/qml/video/UniversalVideoPanel.qml, ui/qml/video/VisualLayerInspector.qml

Modified files:
* .pytest_cache/.gitignore, .pytest_cache/CACHEDIR.TAG, .pytest_cache/README.md, .pytest_cache/v/cache/lastfailed, .pytest_cache/v/cache/nodeids, domain/language.py, domain/project.py, domain/scene_layer.py, domain/timeline_track.py, domain/transcript.py, main.py, pyproject.toml, services/timeline_mapping_service.py, storage/migrations/__init__.py, ui/qml/components/MediaCard.qml, ui/qml/dubbing/DubSetup.qml, ui/qml/editor/TranscriptEditor.qml, ui/qml/editor/TranscriptionPanel.qml, ui/qml/editor/TranslationSetupDialog.qml, ui/qml/timeline/TimelineEditor.qml

Tests run:
* Phase 22 targeted suite: 15 passed. Phase 21 regression suite: 19 passed. Python syntax compilation: passed.
* A complete checkout of every historical repository test was not available in this execution sandbox; GitHub was accessible through the repository connector rather than a networked clone.

Language capability tests:
* Passed service-level registry/provider/VoxCPM metadata checks.

Thai Unicode test:
* Passed.

Vietnamese Unicode test:
* Passed.

Legacy project test:
* Legacy en/km Project validation and lazy legacy ScriptSection speech-block migration passed targeted tests.

Multi-speaker test:
* Reporter/Guest/Reporter ordering, speaker persistence and voice-resolution priority passed.

Green-screen render test:
* Passed actual local FFmpeg render with chroma-key-capable FFmpeg 7.1.5.

PIP render test:
* Passed actual local FFmpeg layered render.

Three-layer render test:
* Passed actual local FFmpeg main canvas + V2 + V3 layered render path.

Normal-video manual test:
* Manual no-AI service path, visual-layer safety and FFmpeg composition covered by targeted tests; full GUI automation was not run.

News realism integration test:
* Generic renderer/Scene layer architecture supports the requested composition; full News GUI end-to-end automation was not run in this sandbox.

Restart persistence test:
* Speakers, speech blocks and Unicode SQLite reopen/persistence passed.

Known issues:
* Qt real-time multi-video PreviewPlayer is not claimed frame-perfect; final FFmpeg render is authoritative.
* Full historical repository test suite and GUI automation were not executable without a complete local repository checkout.
* No lip sync, face animation, arbitrary masks, animation keyframes or advanced grading by design.

Architecture decisions:
* Reuse SceneLayer/Timeline/Media/Voice/Subtitle/Renderer/Export; store normalized transforms; store layer extensions in metadata for backward-compatible schema; add only speakers/speech blocks/manual-audio/state tables; keep engine capability separate from language registry.

Recommended next phase:
Phase 23 — Shorts Maker

Suggested Git commit:
`feat: add universal multilingual layered video studio`

Do not automatically begin Phase 23.

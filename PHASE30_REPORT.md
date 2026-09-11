PHASE 30 STATUS

Completed:

* Implemented Phase 30 only: a persistent, multi-track video-production audio mixer layered on the existing Timeline, Speaker/SpeechBlock, Dub, Asset, Template, Batch, Phase 29 cache, and final FFmpeg renderer systems.

Audio architecture:

* Added one generic signal flow: existing Timeline-derived audio clip → clip gain/pan/fade/effects → Track → Bus → Master → optional loudness normalization → limiter → existing `FFmpegRenderer`; no `AudioProject`, second Timeline, or second renderer was introduced.

Tracks:

* Added persistent logical audio tracks with Voice, Dialogue, Narration, Source Audio, Music, SFX, Ambience, B-roll Audio, Dub, and General roles, plus workflow-specific defaults and user rename/add controls.

Buses:

* Added simple Voice, Music, SFX, and Source buses feeding Master. Tracks route to one bus; no arbitrary DAW routing graph is created.

Clip gain:

* Added per-clip non-destructive dB gain, pan, mute, fade-in/fade-out, route override, and effect metadata on top of canonical Timeline timing.

Track gain:

* Added -60 dB..+12 dB track gain with creator-friendly fader persistence on release/debounce.

Master:

* Added persistent master gain, conservative limiter, optional loudness-normalization target, preset metadata, and mix preview fingerprinting.

Mute/Solo:

* Added clip/track mute and multi-track Solo. Muted buses consume routed tracks rather than leaking them to Master.

Pan:

* Added stereo -1..+1 pan/balance. Mono sources are normalized to stereo first; stereo sources use predictable balance-style channel scaling.

Fades:

* Added non-destructive per-clip fade-in/fade-out, rendered through FFmpeg `afade`.

Crossfades:

* Added simple overlapping clip crossfade metadata with Linear or equal-power-style `qsin` fade curves; no full automation editor.

Waveforms:

* Added lazy downsampled min/max waveform summaries for WAV, compressed audio, and video-audio. Waveforms use Phase 29 `audio/waveforms/` safe cache and regenerate if removed.

EQ:

* Added ordered/bypassable Gain, High-pass, Low-pass, and conservative 3-band EQ effects plus Clear Voice/Warm Voice presets.

Compression:

* Added simple FFmpeg compressor settings for threshold, ratio, attack, release, and makeup gain plus a Gentle Compressor preset.

Limiter:

* Added conservative Master limiter by default and support for explicit limiter effects; unsupported FFmpeg filters fail clearly instead of being silently ignored.

Loudness analysis:

* Added offline peak analysis and integrated-LUFS guidance through FFmpeg `volumedetect`/`loudnorm` where available. It is guidance, not claimed broadcast mastering.

Normalization:

* Added opt-in non-destructive loudness/peak normalization calculations and optional Master loudnorm render stage; sources are never rewritten.

Ducking:

* Added generic timing-based `AudioDuckingService` for Voice→Music, Dub→Original, and other Track/Bus routes with configurable amount, attack, and release.

Multi-speaker audio:

* Reuses Phase 22 SpeakerProfile/SpeechBlock IDs/audio. Narrator routes to Narration, Reporter/Presenter to Voice, and Guest/Character/Interview roles to Dialogue while preserving speaker/language/text metadata.

News audio:

* Added Reporter/Narration, Interview, Source, B-roll, Music, and SFX defaults; B-roll starts muted in narration-driven News and Music can duck under Reporter voice.

Interview audio:

* Independent Reporter, Guest, Ambience, and Music tracks support gain, mute, solo, pan, routing, ducking, and common effects.

Story audio:

* Added Narration, Character Voices, Music, Ambience, and SFX defaults with Story preset balance.

Shorts audio:

* Added Source Audio, Voice, Music, and SFX defaults with Shorts preset; captions remain independent.

Dub integration/migration:

* Phase 21 Original/Dub volume/mode/duck settings migrate lazily into the generic mixer once; old Dub records remain authoritative and are not deleted. Convenience presets: Dub Only, Dub + Quiet Original, Dub + Original.

Asset integration:

* Phase 25 Music/SFX/Ambience subtypes route to matching audio tracks; asset drag now exposes `assetSubtype` so Timeline can distinguish Music vs SFX.

Template integration:

* Phase 24 templates can store ID-free semantic audio mixer settings for track/bus roles, gains, effects, ducking, and Master configuration without project-specific UUID leakage.

Batch integration:

* Phase 26 Batch inherits Phase 24 mixer settings through normal template application; Batch does not implement its own mixer.

Renderer integration:

* Extended existing `RenderPlan` to schema 2 with optional `AudioMixSpec` and extended existing `FFmpegRenderer` to render one temporary project mix WAV before the normal final encode. Legacy projects without a Phase 30 mix keep the previous audio path.

New files:

* `app/phase30_runtime.py`
* `domain/audio_track.py`
* `domain/audio_clip.py`
* `domain/audio_bus.py`
* `domain/audio_effect.py`
* `domain/audio_mix.py`
* `domain/audio_meter.py`
* `domain/ducking_rule.py`
* `domain/audio_errors.py`
* `services/audio_mixer_service.py`
* `services/audio_analysis_service.py`
* `services/audio_waveform_service.py`
* `services/audio_ducking_service.py`
* `services/audio_render_service.py`
* `services/audio_validation_service.py`
* `storage/repositories/audio_mix_repository.py`
* `storage/migrations/m025_create_audio_mixer.py`
* `ui/controllers/audio_mixer_controller.py`
* `ui/qml/audio/AudioMixer.qml`
* `ui/qml/audio/MixerTrack.qml`
* `ui/qml/audio/MixerStrip.qml`
* `ui/qml/audio/MixerBus.qml`
* `ui/qml/audio/AudioInspector.qml`
* `ui/qml/audio/AudioMeter.qml`
* `ui/qml/audio/WaveformView.qml`
* `ui/qml/audio/MasterStrip.qml`
* `ui/qml/audio/DuckingPanel.qml`
* `tests/test_phase30_audio_mixer.py`
* `docs/PHASE30_PROFESSIONAL_AUDIO_MIXER.md`
* `PHASE30_REPORT.md`

Modified files:

* `main.py`
* `pyproject.toml`
* `domain/storage_category.py`
* `services/cache_service.py`
* `storage/migrations/__init__.py`
* `rendering/render_plan.py`
* `rendering/renderer.py`
* `ui/qml/timeline/TimelineEditor.qml`
* `ui/qml/assets/AssetCard.qml`
* `ui/qml/assets/ProjectAssetPanel.qml`
* `ui/qml/news/NewsStudio.qml`
* `ui/qml/story/StoryStudio.qml`
* `ui/qml/dubbing/TranslateDubStudio.qml`
* `README.md`

Tests run:

* Phase 30 focused audio/mixer suite: 48/48 passed.
* Available Phase 22–30 cumulative regression suite: 285/285 passed.
* Separate Phase 21 dubbing regression: 19/19 passed.
* Real FFmpeg/FFprobe audio tests passed on FFmpeg 7.1.5: WAV mixing, ducking, 44.1 kHz + 48 kHz inputs, mono + stereo inputs, 48 kHz stereo output, loudness/peak analysis, MP3/video-audio waveform decode.
* Python compile passed for all Phase 30 Python files.
* QML structural brace audit passed for 15 Phase 30 changed/new mixer/workflow QML files.
* PySide6 and qmllint are unavailable in this sandbox, so live desktop QML execution/lint could not be run here.

Basic mix test:

* PASS — real FFmpeg mix rendered Narration/Voice + Music with configured dB levels into a valid 48 kHz stereo WAV.

News ducking test:

* PASS — timing-based Voice Bus trigger generated Music Bus -12 dB envelope with attack/release, and the real FFmpeg mix rendered successfully.

Interview test:

* PASS — real Reporter + Guest + Ambience mix verified independent gain/pan and multi-solo behavior.

Multi-speaker test:

* PASS — Narrator→Narration, Reporter→Voice, Guest/Character→Dialogue routing is tested; Khmer `អ្នករាយការណ៍`, Thai `ผู้สื่อข่าว`, Vietnamese `Phóng viên`, and English labels round-trip correctly.

Dub migration test:

* PASS — legacy Original 20% / Dub 100% / Duck configuration maps to equivalent dB gains and generic ducking without deleting old Dub data.

Waveform test:

* PASS — WAV, MP3, and video-audio waveform summaries generated; second lookup hits cache; deletion regenerates safely.

Fade/crossfade test:

* PASS — FFmpeg graph contains clip fade-in/out; overlapping clips receive deterministic Linear/equal-power-style crossfade metadata.

Loudness test:

* PASS — real FFmpeg peak and integrated LUFS analysis returned stable finite values; normalization gain remains non-destructive and bounded.

Clipping/limiter test:

* PASS — static validation warns on extreme mix settings and the generated Master graph includes the conservative limiter when enabled.

News Reporter end-to-end test:

* PASS for the Phase 30 audio acceptance path — real Reporter/Voice + background Music with ducking renders through the Phase 30 FFmpeg graph; renderer-source audit confirms the existing final renderer consumes `AudioMixSpec`. Full visual News render execution could not be launched from this reconstructed test workspace because Phase 1–20 renderer support modules are not all materialized here.

Interview end-to-end test:

* PASS for the Phase 30 audio acceptance path — real Reporter + Guest + Ambience mix renders successfully with independent tracks. Full desktop visual/subtitle render was not executable in this reconstructed sandbox for the same support-module limitation.

Batch audio test:

* PASS structural/integration — Template mixer export strips project UUIDs, applies by semantic Track/Bus roles to a new project, preserves ducking/effects, and Phase 30 runtime patches Phase 24 template apply, which is the existing Phase 26 Batch path.

Large-project performance test:

* PASS — 120 audio clips build a mix spec without waveform decoding or synchronous audio analysis; waveforms remain lazy cached summaries.

Manual listening check:

* NOT AVAILABLE in this execution sandbox because there is no audio-output device/listening channel. Representative real WAV mixes were rendered and validated structurally/with FFprobe, but no claim of subjective listening is made.

Restart persistence test:

* PASS — track gain/pan/mute/solo and Master limiter/normalization state persist through a fresh `AudioMixRepository` instance against the same SQLite database.

Known issues:

* PySide6/qmllint and an audio output device are unavailable here, so live GUI QA and subjective listening could not be performed.
* The reconstructed Phase 30 test workspace contains the cumulative Phase 21–29 logic needed for regression but not every Phase 1–20 renderer support file; real Phase 30 audio FFmpeg execution is tested, while complete visual News/Interview final-render execution is source-audited rather than launched here.
* Qt realtime playback cannot guarantee exact parity with FFmpeg EQ/compressor/ducking; rendered audio preview/final output is authoritative for complex effects.
* Full point automation, VST/plugin hosting, source separation, pitch correction, surround mixing, and true-peak broadcast mastering remain intentionally out of scope.

Architecture decisions:

* Existing Timeline/Scene/SpeechBlock/GeneratedAudio/MediaAsset/Dub records remain canonical; Phase 30 stores mixer metadata and derives clip timing instead of duplicating it.
* FFmpeg audio graph generation is centralized in `AudioRenderService`; final mux/encode remains the existing `FFmpegRenderer`.
* Phase 21 Dub migration is lazy/additive so pre-Phase-30 projects preserve behavior and data.
* Waveform and mix-preview derivatives use Phase 29 disposable cache; source audio and active generated narration are never treated as normal cache.
* Template/Batch audio settings use semantic roles rather than project UUIDs, keeping reusable templates deterministic.

Recommended next phase:
Phase 31 — Performance Optimization

Suggested Git commit:
feat: add professional multi-track audio mixer

Do not automatically begin Phase 31.

# Phase 30 — Professional Audio Mixer

Phase 30 extends MMO Video Studio's existing Timeline, Scene, SpeechBlock, GeneratedAudio, MediaAsset, Dub, Asset Library, Template, Batch, Cache, and final FFmpeg renderer architecture. It deliberately does **not** create an `AudioProject`, a separate audio timeline, or a second renderer.

## Signal flow

The persisted/derived mix follows one deterministic path:

`Timeline/Scene audio clip → clip gain/pan/fades/effects → audio track → track gain/pan/effects → bus → bus gain/effects/ducking → master gain → optional loudness normalization → safety limiter → existing final renderer`

Timeline timing remains authoritative. Phase 30 stores mixer metadata and clip mix overrides only. Existing narration, source-video audio, manual audio, multi-speaker SpeechBlocks, and Dub outputs remain owned by their original systems.

## Tracks and roles

Tracks have stable IDs, project ownership, display names, role metadata, ordering, dB gain, stereo pan, mute, multi-solo, enabled state, bus routing, timestamps, and metadata. Supported logical roles are Voice, Dialogue, Narration, Source Audio, Music, SFX, Ambience, B-roll Audio, Dub, and General.

Workflow defaults are created only when a project first enters the mixer. Normal Video uses Source Audio, Voice, Music, and SFX. News adds Reporter/Narration, Interview, and B-roll Audio. Story adds Narration, Character Voices, Music, SFX, and Ambience. Dub uses Dub Voice, Original Audio, and Music/Ambience. B-roll audio is muted by default for narration-driven News/Story projects but remains user-enableable.

## Clip mixing

Clip timing is derived from the current Timeline rather than duplicated. `audio_clip_mix` stores optional per-Timeline-clip overrides: route, gain dB, pan, fade in/out, mute, small effect metadata, and source metadata. Gain is bounded to -60 dB..+12 dB and pan to -1..+1. Fade metadata is non-destructive.

Source video audio remains linked to the Scene/Timeline source by default. Deleting or changing mixer metadata never rewrites the video or user recording. Existing Scene narration/source-volume values are converted to dB when building the generic mix so legacy behavior is preserved.

## Buses and master

Phase 30 uses simple fixed-depth routing rather than a DAW graph. Default buses are Voice, Music, SFX, and Source; tracks route to one bus and buses feed Master. Bus gain and mute are supported. Master stores gain, a conservative limiter, optional loudness normalization target, preset name, and metadata.

The default limiter is enabled for peak safety. It can be disabled by the user, but validation can still warn about likely clipping. Full true-peak/broadcast mastering is intentionally out of scope.

## Mute and solo

Track mute disables all clips on the track. Solo is multi-select: if one or more enabled tracks are soloed, only those tracks are rendered. Bus mute consumes routed tracks and never leaks them directly to Master. Clip mute is also respected.

## Pan and channel handling

Phase 30 normalizes mix inputs to 48 kHz stereo in the FFmpeg graph. Mono inputs are converted to stereo before pan. Stereo sources use a conservative left/right balance-style pan: center preserves both channels, left reduces the right channel, and right reduces the left channel. Surround editing is out of scope; incompatible sources are normalized to the stereo project mix.

## Fades and crossfades

Per-clip fade in/out is supported. Linear fades are the base behavior. Equal-power-style crossfade metadata uses FFmpeg's `qsin` fade curve when two compatible overlapping clips are configured through the simple crossfade helper. There is no full automation/keyframe editor.

## Effects

`AudioEffectSpec` provides an ordered, bypassable chain for Clip, Track, Bus, or Master owners. Initial effects are Gain, High-pass, Low-pass, three-band EQ, Compressor, and Limiter. Voice presets are intentionally conservative: Clear Voice, Warm Voice, and Gentle Compressor. Unsupported FFmpeg filters fail with a typed `AudioEffectUnavailable` error instead of being silently ignored.

## Ducking

`AudioDuckingService` generalizes the older Dub ducking model. Ducking is timing-based and deterministic: known Voice/Dub clip regions generate a volume envelope for Music, Source, or another target Track/Bus. Attack, release, and duck amount are user-adjustable. No realtime sidechain detector is required.

The default News/Voice Focus behavior can lower Music while Voice clips are active and restore it between clips. Dub presets support Dub Only, Dub + Quiet Original, and Dub + Original without duplicating the Phase 21 mixer.

## Multi-speaker audio

Phase 22 SpeakerProfile/SpeechBlock IDs remain authoritative. Phase 30 projects existing generated SpeechBlock audio into mixer tracks. Narrator routes to Narration, Reporter/Presenter/Host to Voice, and Guest/Character/Interview/Dialogue to Dialogue. Speaker name, language, short text, speaker ID, and original audio ID remain metadata for display and routing.

Unicode speaker labels are preserved for English, Khmer, Thai, and Vietnamese.

## Waveforms

`AudioWaveformService` generates lazy, downsampled min/max peak summaries. QML never decodes full PCM. WAV can be read directly; compressed audio and video-audio are decoded to temporary mono 8 kHz PCM through FFmpeg for analysis only. Waveform JSON is keyed by source path/stat fingerprint, bucket count, and waveform version.

Waveforms live under the Phase 29 managed cache category `audio/waveforms/`. The cache is `SAFE_TO_CLEAR`, rebuilds on demand, and is intentionally excluded from generated narration cleanup semantics.

## Loudness and normalization

`AudioAnalysisService` uses FFmpeg `volumedetect` for peak guidance and `loudnorm` analysis when available. It reports peak dB and integrated LUFS when FFmpeg can provide it. Normalization is opt-in and non-destructive: the mixer stores a target/gain policy, never rewrites source files. Phase 30 does not claim full broadcast-grade true-peak mastering.

## FFmpeg render graph

The existing `FFmpegRenderer` remains the final video renderer. `RenderPlan` schema version 2 can carry `audioMixSpec`. When a project has a Phase 30 mix with clips, the existing renderer asks `AudioRenderService` for a temporary project mix WAV, then maps that WAV into the existing final video encode. Projects without a Phase 30 mix retain the previous audio override/source-audio behavior.

The centralized audio graph uses safe subprocess arguments and filters such as `atrim`, `asetpts`, `aresample`, `aformat`, `adelay`, `volume`, `afade`, `pan`, `equalizer`, `highpass`, `lowpass`, `acompressor`, `alimiter`, `loudnorm`, and `amix` where supported. Final project audio is 48 kHz stereo unless existing export settings specify the encoded audio codec/bitrate.

## Preview

Complex mix preview renders a temporary WAV through the same audio graph. Preview keys include clips, gains, pans, fades, effects, ducking, buses, and master settings. Preview WAVs are Phase 29 Preview Cache and are disposable. Qt realtime playback may not exactly reproduce the FFmpeg effect graph; rendered audio preview is the authoritative effect preview.

## Legacy Dub migration

Pre-Phase-30 Phase 21 values map lazily into the generic mixer once: Original/Dub linear volumes become dB gains, Replace maps to Original mute, and Duck creates a generic track ducking rule using the prior normal/under ratio and fade timing. Old dubbing records are not deleted or rewritten.

## Asset Library integration

Phase 25 audio subtypes map Music → Music, SFX → SFX, Ambience → Ambience, and other audio → General. Dragging from the project Asset panel exposes `assetSubtype`, so Timeline drop chooses SFX or Music where possible. Asset source files and rights metadata remain owned by the Asset Library.

## Template and Batch integration

Phase 24 templates may carry ID-free semantic mixer settings in template/component metadata under `audioMixer`, `audioMix`, or `mixer`. Tracks/buses/effects/ducking use semantic roles rather than project UUIDs. Template application maps those roles to the target project's mixer. Phase 26 Batch already applies templates, so Batch inherits the same mixer settings rather than implementing a second batch audio mixer.

## Undo/autosave/project lifecycle

Phase 30 bridges mixer edit commands into Phase 17's existing command stack. Track gain/pan/mute/solo, clip mix, master gain, ducking, track creation, and preset application use that history bridge. UI fader/pan changes persist on release/debounce rather than writing continuously while dragging. SQLite persistence is immediate for committed controls and remains compatible with Phase 27 project snapshots/autosave.

Project duplication remaps buses, tracks, effects, ducking endpoints, master settings, and optional clip IDs. Project deletion uses SQLite `ON DELETE CASCADE` for mixer metadata only; source files, Global Assets, and external media are never mixer deletion targets.

## Database

Migration 25 adds:

- `audio_buses`
- `audio_tracks`
- `audio_clip_mix`
- `audio_effects`
- `audio_ducking_rules`
- `audio_mix_settings`

No separate audio-project/timeline table is created.

## UI

The Phase 28 Soft Creator Studio style is retained. Timeline gains an Audio tab with a docked mixer. Beginner controls emphasize Volume, Mute, Fade, and Music Ducking. Advanced controls expose Tracks, Buses, Pan, effects, limiter, and loudness options without mimicking an intimidating hardware console. News, Story, and Translate & Dub expose an Open Mixer action that routes to the existing Timeline workspace.

## Performance and cache behavior

Waveforms are lazy and downsampled. No project startup decodes every audio file. Mixer state is metadata-only. FFmpeg mix preview is generated only when requested and cached. Tests cover 100+ clip spec construction without synchronous waveform analysis. Phase 29 owns waveform/preview cleanup and can rebuild them when missing.

## Safety boundaries

Phase 30 never destructively edits source recordings or generated narration, never determines copyright automatically, never hosts plugins/VSTs, never performs source separation/voice conversion, and never creates a second renderer. Missing media uses the existing media/relink ownership path. Unsupported effects are reported clearly.

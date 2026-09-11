
## Phase 30 — Professional Audio Mixer

Phase 30 adds a persistent multi-track video-production mixer without creating a second timeline or renderer. Existing Timeline/Scene/SpeechBlock/GeneratedAudio/MediaAsset/Dub records remain canonical; mixer metadata adds track/bus routing, dB gain, pan, mute/multi-solo, fades, simple crossfades, ordered basic effects, timing-based ducking, master limiting, loudness guidance, lazy waveform cache, and rendered mix preview.

The existing `FFmpegRenderer` accepts an optional `AudioMixSpec`; projects with Phase 30 audio render one temporary 48 kHz stereo mix through `AudioRenderService`, while legacy projects keep the previous source/override path. Phase 21 Dub settings migrate lazily, Phase 22 speakers keep their IDs/languages, Phase 25 Music/SFX assets route by subtype, Phase 24 templates store semantic mixer roles, Phase 26 Batch inherits those template settings, Phase 27 remains responsible for project recovery, and Phase 29 owns waveform/mix-preview cache cleanup.

See `docs/PHASE30_PROFESSIONAL_AUDIO_MIXER.md` for signal flow, routing, effects, ducking, waveform/cache behavior, migration, Template/Batch integration, renderer details, safety boundaries, and performance notes.

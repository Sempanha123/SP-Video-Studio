
## Phase 30 — Professional Audio Mixer

Phase 30 adds a persistent multi-track video-production mixer without creating a second timeline or renderer. Existing Timeline/Scene/SpeechBlock/GeneratedAudio/MediaAsset/Dub records remain canonical; mixer metadata adds track/bus routing, dB gain, pan, mute/multi-solo, fades, simple crossfades, ordered basic effects, timing-based ducking, master limiting, loudness guidance, lazy waveform cache, and rendered mix preview.

The existing `FFmpegRenderer` accepts an optional `AudioMixSpec`; projects with Phase 30 audio render one temporary 48 kHz stereo mix through `AudioRenderService`, while legacy projects keep the previous source/override path. Phase 21 Dub settings migrate lazily, Phase 22 speakers keep their IDs/languages, Phase 25 Music/SFX assets route by subtype, Phase 24 templates store semantic mixer roles, Phase 26 Batch inherits those template settings, Phase 27 remains responsible for project recovery, and Phase 29 owns waveform/mix-preview cache cleanup.

See `docs/PHASE30_PROFESSIONAL_AUDIO_MIXER.md` for signal flow, routing, effects, ducking, waveform/cache behavior, migration, Template/Batch integration, renderer details, safety boundaries, and performance notes.

## Phase 31 — Performance Optimization

Phase 31 keeps the existing creator architecture and final renderer intact while optimizing measured editor hot paths. Asset metadata is bulk-fetched instead of using per-card N+1 queries, subtitle playback uses bounded indexed lookup, Batch counters use aggregate SQL, unchanged media metadata reuses a bounded FFprobe cache, and Phase 30 waveform generation deduplicates concurrent requests and supports cached density levels.

The shared WorkerPool is now bounded and priority-aware (Interactive / Normal / Background), stale preview/thumbnail requests carry request versions so late work cannot replace current UI state, and Settings → Performance exposes Auto / Low Memory / Balanced / Maximum Quality plus preview quality and worker limits. Phase 31 does not preload VoxCPM2, Whisper, or translation models and does not change final render resolution/quality.

See `docs/performance.md` for the profiling method, measured before/after numbers, cache/index strategy, worker/model lifecycle, memory-scope results, and target-machine measurements that still require a real Windows/PySide6/CUDA environment.

PHASE 21 STATUS

Completed:
* Translate & Dub domain, persistence, timing, segment generation, audio mixing, subtitle/render adapters, UI surface and tests.

Dubbing architecture:
* Reuses existing STT, translation, Voice Studio, VoxCPM2, subtitle, timeline, render and export systems.

Source video:
* Project-managed video selection with source/target language validation; original video remains unchanged.

Transcription integration:
* Existing transcript IDs are linked; no second STT implementation.

Translation integration:
* Existing TranslationSegment IDs/timestamps are preserved and dubbed from reviewed `translated_text`.

Voice integration:
* Existing VoiceService resolves project/per-segment voices and keeps reference-voice permission checks.

Dub segments:
* Independent persistent segments support lock, regenerate, manual audio replacement, speaker label and stale detection.

Timing analysis:
* Fits/short/long/very-long/needs-review classification with actual generated duration.

Time stretching:
* Safe configurable fit range with chained FFmpeg atempo; extreme stretch is not automatic.

Overlap detection:
* Target speech overlap is detected and blocks final mix until reviewed.

Audio mixing:
* Replace, Mix, Duck and Custom modes; 48 kHz stereo PCM intermediate artifacts.

Background-audio handling:
* Original track can be mixed/ducked; no false claim of vocal removal/source separation.

Subtitle integration:
* Target and bilingual tracks use existing SubtitleService.

Timeline integration:
* Dub Voice logical blocks preserve source transcript timing and use target offsets.

Renderer integration:
* Generic `primary_audio_override` keeps existing renderer/export pipeline and source video duration.

English → Khmer:
* Supported by multilingual project/segment architecture.

Khmer → English:
* Supported with Unicode-safe text/hash/persistence.

AI resource coordination:
* Existing STT/translation/TTS services and AIResourceManager remain authoritative; segment TTS runs sequentially.

New files:
* Phase 21 domain/services/repository/migration/worker/controller/QML/runtime/docs/tests.

Modified files:
* migration registry, render plan/renderer, Translation page, main entry point and pyproject script entry.

Tests run:
* Phase 21 automated suite: 19 passed; the full historical suite requires the complete repository checkout.

Too-long segment test:
* Passed.

Overlap test:
* Passed.

Translation-change test:
* Passed.

Voice-change test:
* Passed.

Khmer dub listening check:
* Requires a local installed VoxCPM2 model and manual listening on the target machine.

Audio-mix test:
* FFmpeg command/fingerprint coverage passed; real listening remains environment-dependent.

Render test:
* Generic renderer override is implemented and structurally tested; full real-media render requires local FFmpeg fixtures.

Project-duplication test:
* New dub IDs are generated; original generated-audio IDs are not retained and copied audio can be remapped to the duplicate project.

Restart persistence test:
* Passed using a reopened SQLite repository.

Known issues:
* Real-model listening/render validation depends on locally installed models and FFmpeg/media fixtures.

Architecture decisions:
* No duplicate STT/translation/voice/subtitle/timeline/renderer architecture; original video timing is canonical.

Recommended next phase:
Phase 22 — Normal Video Studio

Suggested Git commit:
feat: add translate and dub production workflow

Do not automatically begin Phase 22.

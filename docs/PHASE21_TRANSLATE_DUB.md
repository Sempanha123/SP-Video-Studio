# Phase 21 — Translate & Dub

Phase 21 adds a local, segment-based narration dubbing workflow on top of the existing media, transcription, translation, Voice Studio, VoxCPM2, subtitles, timeline, renderer and export systems.

## Pipeline

Source video → existing transcription → reviewed transcript → existing translation → reviewed `translated_text` → target voice → per-segment TTS → timing analysis → narration track → original-audio mix → subtitles → existing renderer/export.

The original source video timeline remains canonical. Transcript timestamps are never rewritten by dub timing edits. Each `DubSegment` stores its own offset, timing mode and generated-audio relationship.

## Persistence

Migration 18 creates `dubbing_projects`, `dub_segments`, `dub_audio_outputs` and `dub_mix_settings`. Audio stays on disk under the project; WAV data is never stored in SQLite. Segment state, timing, locks, mix settings and final-output metadata survive restart.

## Timing

Natural mode keeps generated speech unchanged. Fit Segment uses configurable safe tempo limits and FFmpeg `atempo` chains. Extreme fitting is marked for review instead of silently distorting speech. Extend Segment may exceed the source window and is checked for overlap. The source video itself is not re-timed.

## Audio

Generated segment WAV files remain independent so one line can be regenerated without rebuilding every line. Final narration is assembled at 48 kHz stereo PCM. Mix modes are Replace, Mix, Duck and Custom. Duck mode lowers the original track during dubbed speech; it is not source separation and original speech may remain audible.

## Voice safety

Phase 21 reuses Voice Studio. Preset, designed and authorized reference voices are supported. Reference-voice permission remains enforced by Voice Studio. Source speakers are never cloned automatically and no public-figure voice presets are added.

## Subtitles / Timeline / Render

Target and bilingual subtitle tracks are created through the existing SubtitleService. Dub blocks expose logical `Dub Voice` timeline placement without modifying source transcript timing. `RenderPlan.primary_audio_override` is generic renderer support used to replace the combined scene audio with a ready final dub mix while keeping the video duration fixed.

## Recovery and resources

Generation is segment-based and resumable. Pending, failed and outdated unlocked rows are candidates; completed and locked rows are skipped. Failed regeneration preserves the last working audio. TTS remains serialized through the existing VoxCPM2/TTS resource path, and the existing AI resource manager continues coordinating STT, translation and TTS models.

## Limits

Phase 21 does not implement lip sync, face animation, automatic speaker diarization, source-speaker cloning, cloud dubbing, heavy source separation, automatic publishing, Batch Factory or AI video generation.

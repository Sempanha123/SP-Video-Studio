# Phase 32 — Manual Speech & TTS Editor

Phase 32 adds one reusable manual speech workspace across MMO Video Studio. It **does not** add a second TTS engine, subtitle model, timeline, or audio mixer. `SpeechBlock` remains the canonical speech segment, `GeneratedAudio` remains take history, Phase 22 multi-speaker TTS remains the generator, Phase 17 Timeline remains the timing view, Phase 27 remains the save/recovery coordinator, and Phase 30 remains the audio-routing/mix layer.

## Canonical SpeechBlock extension

Migration 27 adds project ownership, absolute `timeline_start_ms` / `timeline_end_ms`, `active_generated_audio_id`, text hash, audio/timing statuses, and `user_modified`. Legacy `audio_id` and `start_offset_ms` stay mirrored so existing Phase 22/30 paths remain compatible. Old rows are backfilled without deleting generated audio.

A text, speaker, voice, language, or source-type edit recalculates the text hash and marks the current generated take **Outdated** instead of deleting it. Generation is explicit. The active take changes only after successful generation; failure/cancellation keeps the last good take available.

## Shared editor

`ui/qml/speech/SpeechEditor.qml` is a virtualized `ListView` workspace with recycled delegates. It exposes Select, Start, End, Speaker, Language, editable Text, Voice Profile, Duration Status, Audio Status, and Actions. The toolbar supports Add, Split, Merge, Delete, Find/Replace, bulk speaker/voice/language assignment, status-based selection, and selected/outdated/all generation.

Only the active text row instantiates an editor. Start/end values display as millisecond timecodes while canonical storage remains integer milliseconds. Keyboard actions include Ctrl+Enter, Ctrl+F, Delete, and Space when text entry is not active.

## Voice resolution and generation

Voice resolution remains:

1. SpeechBlock voice override
2. Speaker voice
3. Project default voice
4. unresolved

The editor lists actual Voice Studio profiles and can filter by language, role/category, style, tone, energy, and favorites. Generation routes through the existing `MultiSpeakerTTSService` and therefore the existing `TTSService` / `AIResourceManager`; it does not load a separate model per row.

Generation statuses are Not Generated, Queued, Generating, Ready, Outdated, Failed, and Cancelled. Successfully generated rows stay complete when remaining work is cancelled.

## Timing and fit

SpeechBlock absolute timing is the single source of truth. Table timing edits update Timeline clips; dragging/resizing a `speech_block` Timeline clip writes back to the same SpeechBlock. Completed timing edits enter the existing Timeline command stack rather than writing during every mouse movement.

Generated duration is compared with allocated segment duration. The editor reports Fits, Short, Long, Very Long, Adjusted, or Needs Review and displays the signed duration difference. Fit Audio stores a conservative atempo request only in the 0.8–1.25 range; larger mismatches require Extend Segment or regeneration.

## Take history

Every successful generated result remains a `GeneratedAudio` record tagged with `speechBlockId`. A block can preview and reactivate older takes. Failed regeneration never deletes or deactivates the last successful take. Project duplication intentionally clears generated take pointers so a duplicate cannot reference another project's generated output.

## Subtitles, transcript, and translation

Speech and subtitle text remain independently editable. `Update Subtitle from Speech` refuses to replace a manually edited cue without explicit confirmation. Reverse synchronization is explicit as well. Existing real word timings are untouched; Phase 32 does not fabricate translated/TTS word timestamps.

Transcript segments can become SpeechBlocks with timing, language, and speaker metadata. Translation segments can become SpeechBlocks while retaining translation review state in metadata.

## Workflow reuse

The same SpeechEditor is exposed in News Studio, Story Studio, Translate & Dub, Shorts, and Timeline. News Reporter/Guest, Story Narrator/Character, and multilingual rows are all ordinary SpeechBlocks. Source-audio rows are visible in the same editor but are skipped by TTS generation.

Generated SpeechBlock audio continues to route through the existing Phase 30 mixer. The active take is mirrored to legacy `audio_id`, and absolute start is mirrored to legacy `start_offset_ms` for compatibility with established mixer/render paths.

## Autosave and recovery

Speech edits are transactionally persisted through the canonical repositories. The Manual Speech controller also updates Phase 27 autosave state after persisted edits so the existing Saved / Unsaved / recovery UI stays authoritative. No separate speech save loop was added.

## Performance

The speech table uses ListView delegate recycling and activates the text editor only for the current row. Repository queries are project/section ordered and migration 27 adds project/timing/status indexes. This avoids creating 1,000 heavyweight text editors for a 1,000-row speech project.

# Phase 22 — Universal Multilingual Layered Video Studio

Phase 22 keeps the existing `Project -> Media -> Scene -> Timeline -> Renderer -> Export` architecture. It does not add another editor or renderer.

## Language registry

`resources/languages.json` is the built-in content-language catalog. `domain.language` exposes backward-compatible helpers while `LanguageService` combines application language availability with runtime engine capability. English/Khmer remain valid and Thai/Vietnamese are first-class content languages. Engine support remains separate from registry membership.

VoxCPM2 capability metadata uses the verified official 30-language model catalog. faster-whisper capability is read from the installed package's own `_LANGUAGE_CODES`. Translation pairs are queried from the selected provider/model. Manual translation is intentionally provider-independent because the user supplies the translated text.

## Speakers and speech blocks

`SpeakerProfile` is project identity/role metadata and is separate from a `VoiceProfile`. `SpeechBlock` is the reusable dialogue unit under a ScriptSection. Existing ScriptSection content is lazily represented as one backward-compatible speech block, without deleting or rewriting legacy content.

Voice resolution is: block voice override -> speaker voice -> project default voice. TTS generation validates the speech-block language against the chosen engine before generation and stores speaker/voice/language/text-hash metadata.

## Universal manual video workflow

Normal `video` projects use the existing project workspace. Timeline is the advanced manual editor surface. Media cards can be dragged to Timeline or added at the playhead. Empty main video can become the Scene primary visual; V2/V3 additions use the existing `scene_layers` relationship.

Layer roles include B-roll, overlay video, presenter, reporter, interview guest, host, character and image overlay. Transform coordinates are normalized. Crop, opacity, rotation, flip, PIP, z-order, speaker relation, timing and chroma-key settings persist in SceneLayer metadata, so existing SceneRepository/project duplication behavior remains compatible.

Deleting a visual layer deletes only the relationship. It never deletes the MediaAsset or external source file.

## Layered renderer

The Phase 15 SceneRenderer remains authoritative. Phase 22 wraps only its scene-command builder when layered content exists. The FFmpeg filter graph composes the primary visual, multiple visual layers, image/logo/text/shape overlays and audio into the same Scene intermediate.

Chroma key checks the installed FFmpeg filter list and selects `chromakey` or `colorkey`. If neither exists the render fails with a typed, user-facing error. Source files are never altered.

Layer video audio is opt-in. B-roll defaults muted; interview/host layers may keep source audio. Manual audio clips support volume, mute and simple fade-in/out.

## Word timing

Word timing remains milliseconds internally with optional frame snapping. Editing a transcript word updates the canonical transcript segment text. Source-language subtitle/karaoke word rows are rebuilt where a timed transcript-backed subtitle track exists. Translated word timing is never fabricated.

## Preview limitation

The existing Qt PreviewPlayer remains bounded and does not instantiate one MediaPlayer per timeline clip. Final FFmpeg output is authoritative for multi-video synchronization/chroma composition. A future phase can add cached low-resolution composition previews without changing the domain model.

## Deliberately not included

No lip sync, face animation, arbitrary masks, full keyframe animation, speed ramping, advanced color grading or second renderer/editor is introduced in Phase 22.

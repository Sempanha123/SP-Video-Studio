# PHASE 13 STATUS

Completed.

## Completed:

- Reusable workflow-agnostic Scene domain and persistence foundation
- Manual scene creation, deletion, duplication, ordering and enable/disable state
- Scene creation from enabled Script sections
- Scene creation from grouped Transcript segments
- Project media, generated narration and subtitle-track assignment
- Explicit millisecond scene duration with narration-duration matching
- Image/video fit mode and simple video source-range metadata
- Source/narration audio enable + normalized volume preferences
- Cut, Fade, Crossfade and Slide transition metadata
- Headline, body/lower-third and logo overlay foundation
- Resolution-independent normalized overlay coordinates
- Khmer/English/mixed Unicode overlay persistence
- Scene status and validation warnings/errors
- Script source hashes, changed/missing detection and explicit synchronization
- Renderer-neutral per-scene render specification
- Enabled project scene-sequence specification with cumulative timing
- Modern storyboard + preview + inspector QML workspace
- Project duplication remapping for project-owned scene references
- Existing Phase 0–12 migrations/tests preserved

## Scene architecture:

- `Scene` is generic and not tied to News, Story, Shorts or another workflow
- Stable UUID identity and deterministic zero-based scene order
- Explicit `duration_ms`; it is never recalculated silently after user edits
- Optional source relationships for ScriptSection, TranscriptSegment and TranslationSegment
- `SceneLayer`, `SceneOverlay`, `SceneTransition` and `SceneAudioSettings` are separate reusable domain models
- Normalized 0.0–1.0 scene element geometry keeps composition resolution-independent
- SQLite schema version 10 adds `scenes`, `scene_layers` and `scene_overlays`
- Phase-0 `Scene(index=..., media=...)` constructor compatibility remains intact for existing code/tests

## Scene editor:

- Added **Scenes** as a functional Project Workspace module
- Storyboard list uses a `QAbstractListModel` and lightweight media thumbnails
- Add Scene, Create from Script, Create from Transcript, Sync Script, move, duplicate and delete controls
- Scene inspector sections cover General, Visual, Audio, Text & Overlays, Subtitles and Transition
- Empty scenes clearly request a visual or explicit background instead of pretending to be render-ready
- Scene preview uses project aspect ratio and normalized overlay placement
- No advanced timeline or keyframe editor was introduced

## Media assignment:

- Scene visuals accept only project-managed image/video assets
- Image and video references reuse the Phase 4 Media Library and never mutate source files
- Fill, Fit and Stretch metadata supported; Fill is default
- Video source start/end range stored without creating permanent trims
- Transcript-created scenes reuse the transcript source media and preserve grouped source ranges
- Missing media is detected without deleting the scene
- Replacing media preserves scene-owned overlays/layout metadata

## Narration integration:

- Scenes reference existing Phase 8 generated-audio records; audio is not duplicated inside scenes
- Script-created scenes attach the latest completed section narration when available
- Real narration duration is preferred over the script estimate for initial scene duration
- Narration-too-long validation warning added
- Explicit **Match Scene Duration to Narration** action updates duration
- Narration preview routes through the existing Phase 5 external-audio playback stack

## Subtitle integration:

- Scenes can reference a project Phase 12 subtitle track or no track
- Subtitle tracks remain global project artifacts; cues are not duplicated per scene
- Missing track references are reported as scene validation issues
- Scene Editor does not recreate Subtitle Studio
- Absolute subtitle timing is not fabricated for script scenes before a final project timeline exists

## Overlay system:

- Headline, body text, lower third, label and logo domain types
- QML tools for Headline, Lower Third and Logo creation
- Text, secondary text, layer order, normalized position/size and opacity persistence
- Logo overlays reference project image media and retain transparent image rendering in QML
- Overlay child IDs are regenerated during scene/project duplication
- Overlay timing structure exists for full-scene or bounded visibility without implementing keyframes
- Validation covers bounds, timing and safe-area warnings

## Transitions:

- Stable transition codes: `cut`, `fade`, `crossfade`, `slide`
- Transition duration stored independently from UI
- Excessive transition durations are rejected/warned relative to scene duration
- Phase 13 preview/sequence policy remains sequential and no-overlap
- Final crossfade overlap/render math is intentionally deferred to the renderer

## Script-to-scene creation:

- One enabled ScriptSection creates one initial Scene
- Disabled sections are excluded
- Scene name comes from section title
- Estimated narration duration uses existing script analysis
- Completed section narration is assigned when available
- Script section ID and stable SHA-256 source hash are stored
- Existing scenes are not overwritten by create/sync operations

## Source synchronization:

- Changed script section text marks mapped scenes `source_changed`
- Deleted source sections mark mapped scenes `source_missing`
- New enabled sections can add only new mapped scenes
- Sync preserves assigned media, overlays, subtitles, audio preferences and other scene edits
- Explicit per-scene sync refreshes source metadata without resetting visual composition

## Scene validation:

- Positive duration validation
- Missing media/narration/subtitle detection
- Video-source range validation
- Video-shorter-than-scene warning
- Narration-longer-than-scene warning
- Overlay timing/bounds/safe-area checks
- Transition duration validation
- Disabled scenes remain stored and are excluded from enabled total duration
- Scene status codes remain generic: Ready, Incomplete, Missing Asset, Disabled

## Render-spec preparation:

- `build_scene_render_spec(scene_id)` returns renderer-neutral visual/audio/subtitle/overlay/transition/source data
- `build_project_scene_sequence()` returns enabled scenes in stable order
- Sequence includes cumulative `startMs`/`endMs` and total duration
- Phase 13 policy is documented as `sequential_no_overlap_phase13`
- No FFmpeg rendering is executed by the Scene Engine

## Project duplication:

- Scene IDs are regenerated
- Layer and overlay IDs are regenerated
- Media references remap through the duplicated-media ID map
- Generated narration IDs remap to duplicated generated audio
- Script section IDs remap to duplicated Script sections
- Transcript and Translation segment IDs remap to duplicated source rows
- Subtitle track IDs remap to duplicated project subtitle tracks
- Logo/layer asset references remap too
- Tests verify duplicated scenes do not retain original project-owned IDs
- Scene deletion does not delete media, generated narration or subtitle tracks

## New files:

- `domain/scene_audio.py`
- `domain/scene_layer.py`
- `domain/scene_overlay.py`
- `domain/scene_transition.py`
- `services/scene_generation_service.py`
- `services/scene_preview_service.py`
- `services/scene_service.py`
- `services/scene_validation_service.py`
- `storage/migrations/m010_create_scenes.py`
- `storage/repositories/scene_repository.py`
- `ui/controllers/scene_controller.py`
- `ui/models/scene_list_model.py`
- `ui/qml/editor/SceneCard.qml`
- `ui/qml/editor/SceneEditor.qml`
- `ui/qml/editor/SceneInspector.qml`
- `ui/qml/editor/SceneList.qml`
- `ui/qml/editor/SceneMediaPicker.qml`
- `ui/qml/editor/SceneOverlayEditor.qml`
- `ui/qml/editor/ScenePreview.qml`
- `ui/qml/editor/SceneTransitionPicker.qml`
- `tests/test_scene_phase13.py`
- `tests/test_scene_qml_structure.py`
- `PHASE13_REPORT.md`

## Modified files:

- `README.md`
- `app/bootstrap.py`
- `domain/scene.py`
- `services/narration_service.py`
- `services/project_service.py`
- `services/subtitle_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- Existing migration/version regression tests updated for schema v10
- Existing Script workspace static test updated because Scenes is now a completed module

## Tests run:

- Baseline before Phase 13: **281 passed, 5 skipped**
- Phase 13 focused backend/QML suite: **24 passed**
- Final full suite: **305 passed, 5 skipped**
- `python -m compileall -q app domain engines media services storage ui workers`: passed
- `git diff --check`: passed
- Fresh temporary bootstrap applied migrations 1–10 and resolved `SceneService`: passed
- Expected skips remain two PySide6 runtime/QML tests plus opt-in real VoxCPM2, faster-whisper and translation integration tests

## Create-from-script test:

- Hook/Main/Outro-style enabled sections create stable ordered scenes
- Disabled Script sections are excluded
- Source IDs/hashes preserved
- Existing completed section narration is attached
- Real narration duration wins over the estimate when available
- Source changes preserve scene media and overlays

## Narration test:

- Generated audio assignment persists
- Narration longer than the scene produces a warning
- Match Duration updates the scene to the generated WAV duration
- Scene deletion leaves the GeneratedAudio record/file ownership untouched

## Khmer overlay test:

- Khmer scene name and headline/lower-third text persist through SQLite/restart
- Normalized overlay positions survive reload
- No encoding conversion is performed by Scene domain/repository layers

## 100-scene test:

- 100 scenes created and listed in deterministic order
- Last scene moved to the beginning successfully
- Total duration calculation remained correct
- Enabled render-sequence specification contains all 100 scenes
- Storyboard model architecture does not instantiate media players per card

## Restart persistence test:

- Scene name, duration, media references, transitions and Khmer overlay content reload from SQLite
- Overlay normalized positions reload correctly
- Database migration version is 10 after restart/open

## Known issues:

- Live PySide6/QML window smoke cannot run in this packaging sandbox because PySide6 is unavailable; static QML wiring tests pass
- Scene video preview uses the existing playback controller; the storyboard composition surface uses the media thumbnail/image rather than a second concurrent video player
- Narration + source-video audio preview is not a sample-accurate final mix; Phase 13 stores the intended volume/enabled settings for the future renderer
- Subtitle preview inside a script-driven scene is intentionally limited because an absolute final project timeline does not exist yet
- Transitions are metadata/QML-preview concepts only; final FFmpeg transition composition belongs to the rendering phase
- Scene layers are a foundation; Phase 13 UI primarily edits overlays and the primary visual rather than exposing a full Photoshop-style layer tree

## Architecture decisions:

- One generic Scene model for every workflow
- Explicit scene duration rather than continuously inferred duration
- Project assets remain referenced, not copied into each scene
- Scene-owned children use independent IDs; shared media/audio/subtitles remain immutable references
- Positions are normalized instead of desktop-preview pixels
- Source relationships are advisory and hash-tracked; user composition edits are never overwritten automatically
- Empty scene readiness requires either a primary visual or an explicitly enabled background
- Scene sequence timing is cumulative/no-overlap for Phase 13; final transition overlap math is deferred
- Renderer consumes scene/render specs, never QML state

## Recommended next phase:
Phase 14 — AI Director Foundation

## Suggested Git commit:
`feat: add reusable scene engine and storyboard editor`

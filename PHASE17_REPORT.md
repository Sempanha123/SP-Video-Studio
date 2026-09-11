# PHASE 17 STATUS

Completed:

* Professional multi-track Timeline workspace built on the existing Scene/Subtitle/Audio domain rather than a second project model.
* Playhead/scrubbing, zoom/fit, scene reorder/ripple, trim, split, duplicate/delete, snapping, markers, track lock/mute/visibility, audio volume/mute, subtitle/overlay timing, transition editing, command-based undo/redo, restart persistence, and renderer integration.
* Schema v14 migration adds minimal timeline-specific persistence while all creative clips remain derived from canonical records.

Timeline architecture:

* `TimelineService` orchestrates derived clips, persistent editor state/tracks/markers, time mapping, snapping, validation, and command-backed editing.
* `TimelineMappingService` derives Scene/Overlay/Narration/Source-Audio/Subtitle clips from existing Phase 13/12/8 data and shares Phase 15 renderer duration/transition math.
* SQLite persists `timeline_state`, `timeline_tracks`, and `timeline_markers`; Scene/Subtitle/Overlay clips are not redundantly stored.

Track types:

* Functional derived tracks: Video, Overlay, Voice, Source Audio, Subtitles.
* Future-ready infrastructure: Music, SFX, B-roll. Phase 17 intentionally does not create renderer-ignored B-roll/audio-compositing features.
* Lock state blocks edits; Voice/Source Audio mute and Overlay visibility have documented render semantics.

Scene synchronization:

* Storyboard and Timeline modify the same `Scene` records.
* Storyboard duration/media changes appear on Timeline refresh; Timeline trim/reorder/split immediately appear in Storyboard data.
* Primary scenes remain a sequential ripple timeline, not arbitrary free-position blocks.

Playhead/scrubbing:

* Timeline ruler/playhead click and drag seek through the existing Phase 5 PlaybackController.
* Scene source ranges are mapped correctly between project time and media-source time.
* Playback position feedback subtracts Scene `source_start_ms` before mapping back to project time.
* Previous/Next Scene and approximate Previous/Next Frame stepping are available.

Zoom/scroll:

* Pixels-per-second zoom with bounded Zoom In/Out and Fit Timeline.
* Long projects use horizontal Flickable scrolling; timeline width scales from project duration.
* Zoom/playhead/scroll state can persist without being treated as creative clip data.

Trim:

* Image right-edge trim changes Scene duration only.
* Video right-edge trim updates duration/source-out; left trim advances source-in and reduces duration without modifying original media.
* Media bounds and a 100 ms minimum Scene duration are enforced; following scene positions ripple automatically.

Split:

* Video Scene split creates two independent Scene IDs with complementary source ranges.
* Image split shares the project-managed read-only image reference and divides duration.
* Scene overlays are redistributed/clamped by local split time; the second half does not silently replay the same generated narration file.

Reorder/ripple:

* Drag/reorder updates persistent Scene order, not just QML rectangles.
* Any Scene duration change recalculates all following project start positions from shared render-time mapping.

Snapping:

* `TimelineSnapService` converts an 8 px screen threshold to milliseconds at current zoom.
* Targets include playhead, Scene boundaries, markers, and project start/end.
* Subtle snapped positioning is exposed through the controller; no fixed 500 ms snap rule is used.

Markers:

* Project markers persist with stable IDs, integer millisecond time, Unicode label, optional color, and metadata.
* Add/update/delete APIs are available; `M` adds a marker at the playhead.

Voice/audio tracks:

* Narration and source-video audio clips are derived from Scene relationships/settings.
* Individual narration/source-audio volume and mute write the canonical Scene audio settings.
* Source audio remains linked to its Scene; Timeline does not detach it into a second audio model.

Subtitle track:

* Default-track `SubtitleCue` rows appear as timeline clips at their real project timing.
* Timeline timing changes write the canonical SubtitleCue; Subtitle Studio changes are visible after refresh.
* Deleting a timeline representation does not delete the SubtitleTrack implicitly.

Overlay track:

* Scene overlays appear at `sceneStart + startOffsetMs` with normalized Scene ownership.
* Move/trim updates SceneOverlay offsets, clamps inside Scene duration, and supports undo/redo.
* Overlay delete is command-backed and restores the same overlay data/order on Undo.

Transitions:

* Timeline clip metadata exposes Cut/Fade/Crossfade/Slide plus duration.
* Scene inspector offers transition type and duration editing; clip badges show non-Cut transitions.
* Project duration/time mapping uses the same Crossfade/Slide overlap semantics as Phase 15 rendering.

Undo/redo:

* New command stack supports execute/undo/redo with 150-command history.
* Required canonical edits—trim, split, delete, duplicate, reorder, audio/track settings, transition, overlay/subtitle timing—are command-backed.
* Slider/value edits coalesce by semantic key so one completed drag/adjustment does not create hundreds of history entries.
* History is intentionally in-memory only and does not survive application restart; saved project state does.

Renderer integration:

* Timeline reorder/trim/split/overlay/subtitle/audio/transition edits flow through existing Scene/Subtitle records into Phase 15 RenderPlan.
* RenderService additionally consumes Timeline Overlay visibility and Voice/Source-Audio mute settings when building an immutable snapshot.
* Real FFmpeg regression after Timeline reorder + source trim + split validated output duration and decoded frames for actual order/source-range behavior.

New files:

* `commands/__init__.py`
* `commands/base_command.py`
* `commands/command_stack.py`
* `commands/timeline/__init__.py`
* `commands/timeline/commands.py`
* `domain/timeline_clip.py`
* `domain/timeline_marker.py`
* `domain/timeline_selection.py`
* `domain/timeline_track.py`
* `services/timeline_edit_service.py`
* `services/timeline_mapping_service.py`
* `services/timeline_service.py`
* `services/timeline_snap_service.py`
* `services/timeline_validation_service.py`
* `storage/migrations/m014_create_timeline.py`
* `storage/repositories/timeline_repository.py`
* `ui/controllers/timeline_controller.py`
* `ui/qml/timeline/TimelineClip.qml`
* `ui/qml/timeline/TimelineClipHandle.qml`
* `ui/qml/timeline/TimelineContextMenu.qml`
* `ui/qml/timeline/TimelineEditor.qml`
* `ui/qml/timeline/TimelineHeader.qml`
* `ui/qml/timeline/TimelinePlayhead.qml`
* `ui/qml/timeline/TimelineRuler.qml`
* `ui/qml/timeline/TimelineSelectionOverlay.qml`
* `ui/qml/timeline/TimelineToolbar.qml`
* `ui/qml/timeline/TimelineTrack.qml`
* `ui/qml/timeline/TimelineZoomControl.qml`
* `tests/test_timeline_phase17.py`
* `tests/test_timeline_qml_structure.py`
* `tests/test_timeline_render_integration.py`
* `PHASE17_REPORT.md`

Modified files:

* `README.md`
* `app/bootstrap.py`
* `domain/timeline.py` (foundation placeholder upgraded to the real Timeline domain)
* `services/project_service.py`
* `services/render_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/__init__.py`
* `ui/qml/pages/ProjectWorkspacePage.qml`
* prior schema-version regression assertions updated to v14 and prior "Timeline unfinished" assertions removed now that the module is functional.

Tests run:

* Full automated suite: **451 passed, 7 skipped** before final packaging verification.
* Phase 17 focused tests: **32 passed** (domain/service/QML structure + real FFmpeg timeline-render regression).
* `python -m compileall` and final static QML delimiter checks are run again during packaging verification.
* Expected skips remain two unavailable PySide6 live-runtime checks, opt-in faster-whisper/VoxCPM/translation tests, unavailable real hardware encoder, and opt-in Phase 15 60-second render performance test.

Storyboard ↔ Timeline test:

* Mandatory synchronization path passed: Storyboard Scene duration changes are immediately reflected in derived Timeline clips; Timeline trim/reorder writes the same Scene records and is visible to Storyboard without conversion/restart.

Subtitle synchronization test:

* Mandatory two-way timing path passed: Timeline edits persist to SubtitleCue; direct Subtitle Studio/repository timing changes are reflected by rebuilt Timeline subtitle clips.

Reorder render test:

* Real FFmpeg regression moved the green Scene before the red Scene and decoded the completed MP4 first frame; the green frame was first in actual output.

Trim render test:

* Real synthetic source video contains red 0–2 sec and blue 2–4 sec. Timeline left-trim selected the 2–4 sec range; a decoded output frame during that Scene is blue, verifying the renderer consumes the edited source range.

Split render test:

* Timeline split divided a 1-second image Scene into two 500 ms canonical Scene records. The real render remained continuous and final FFprobe duration matched the 4-second edited timeline within tolerance.

Undo/redo test:

* Trim, split, delete, duplicate, reorder, transition, overlay/subtitle timing, audio settings, track settings, and overlay deletion paths are command-backed.
* Focused tests verify exact previous state returns on Undo and edited state returns on Redo; coalescing keeps repeated semantic value edits to one history entry.

Large-project test:

* Test project derives **100 Scene clips + 1,000 subtitle cues + 200 overlay clips** and builds the clip map within the 5-second guard on this validation host.
* No per-clip media players or waveform generation are instantiated.

Khmer timeline test:

* Khmer Scene names, overlays, subtitle text, and marker labels persist/reload as Unicode without corruption.

Restart persistence test:

* Combined test performs Scene reorder, trim, split, SubtitleCue timing change, narration/source-audio volume change, and Khmer marker creation; fresh repository instances reload all creative edits correctly.

Known issues:

* PySide6 is not installed in this packaging sandbox, so live Timeline QML runtime/scrub QA is not executed here; static QML structure/delimiter tests pass.
* Qt Multimedia scrubbing/frame stepping is best-effort and not advertised as frame-accurate; frame stepping quantizes approximately from project FPS while milliseconds remain canonical.
* Crossfade preview chooses the incoming Scene during overlap; final visual/audio blending remains the authoritative Phase 15 FFmpeg render.
* Timeline QML currently derives all subtitle/overlay items directly; the backend 100/1000/200 large-project test is fast, but live GPU/UI profiling of 1,000 QML cue items still requires a Windows PySide6 runtime.
* Music/SFX/B-roll tracks are infrastructure only in Phase 17. No renderer-ignored B-roll compositing, waveform system, full audio mixer, keyframes, speed changes, or color grading is introduced.
* Undo history intentionally does not persist across restart.

Architecture decisions:

* Scene remains canonical for primary visual ordering/duration/source ranges/overlays/narration/transitions; SubtitleCue remains canonical for subtitle timing.
* Timeline-specific DB persistence is intentionally minimal to avoid dual writable timing models.
* Renderer and Timeline share project-duration/transition-overlap helpers, eliminating duplicated timeline math.
* Main Video track is ripple/reorder based rather than arbitrary free-position NLE clips; this keeps Scene Engine and renderer semantics coherent.
* Non-destructive trim/split never modifies original media/generated audio files.
* Track-level render switches are implemented only where semantics are unambiguous and renderer-supported: Overlay visibility plus Voice/Source Audio mute.

Recommended next phase:
Phase 18 — News Studio

Suggested Git commit:
`feat: add advanced multi-track timeline editor`

Do not automatically begin Phase 18.

# PHASE 5 STATUS

## Completed:

- Python 3.14 package compatibility (`>=3.11,<3.15`)
- Python 3.14-compatible PySide6 / psutil / Pillow dependency floors
- Explicit playback state model
- Native Qt Multimedia preview foundation
- Video, audio, and image preview
- Play / pause / replay controls
- Seek/scrub with clamping
- Current and total time display
- Volume and mute with previous-volume restoration
- Keyboard playback shortcuts
- Media switching and project switching cleanup
- Selected-media removal cleanup
- Runtime preview errors separated from Phase 4 media validity
- Responsive split Media Library / Preview workspace

## Player architecture:

- `domain/playback.py` defines states, selection model, and seek constants.
- `services/playback_service.py` owns backend-neutral playback policy/state.
- `ui/controllers/playback_controller.py` exposes state and commands to QML.
- `ui/qml/editor/PreviewPlayer.qml` owns one native `MediaPlayer`, one `AudioOutput`, and one `VideoOutput`.
- QML receives local media URLs created with `QUrl.fromLocalFile`; raw `file:///` strings are not hand-built.

## Supported preview types:

- Video: native Qt Multimedia playback with preserved aspect ratio.
- Audio: native Qt Multimedia playback with dedicated audio preview state.
- Image: aspect-preserving still preview with playback controls hidden.

## Controls:

- Play / Pause
- Replay from beginning after end-of-media
- Seek bar
- Current / total time
- Volume 0–100
- Mute / unmute with previous-volume restoration

## Keyboard shortcuts:

- Space — Play / Pause / Replay
- Left / Right — seek 5 seconds
- Shift + Left / Right — seek 10 seconds
- M — mute / unmute

## Media-library integration:

- Selecting Phase 4 media loads its project-managed copy into preview.
- Rapid selection releases the previous source before loading the next source.
- Images do not expose fake playback duration.
- Missing media is not sent to the native player.
- Grid/list selected state remains synchronized with playback selection.

## Error handling:

- Native Qt preview errors show a friendly preview-only state.
- Qt codec failure does not mark the imported media database record invalid.
- Broken/missing managed files are refused before playback.
- Reveal in Folder remains available from the preview error state.

## Resource cleanup:

- Playback clears on media replacement.
- Playback clears before selected media is removed.
- Playback clears on project switch / workspace destruction.
- Playback clears during application shutdown.

## New files:

- `domain/playback.py`
- `services/playback_service.py`
- `ui/controllers/playback_controller.py`
- `ui/qml/editor/PreviewPlayer.qml`
- `ui/qml/editor/PlayerControls.qml`
- `ui/qml/editor/SeekBar.qml`
- `ui/qml/editor/VolumeControl.qml`
- `ui/qml/editor/MediaInfoStrip.qml`
- `ui/qml/editor/AudioPreview.qml`
- `ui/qml/editor/ImagePreview.qml`
- `ui/qml/editor/PlayerErrorState.qml`
- `resources/icons/play.svg`
- `resources/icons/pause.svg`
- `resources/icons/replay.svg`
- `resources/icons/volume.svg`
- `resources/icons/mute.svg`
- `tests/test_playback.py`
- `tests/test_playback_controller_qt.py`
- `tests/test_python_compatibility.py`
- `PHASE5_REPORT.md`

## Modified files:

- `pyproject.toml`
- `app/bootstrap.py`
- `ui/controllers/media_controller.py`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- `tests/test_qml_structure.py`
- `README.md`

## Tests run:

- `python -m compileall -q app domain media services storage workers ui`
- `pytest -q`
- 100 passed
- 2 skipped in this sandbox because PySide6 is not installed (Qt controller URL test + live QML smoke)
- Phase 0–4 regression suite remains green.

## Manual playback checks:

- Native QML player wiring statically audited against Qt 6.11 MediaPlayer / AudioOutput / VideoOutput API.
- Video/audio selection, source release, state transitions, controls, and error bindings reviewed.
- Real GUI playback cannot be executed in this packaging sandbox because PySide6 is unavailable.

## Remove-while-playing test:

- Python/QML flow is wired so `MediaController.mediaAboutToRemove` clears PlaybackController before filesystem deletion.
- Unit state cleanup is covered; live Windows file-handle behavior should be smoke-tested after extracting on the target machine.

## Project-switch test:

- Workspace current-project changes call `PlaybackController.setCurrentProject`, which clears old playback before switching project identity.
- Workspace destruction and app shutdown also clear playback.

## Known codec limitations:

- Import validity comes from Phase 4 probing and is separate from Qt native preview support.
- Platform codecs / Qt Multimedia backend may reject an otherwise valid imported file.
- Proxy transcoding is intentionally deferred.

## Known issues:

- Live Qt playback smoke is not runnable in this sandbox because PySide6 is not installed.
- Preview volume is session-only for Phase 5.
- Fullscreen, playback-rate, waveform, frame-step, and proxy preview are deferred.

## Architecture decisions:

- One main player only; media cards remain thumbnail-only.
- Native Qt Multimedia is used instead of a custom decoder.
- Playback business state is Python-side; media decoding/rendering remains native QML/Qt.
- Project-managed media paths are always used for preview.
- No valid media status is changed solely because native preview fails.
- Python 3.11 remains the syntax baseline while package metadata now supports Python through 3.14.

## Recommended next phase:
Phase 6 — Script Editor

## Suggested Git commit:
`feat: add media preview and playback system`

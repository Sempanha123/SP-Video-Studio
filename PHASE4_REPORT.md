# PHASE 4 STATUS

## Completed:

- Persistent project media domain and SQLite repository
- Safe streaming import of video, audio, and images
- Background multi-file imports with progress and cancellation
- Local-file drag and drop plus native multi-file picker UI
- Search, type filters, sorting, grid/list views, selection, details, reveal, and removal
- Missing-media detection and user-facing Missing state
- Transaction-like cleanup for partial copy/probe/database failures
- Unicode/Khmer filenames
- Project duplication/deletion integration with media
- Original-source protection throughout destructive project operations

## Supported media:

- Video: MP4, MOV, MKV, AVI, WebM, M4V
- Audio: MP3, WAV, M4A, AAC, FLAC, OGG, Opus
- Images: JPG, JPEG, PNG, WebP, BMP
- Extensions classify files; FFprobe/Pillow perform actual validation

## Import system:

- Phase 4 always copies imported files into project-managed media storage
- Project copies use UUID-based collision-safe filenames
- Large files are streamed in chunks instead of loaded into RAM
- Free disk space is checked before copying
- Copy progress exposes byte-level progress
- Cancellation removes partial project copies and prevents final DB insertion
- Multi-file imports continue when one independent file fails
- Import rollback cleans media/thumbnail files when persistence fails

## Metadata / FFprobe:

- Central `FFprobeService`
- Structured `subprocess` arguments with `shell=False` and timeout
- JSON parsing for video/audio streams and format metadata
- Duration, dimensions, rational FPS, codecs, channels, sample rate, bitrate, container, rotation
- Missing/timeout/corrupt/unsupported cases handled without crashing
- Image dimensions/format/orientation inspected with Pillow

## Thumbnail system:

- Project-local `<media-id>.jpg` thumbnails
- Video representative frame near 10% duration through FFmpeg
- Safe short-video timestamp fallback
- Image thumbnail resize with EXIF orientation support
- Bounded thumbnail dimensions
- Audio placeholder icon; waveform intentionally deferred
- Thumbnail failure does not fail valid media import

## Media library UI:

- Functional Media workspace inside Project Workspace
- Import Media native multi-select picker
- Local file drag/drop with drop-zone feedback
- Search by filename
- All / Video / Audio / Images filters
- Recently Added / Name / Type / File Size sorting
- Grid/List switch
- `QAbstractListModel` media roles
- Single selection
- Media detail dialog
- Reveal in Folder
- Remove from Project / Remove Reference confirmation
- Import progress + Cancel
- Phase 1 design tokens/components retained

## Project duplication compatibility:

- Project-managed media files are physically copied into the duplicate
- Media database rows receive new media IDs
- Duplicate paths point only inside the duplicated project
- Thumbnail filenames are rewritten to duplicated media IDs
- Transient cache is not duplicated
- Source and duplicate never share writable managed media copies

## Project deletion compatibility:

- Project directory staging/safety from Phase 2 remains intact
- `media_assets` records use an intentionally tested project foreign-key cascade
- Deleting a project removes only project-managed files and records
- Original source paths are never filesystem deletion targets

## Original-file safety:

- Import reads and copies the selected source; it never overwrites it
- Remove deletes only validated project-local copies/derivatives
- Project deletion never follows `original_path`
- Safe path guards reject media paths that escape project media/thumbnail roots
- Automated tests verify original bytes remain after media removal/project deletion

## New files:

- `storage/migrations/m002_create_media_assets.py`
- `storage/repositories/media_repository.py`
- `media/file_classifier.py`
- `media/media_importer.py`
- `media/probe.py`
- `media/thumbnails.py`
- `services/platform_service.py`
- `ui/controllers/media_controller.py`
- `ui/models/media_format.py`
- `ui/models/media_list_model.py`
- `ui/qml/components/MediaCard.qml`
- `ui/qml/components/MediaListRow.qml`
- `ui/qml/components/MediaDetailsDialog.qml`
- `resources/icons/audio.svg`
- `resources/icons/grid.svg`
- `resources/icons/image.svg`
- `resources/icons/import.svg`
- `resources/icons/list.svg`
- `resources/icons/more.svg`
- `resources/icons/search.svg`
- `tests/test_media_phase4.py`
- `tests/test_media_format.py`
- `tests/test_media_ffmpeg_integration.py`
- `PHASE4_REPORT.md`

## Modified files:

- `app/bootstrap.py`
- `domain/media.py`
- `media/__init__.py`
- `media/ffprobe.py`
- `pyproject.toml`
- `services/media_service.py`
- `services/project_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `tests/test_database.py`
- `tests/test_qml_structure.py`
- `ui/qml/Main.qml`
- `ui/qml/components/StatusBadge.qml`
- `ui/qml/pages/AssetsPage.qml`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- `README.md`

## Tests run:

- `python -m compileall -q app domain media services storage ui workers`
- `pytest -q`
- 85 passed
- 1 skipped: live QML smoke because PySide6 is unavailable in this packaging sandbox
- Previous Phase 0/1/2/3 automated tests remain green after the Phase 4 migration expectation update

## Integration tests:

- Real local FFmpeg generated a tiny MP4 and WAV fixture
- Real FFprobe successfully parsed the MP4/WAV metadata
- Real FFmpeg successfully generated a video JPG thumbnail
- Real MediaService imported both fixtures and persisted them
- Tests automatically skip on machines without FFmpeg/FFprobe

## Manual checks:

- Project create → image/video/audio import → list/search/filter → remove flow exercised with temporary directories
- Multi-file partial-success behavior verified
- Invalid video and missing FFprobe failures leave no media DB row or partial project file
- Low-disk import protection verified
- Missing managed file changes to Missing without crashing
- Duplicate project media remains independent after modifying duplicate content
- Original-source bytes verified unchanged after remove/project delete
- QML Phase 4 wiring statically audited for file picker, DropArea, search/filter, grid/list, details and remove actions
- Live Qt window interaction could not be executed in this sandbox because PySide6 is unavailable

## Restart persistence test:

- Passed: imported media rows reload from the same SQLite database after repository/service reconstruction.
- Project-managed files and metadata remain available after restart.

## Known issues:

- Live QML runtime smoke remains skipped here because PySide6 is not installed in the packaging sandbox.
- Video/audio import requires FFprobe; video thumbnails require FFmpeg.
- Missing-media relinking is deferred; users can remove the missing reference.
- Animated GIF/TIFF, waveform generation, auto-transcoding, internet downloads, playback and timeline are intentionally outside Phase 4.

## Architecture decisions:

- Original source, project-managed copy, and generated derivatives are separate concepts.
- Phase 4 uses copy-only imports for portable projects and source safety.
- SQLite remains canonical for media library rows; project files contain the actual managed copies.
- Media import/probe/thumbnail work runs outside the UI thread through WorkerPool.
- FFprobe and FFmpeg subprocesses use argument arrays, timeouts, captured output and no shell.
- UUID-based media filenames avoid collisions and Windows filename hazards while preserving Unicode display names.
- Project media directories are created lazily for backward compatibility with existing Phase 2/3 project folders.
- Media DB rows intentionally cascade with project DB deletion; original source paths are never deletion targets.

## Recommended next phase:
Phase 5 — Video Player and Preview System

## Suggested Git commit:
`feat: add project media import and library system`

Do not automatically begin Phase 5.

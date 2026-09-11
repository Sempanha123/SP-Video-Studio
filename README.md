# SP Video Studio

SP Video Studio is a native Windows desktop video-creation application built with Python 3.11–3.14, PySide6, Qt Quick, and QML.

## Current milestone

Phase 0 foundation + Phase 1 application shell + Phase 2 persistent projects + Phase 3 settings/readiness + Phase 4 media library + **Phase 5 native media preview/playback**.

Implemented now:

- Native QML application shell with persistent Light / Dark / System theme
- Versioned user settings and system-readiness detection
- SQLite project library with ordered, transactional migrations
- Create, open, rename, duplicate, and safely delete projects
- Project-local media import for video, audio, and images
- Streaming copy with per-file progress, cancellation, low-disk checks, and rollback cleanup
- FFprobe metadata extraction for video/audio
- Cached image/video thumbnails
- Project Media workspace with search, filters, sorting, grid/list views, details, drag/drop, and removal
- Missing-media detection without crashing
- Project duplication that produces independent managed media records/copies
- Safe project/media deletion that never deletes imported original source files
- Native Qt Multimedia preview for imported video and audio
- Aspect-preserving image preview
- Play/pause/replay, seek/scrub, volume/mute, playback time, and keyboard shortcuts
- Runtime preview-error handling without marking valid imported media invalid
- Playback cleanup on media removal, media switching, project switching, and app shutdown

Not implemented yet: timeline editing, AI inference, VoxCPM2 inference, Whisper transcription, translation, subtitles, News/Story generation, final rendering/export, model downloads, or batch processing.

## Requirements

- Windows 10/11 recommended
- Python 3.11, 3.12, 3.13, or 3.14
- PySide6 6.10.2+
- psutil 7.2+
- Pillow 12+
- FFmpeg + FFprobe for video/audio metadata and video thumbnails

FFmpeg is detected from a validated custom path or `PATH`. SP Video Studio does not download FFmpeg automatically in Phase 4.

## Setup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Run

```powershell
python main.py
```

## Test

```powershell
pytest
```

The FFmpeg integration tests automatically skip on machines where FFmpeg/FFprobe are unavailable. The rest of the test suite does not require them.

## Runtime data

Application-managed data lives outside the source repository. On Windows:

```text
%LOCALAPPDATA%\MMOVideoStudio\
├── data\app.db
├── settings\settings.json
├── models\
├── cache\
├── temp\
├── logs\
├── downloads\
└── exports\
```

Projects default to:

```text
Documents\SP Video Studio\Projects\
```

Settings → Projects can change the default for **new** projects. Existing projects remain in their current folders.

## Project structure

Each project has a stable UUID-backed folder and compact `project.json` metadata:

```text
project-folder\
├── project.json
├── media\
│   ├── video\        # created on first video import
│   ├── audio\        # created on first audio import
│   └── images\       # created on first image import
├── audio\
├── subtitles\
├── generated\
├── thumbnails\
├── renders\
└── cache\
```

Media type directories are created lazily so older Phase 2/3 projects remain fully compatible.

## Media architecture

Phase 4 keeps media responsibilities separated:

```text
QML Media Workspace
        ↓
MediaController + MediaListModel
        ↓
MediaService
   ├── MediaRepository → SQLite media_assets
   ├── FileClassifier
   ├── MediaImporter → streaming project copy
   ├── FFprobeService → video/audio metadata
   ├── ThumbnailService → video/image thumbnails
   └── platform reveal utility
```

QML does not parse FFprobe output, copy files, or execute media subprocesses. Multi-file imports run through the existing background `WorkerPool`.

## Supported media

### Video

- `.mp4`
- `.mov`
- `.mkv`
- `.avi`
- `.webm`
- `.m4v`

### Audio

- `.mp3`
- `.wav`
- `.m4a`
- `.aac`
- `.flac`
- `.ogg`
- `.opus`

### Images

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`
- `.bmp`

A recognized extension is only the first check. Video/audio must still pass FFprobe validation, and images must be readable by Pillow. A container extension does not guarantee that every codec inside it is supported by the installed FFmpeg build.

## Import strategy and original-file safety

Phase 4 uses **copy into project** as the only import mode.

The application distinguishes:

1. the original source selected by the user
2. the independent project-managed copy
3. generated thumbnail/cache derivatives

Imported files receive UUID-based destination filenames, while the original Unicode display filename is stored in metadata. Duplicate imports are allowed and create separate IDs/copies.

**Original media files are never modified or deleted by import, remove-from-project, project duplication, or project deletion operations.**

Removing media deletes only the validated project-managed copy, its thumbnail, its project cache, and its database record. Destructive operations are guarded so stored paths cannot escape the recognized project media directories.

## Media database

Database schema version is currently **2**.

Migration `002_create_media_assets` adds `media_assets` with persistent metadata including:

- stable media ID and project ID
- media type and original display filename
- original source path and project-managed path
- thumbnail path
- duration, dimensions, FPS, codecs, sample rate, channels
- byte size, MIME type, extension
- created/imported timestamps
- status and compact JSON metadata

The foreign key uses an intentionally tested `ON DELETE CASCADE` relationship for media **database records** when a project library record is deleted. It does not target original source files; project filesystem deletion remains guarded by `ProjectService`.

## FFprobe metadata

`media/probe.py` invokes FFprobe with structured arguments and `shell=False`:

```text
ffprobe -v error -print_format json -show_format -show_streams <project-copy>
```

The parser handles:

- video/audio stream discovery
- duration
- width/height
- rational FPS such as `30000/1001`
- video/audio codecs
- sample rate and channels
- bitrate/container
- phone-video rotation metadata

Missing FFprobe, timeouts, corrupt media, invalid JSON, and unsupported streams produce user-facing failures without crashing the app. Technical details remain in logs.

## Thumbnail system

Thumbnails are stored under the project `thumbnails/` folder using the media ID:

```text
<media-id>.jpg
```

- Images: Pillow loads the project copy, applies EXIF orientation where possible, downsizes it, and writes a bounded JPEG thumbnail.
- Video: FFmpeg extracts a representative frame near 10% of duration with a safe short-clip fallback and bounded width.
- Audio: uses the reusable audio placeholder icon in Phase 4; waveform generation is deferred.

A thumbnail failure does not invalidate otherwise valid media.

## Media library behavior

The project workspace provides:

- Import Media native multi-file picker
- local-file drag and drop
- import phase/byte progress and cancellation
- filename search (case-insensitive)
- All / Video / Audio / Images filters
- Recently Added / Name / Type / File Size sorting
- grid and list layouts backed by `QAbstractListModel`
- single selection
- media details
- Reveal in Folder
- Remove from Project / Remove Reference
- missing-file status refresh

The UI uses cached thumbnails rather than loading full-size media into card delegates.

## Project duplication and deletion

Project duplication first creates an independent project folder, copies persistent project content (not transient cache), then recreates media database records with **new media IDs** and paths inside the duplicate project. Thumbnail filenames are rewritten to the new media IDs. The source and duplicate do not share writable project-managed media files.

Project deletion stages the validated project folder, deletes the project library row, and then removes the staged folder. Media database records are removed transactionally through the tested foreign-key cascade. Original source paths are metadata only and are never deletion targets.

## Settings and readiness

Settings are stored as versioned atomic JSON. Current categories remain General, Appearance, Projects, Performance, Rendering, Storage, and Advanced.

`SystemReadinessService` reports best-effort OS/CPU/RAM/GPU/CUDA/storage/FFmpeg/FFprobe/model information. Hardware detection failures degrade to Unknown rather than preventing application startup.

## Architecture

```text
QML
  ├── ProjectController → ProjectService → ProjectRepository → SQLite
  │                                      └── MediaService duplication hook
  ├── MediaController → WorkerPool → MediaService
  │                              ├── MediaRepository → SQLite
  │                              ├── FFprobeService
  │                              ├── ThumbnailService
  │                              └── MediaImporter
  ├── PlaybackController → PlaybackService → Qt Multimedia (QML MediaPlayer)
  │                                           ├── AudioOutput
  │                                           └── VideoOutput
  ├── SettingsController → SettingsService → SettingsRepository → JSON
  └── ReadinessController → WorkerPool → SystemReadinessService
                                      ├── FFmpegLocator
                                      ├── OS / CPU / RAM
                                      ├── GPU / CUDA
                                      └── disk/model checks
```

## Playback and preview system

Phase 5 uses one native Qt Multimedia `MediaPlayer` for the project preview. Video is rendered through `VideoOutput`, audio through one shared `AudioOutput`, and images use the Qt Quick image path. Imported files are previewed from their **project-managed copy**, not the original source path.

Playback state uses explicit values: `idle`, `loading`, `ready`, `playing`, `paused`, `stopped`, `ended`, and `error`. Python owns state/control policy through `PlaybackService` and `PlaybackController`; QML owns the native player surface and visual animations.

Controls:

- Space: Play / Pause / Replay
- Left / Right: seek 5 seconds
- Shift + Left / Right: seek 10 seconds
- M: Mute / Unmute
- seek slider avoids fighting the playhead while the user is scrubbing
- mute restores the previous volume instead of forcing 100%

Preview volume is intentionally session-only in Phase 5. The existing Settings architecture can persist it later without introducing a second settings system.

A valid FFprobe-imported file can still fail native preview when the local Qt Multimedia backend cannot decode its codec. That produces a **preview error only**; the Phase 4 media record remains valid for future FFmpeg-based workflows.

Resource cleanup stops playback, clears the source, and releases the current selection when media is removed, another project is opened, the workspace closes, or the application exits. This avoids stale playback and reduces Windows file-handle conflicts.

## Python 3.14 compatibility

The package metadata supports `>=3.11,<3.15`. The dependency floors are selected from releases that provide Python 3.14 support: PySide6 6.10.2+, psutil 7.2+, and Pillow 12+.

## Known Phase 5 limits

- Native preview codec availability depends on the local Qt Multimedia backend/platform codecs.
- No proxy/transcoded preview fallback yet.
- No waveform generation.
- No playback-rate or frame-step controls.
- No playback-position persistence across application restarts.
- No fullscreen preview requirement yet.
- Timeline, subtitles, scene composition, AI processing, and final rendering remain later phases.

## Phase discipline

Phase 5 is intentionally limited to stable native media preview/playback. The next phase is **Phase 6 — Script Editor**.

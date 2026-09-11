# SP Video Studio

SP Video Studio is a native Windows desktop video-creation application built with Python 3.11–3.14, PySide6, Qt Quick, and QML.

## Current milestone

Phase 0 foundation through Phase 7 local model management + **Phase 8 VoxCPM2 narration engine**.

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
- Persistent section-based script editor with English/Khmer narration estimates
- Local AI Model Manager for VoxCPM2 and faster-whisper variants
- Lazy official VoxCPM2 TTS adapter with CPU/CUDA device policy
- English/Khmer narration pipeline with voice design and authorized reference-voice support
- Full-script and per-section narration generation with chunking, progress, cancellation and WAV validation
- Project-owned generated narration with freshness hashes, safe deletion, duplication and shared audio preview

Not implemented yet: full Voice Studio UX, Whisper transcription, translation, subtitles, scenes, timeline editing, News/Story generation, final rendering/export, or batch processing.

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

For local VoxCPM2 narration, install the optional official TTS runtime:

```powershell
pip install -e ".[tts]"
```

The desktop application itself remains Python 3.11–3.14 compatible and starts normally when TTS dependencies are absent. VoxCPM/PyTorch are imported lazily only when narration is loaded/generated; actual wheel/runtime availability still depends on the upstream packages for the selected Python/OS/GPU environment.

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


## Script editor

Phase 6 adds a reusable manual narration-script foundation shared by every future workflow. Script data is stored in SQLite through `ScriptRepository` and `ScriptService`; QML never accesses SQL directly.

Each project gets one primary script on first opening of the Script workspace. The default structure is **Hook / Body / Outro**, while users can add Body or Custom sections, rename, duplicate, reorder, enable/disable, and delete sections. Sections use independent stable IDs and sequential zero-based ordering. A lightweight `scene_source` metadata marker prepares sections for future scene generation without creating scenes in Phase 6.

Database schema version 3 adds:

```text
scripts
script_sections
```

Existing Phase 2–5 databases migrate in place; no fresh database is required. Project duplication creates a new script ID and new section IDs, while project deletion relies on the existing SQLite project lifecycle and foreign-key cleanup without affecting other projects.

### Autosave and editing

The QML editor uses a multiline plain-text `TextArea` with native selection/copy/cut/paste and text undo/redo. Content changes are held in memory, statistics are recalculated after a short debounce, and script changes autosave about 1.5 seconds after typing stops. Ctrl+S flushes immediately. Pending script changes are also flushed when leaving Script, switching projects, deleting/closing the current project, or closing the application.

Save state is exposed as **Saved**, **Saving…**, **Unsaved changes**, or **Save failed**. Structural actions save pending text first. Deleting non-empty sections requires confirmation; structural operations are intentionally outside the native text undo stack in this phase.

### Language and narration estimates

Script language is stored as a stable code (`en` or `km`). Changing the language never translates content.

- English uses a token-oriented word count and configurable Slow / Normal / Fast words-per-minute assumptions.
- Khmer uses non-whitespace character count plus a character-rate narration heuristic rather than pretending whitespace is an exact Khmer word boundary.
- Duration is always an estimate until real synthesized audio exists.

`ScriptAnalysisService` also prepares future TTS input by combining enabled sections in order while preserving punctuation and section character boundaries. No model-specific text rewriting is performed.

### TXT import/export

UTF-8 `.txt` import supports BOM and Khmer/Unicode text. Users can add imported text as a new section or replace the current structure with one **Imported Script** section. TXT export writes enabled section titles and content in UTF-8. **Copy Full Script** copies the enabled combined narration text.

Phase 6 does **not** include AI script generation, News research, VoxCPM2, Whisper, translation, subtitles, scene generation, timeline editing, or rendering.

## AI model manager

Phase 7 adds a local model-management layer without loading or running any AI model. The catalog is centralized in `engines/model_registry.py`; static model definitions are kept separate from runtime installation state in SQLite.

Database schema version 4 adds:

```text
model_installations
```

The initial catalog is:

- `voxcpm2` → `openbmb/VoxCPM2` — Apache-2.0 — current public repository size approximately 4.96 GB
- `whisper-small` → `Systran/faster-whisper-small` — MIT — approximately 486 MB
- `whisper-medium` → `Systran/faster-whisper-medium` — MIT — approximately 1.53 GB
- `whisper-large-v3` → `Systran/faster-whisper-large-v3` — MIT — approximately 3.09 GB

Source metadata was verified against the public model repositories on 2026-09-11. Model downloads resolve a concrete Hugging Face repository revision returned by the source API rather than mixing files from a changing `main` snapshot.

### Installation pipeline

Model files live under the application-managed Models folder, never inside the source repository or project folders. Downloads are staged under `models/.downloads/` and only move into the final model directory after validation.

```text
registry
  ↓
ModelService
  ├── ModelCompatibilityService
  ├── ModelDownloadService
  │     └── HuggingFaceSource (public HTTP snapshot files + Range resume)
  ├── ModelVerificationService
  └── ModelRepository → SQLite
```

The download pipeline supports background progress, cancellation, retry/backoff, resumable `.part` files where HTTP Range is supported, interrupted-download recovery, atomic final-directory replacement, and one active model download at a time. Partial data is never reported as Installed.

Each completed installation receives `model_manifest.json` containing model identity, source identifier/revision, installed version, file list, sizes, available official SHA-256 values, installation time, and manifest schema version. Verification checks the managed directory, manifest identity, required files, non-empty files, expected sizes, and hashes when the source publishes them. A failed verification becomes **Repair Required** rather than a false Installed state.

Repair currently performs a safe staged reinstallation. This is deliberate: source-specific partial repair can be added later without weakening installation safety.

### Safe removal and discovery

Removal is restricted to the registry-defined path under the managed model root. Arbitrary paths from database metadata are never recursively deleted. Drive roots, the model root itself, project folders, scripts, media, and generated outputs are outside model deletion targets.

Refresh reconciles the registry, SQLite installation metadata, model manifests, final model directories, and interrupted download folders. A valid managed installation can be rediscovered after metadata loss. Existing unmanifested files are treated as **Repair Required** instead of trusted automatically.

### Compatibility and readiness

Compatibility is guidance, not an inference engine. The Model Manager compares model RAM/VRAM/CPU/CUDA guidance with Phase 3 `SystemReadiness`. Whisper Small / Medium / Large V3 recommendations adapt to detected hardware. VoxCPM2 follows the currently published CUDA/VRAM guidance. Installation is blocked only for insufficient disk space; performance warnings remain advisory.

`SystemReadinessService` now reads real Model Manager family state:

- Installed
- Repair Required
- Not Installed

Home and Settings update after install, verify, repair, or removal without requiring an application restart. Settings → Storage also shows measured managed model storage.

Phase 7 does **not** load VoxCPM2, run faster-whisper, synthesize speech, transcribe media, clone voices, translate, create subtitles, or render video.


## VoxCPM2 narration engine

Phase 8 integrates the official OpenBMB VoxCPM2 Python API behind `VoxCPM2Engine`. The adapter targets the current `voxcpm` 2.0.3 API and managed model identifier `openbmb/VoxCPM2`. Heavy `voxcpm`, PyTorch and audio dependencies are never imported during normal app startup.

The application loads the Phase 7 managed model directory with local-files-only behavior, so a verified installation does not silently trigger a second model download. `TTSEngineManager` owns one reusable engine instance; `TTSService` coordinates Model Manager in-use state, device selection, load/unload and error mapping. CPU and CUDA are explicit choices, while Auto uses current System Readiness and the performance profile.

Supported Phase 8 request modes are:

- **Default** — normal text-to-speech
- **Designed** — passes an official VoxCPM control instruction using the current `(control)text` format
- **Reference** — uses a user-authorized reference recording copied into project-managed `audio/references/` before use
- **Continuation** — represented in the engine request model for prompt-audio + prompt-text workflows; the compact Phase 8 UI intentionally keeps this advanced mode out of the normal panel

CFG, inference steps and optional seed are centralized in the adapter. The Script page keeps a compact narration panel; Phase 9 adds the reusable Voice Studio on top of the same TTS pipeline. Reference-voice use requires explicit permission confirmation and the application does not include public-figure presets.

### Narration pipeline

Enabled script sections are chunked on paragraph/sentence boundaries (including Khmer `។` punctuation) rather than naïve character slicing. Jobs run through the existing worker pool and expose preparing, model-loading, chunk generation, combining, validating and completion states. Cancellation is immediate between chunks; if upstream inference is already inside one model call, stopping completes at the next safe boundary.

Final narration is stored as lossless WAV under:

```text
project/audio/narration/<generated-audio-id>.wav
```

Temporary chunks live under `project/cache/tts/` and are removed after success/failure/cancellation. Chunk concatenation stays in the WAV domain and adds small centralized pauses between chunks/sections. Output is validated before a `generated_audio` database row is marked complete. Schema version 5 adds this table; audio bytes are never stored in SQLite.

Generated narration records preserve engine/model metadata, language, voice configuration, seed/settings, duration/sample rate/channels and a SHA-256 text hash. The hash uses enabled ordered text + language rather than database IDs, so duplicated projects can keep copied narration current while later script edits correctly show **Needs Update**. Regeneration creates a new WAV/record first, so a failed take never destroys the previous working narration.

Project duplication copies generated WAV files to independent new IDs and remaps project-local reference paths. Project deletion removes project-owned generated audio with the project; external source/reference originals are never deleted. Generated narration preview reuses the Phase 5 playback controller instead of creating a separate audio player.

### Testing real VoxCPM2

The standard suite uses `FakeTTSEngine` and never loads the 2B model. A real opt-in integration test is provided:

```powershell
$env:SPVS_RUN_VOXCPM_INTEGRATION="1"
$env:SPVS_VOXCPM_MODEL_PATH="C:\path\to\managed\voxcpm2"
$env:SPVS_VOXCPM_DEVICE="cuda"   # or cpu/auto
pytest -m voxcpm tests/test_voxcpm_integration.py
```

A successful file-generation integration test is not a substitute for listening checks. English/Khmer voice quality and reference/design behavior should be listened to on the target machine before release.


## Voice Studio

Phase 9 turns the Voices placeholder into a reusable local Voice Studio without creating another TTS engine. Built-in voice presets are versioned configuration data, while Designed Voices, Reference Voices, favorites, recent usage, and project/section assignments are persisted through `VoiceService` and `VoiceRepository`.

Built-in presets are fictional app configurations rather than identities of real people. The starter catalog includes five English presets (James, Maya, Oliver, Sophie, Leo) and four Khmer presets (Sokha, Dara, Sreypov, Ratha), with News, Story, Documentary, Professional, Friendly, Educational, Energetic, Calm, Conversational, and Dramatic style categories. Browsing supports local search, category/language/engine filters, favorites, recently used sorting, and deterministic project-language/workflow recommendations.

User voices live globally under the application-managed `voices/` folder. Designed voices persist their VoxCPM2 design prompt and friendly defaults. Reference voices require explicit permission confirmation and copy the validated recording into managed local storage; Phase 9 never uploads reference recordings. Replacing a reference validates/copies the new recording before retiring the old managed copy.

SQLite schema version 6 adds `voice_profiles` and `voice_preferences`, plus `projects.default_voice_id` and `script_sections.voice_override_id`. Voice resolution is deterministic: a section override wins, otherwise the project default is used, otherwise generation asks the user to choose a voice. Project duplication preserves global voice IDs; deleting a project never deletes global voices. Deleting an assigned user voice is blocked unless the user explicitly chooses assignment cleanup, while previously generated WAV files remain untouched.

The Voice Studio uses the existing Phase 8 `TTSController`, `TTSService`, and `NarrationService` for preview, section narration, and full narration. Friendly Pace/Energy/Tone controls are translated into VoxCPM2 design wording instead of inventing unsupported model parameters; CFG, inference steps, seed, and device remain secondary Advanced controls. Generated previews reuse the Phase 5 playback controller and a session cache keyed by voice ID, text, settings, and model identity. Recent narration takes can be played, promoted to Active, or removed without destroying earlier successful takes automatically.

The Script workspace shows the current project voice and selected-section override. Section narration resolves the override first; full narration uses the project voice. The Voice Studio remains browsable when VoxCPM2 is not installed and links to Models instead of crashing or hiding the catalog.

Phase 9 does **not** add Whisper, transcription, translation, subtitles, scenes, timeline editing, News automation, final rendering, or batch voice generation.

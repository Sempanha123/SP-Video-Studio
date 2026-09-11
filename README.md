# SP Video Studio

SP Video Studio is a native Windows desktop video-creation application built with Python 3.11–3.14, PySide6, Qt Quick, and QML.

## Current milestone

Phase 0 foundation through Phase 13 scenes + **Phase 14 structured AI Director planning foundation**.

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
- Polished Voice Studio with English/Khmer presets, Designed/Reference voices, favorites, and project/section assignments
- Lazy faster-whisper STT adapter with CPU/CUDA device and compute-type policy
- Timestamped transcript persistence with optional word timestamps, VAD, search/edit/reset, UTF-8 export, and source-staleness detection
- Shared AI resource coordination so VoxCPM2 and Whisper do not independently consume conflicting GPU resources
- Provider-based English↔Khmer translation with local Marian/OPUS and manual-review providers
- Side-by-side Translation Review with machine-output preservation, human edits, review/lock protection, source synchronization, and UTF-8 export
- Professional Subtitle Studio with transcript/translation/bilingual/manual tracks, editable millisecond timing, source-safe synchronization, live overlay preview, reusable styles/presets, word highlighting, SRT/VTT/ASS import/export, and short FFmpeg/libass burn-in previews
- Reusable Scene Engine + storyboard editor with script/transcript creation, project media/narration/subtitle references, normalized overlays, transitions, validation, and renderer-ready sequence specs
- Offline structured AI Director with deterministic platform/workflow rules, script/scene duration planning, voice/subtitle/visual/audio recommendations, plan locking/versioning, source fingerprints, safe apply modes, and Scene Engine integration

Not implemented yet: cloud LLM Director providers, web/news research, automatic News/Story content generation, speaker diarization, dubbing, advanced timeline editing, AI image/video generation, final production video rendering/export, or batch processing.

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

For local faster-whisper transcription, install the optional speech-recognition runtime:

```powershell
pip install -e ".[ai]"
```

For local English↔Khmer translation, install the optional local translation runtime:

```powershell
pip install -e ".[translation]"
```

The desktop app remains usable without this optional runtime because Manual Translation is always available. Local model weights are installed separately through the Model Manager and are never bundled automatically.


Phase 10 targets the official `faster-whisper` 1.2.1 API and CTranslate2 4.8.2. The application imports both lazily; missing STT dependencies do not prevent the desktop app from starting.

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

Phase 9 itself remains focused on Voice Studio. Phase 10 adds speech-to-text separately without changing the Phase 9 voice-profile architecture.


## faster-whisper speech-to-text

Phase 10 integrates the official `faster-whisper` API behind `FasterWhisperEngine`. The adapter targets the current 1.2.1 API and keeps `faster_whisper`/CTranslate2 imports lazy, so the application can still launch when speech-recognition dependencies or models are missing. The optional `ai` dependency group pins a current CTranslate2 4.8.x runtime.

The engine loads only Phase 7 managed Whisper model folders (`whisper-small`, `whisper-medium`, `whisper-large-v3`) with local-files-only behavior. It supports standard `WhisperModel` transcription and the current `BatchedInferencePipeline`, optional word timestamps, Silero VAD, initial prompts, hotwords, English/Khmer explicit language selection, and automatic language detection. Translation mode is intentionally not exposed in Phase 10.

### Device and compute policy

Device/precision selection is service-owned rather than hardcoded in QML:

- **CPU** defaults to `int8` when supported.
- **CUDA** defaults to `float16`; Low Memory may prefer `int8_float16` when CTranslate2 reports support.
- **Auto** chooses CUDA only when current readiness plus a live CTranslate2 capability check confirm it; otherwise CPU is used.
- Unsupported device/compute combinations produce typed, user-friendly STT errors instead of raw CTranslate2 exceptions.

CTranslate2 CUDA readiness is deliberately separate from PyTorch CUDA readiness. Current upstream GPU builds require a compatible CUDA/cuDNN runtime; the adapter asks CTranslate2 for supported compute types before loading.

### Transcript storage

SQLite schema version 7 adds:

```text
transcripts
transcript_segments
transcript_words
```

A transcript stores model/device/language/settings metadata and an efficient source fingerprint. Segment and word timestamps are stored as integer milliseconds. Segment edits preserve `original_text`, allowing **Reset to Generated Text** without retranscribing. Regeneration creates a new transcript first and only makes it active after successful completion, so a failure or cancellation never destroys the previous good transcript.

If the project-managed source media changes after transcription, the old transcript is kept and marked **Out of Date**. TXT export is UTF-8 and preserves Khmer text. Project duplication creates new transcript/segment/word IDs and remaps them to the duplicated media IDs; project deletion removes transcript rows through the normal project-owned database lifecycle.

### Transcription workflow

The project workspace now provides **Media / Script / Transcription**. Selecting an audio/video item carries its managed Phase 4 path into the Transcription panel. The normal setup exposes model, Auto/English/Khmer language, Auto/CPU/CUDA device, Word timestamps, and VAD; compute type, batch mode/size, beam size, initial prompt, and hotwords remain under **Advanced**.

The faster-whisper segment iterator is always consumed inside the worker job. Progress is estimated from the latest segment end versus media duration when duration is known. Cancellation is checked between generated segments and discards incomplete output by default. No hidden model download occurs from Transcribe; missing models link users back to Models.

Transcript rows are editable with debounced autosave, local search, original-text reset, Copy Full Transcript, and TXT export. Clicking **Play** on a segment reuses the Phase 5 playback controller and seeks the selected media to the segment start rather than creating another player.

### AI memory coordination

`AIResourceManager` coordinates heavy local engines. Before CUDA STT loads, an idle VoxCPM2 engine can be unloaded; an active TTS job blocks conflicting STT acquisition rather than allowing both models to consume GPU memory unpredictably. The same coordinator is registered with TTS for the reverse direction.

### Testing real faster-whisper

The normal test suite uses `FakeSTTEngine` and fake current-API adapters. It never loads a real Whisper model. The real integration test is explicitly opt-in:

```powershell
$env:SPVS_RUN_FASTER_WHISPER_INTEGRATION="1"
$env:SPVS_WHISPER_MODEL_PATH="C:\\path\\to\\managed\\whisper-model"
$env:SPVS_WHISPER_MEDIA_PATH="C:\\path\\to\\short-authorized-audio.wav"
$env:SPVS_WHISPER_DEVICE="cpu"
$env:SPVS_WHISPER_COMPUTE_TYPE="int8"
pytest -m faster_whisper tests/test_faster_whisper_integration.py
```

For CUDA, configure the target machine with a CTranslate2-compatible CUDA/cuDNN runtime and select a supported compute type. English and Khmer quality must be reviewed on real authorized audio before release; automated file/persistence tests do not claim perfect recognition accuracy.

Phase 10 does **not** implement translation, final SRT/VTT/ASS subtitle generation/styling, speaker diarization, dubbing, scenes, timeline editing, News workflows, or video rendering.


## Multilingual translation and review

Phase 11 adds a provider-based translation layer that keeps source data independent from translated data. `TranslationService` coordinates the generic `TranslationEngine` interface, source synchronization, persistence, review state, and Model Manager integration. The first providers are **Local Translation** (`LocalMarianEngine`) and **Manual Translation**. Manual Translation requires no model or network and creates review rows with empty target text so the localization workflow remains usable even when AI dependencies are unavailable.

SQLite schema version 8 adds:

```text
translations
translation_segments
```

Each translation document records its source type (`transcript`, `script`, or `manual_text`), source/target language, provider/model identity, source fingerprint, status, settings, and metadata. Each translation segment stores source mapping/timestamps, a stable source hash, immutable machine output (`machine_translation`), user-facing reviewed text (`translated_text`), and explicit edit/review/lock state. Human corrections never overwrite the original machine result.

### Local English ↔ Khmer models

The Phase 7 Model Registry now contains two verified Apache-2.0 OPUS/Marian entries:

- `translation-en-km-opus` → `Helsinki-NLP/opus-mt-en-mkh` — English → Khmer
- `translation-km-en-opus` → `Helsinki-NLP/opus-mt-mkh-en` — Khmer → English

The English→Khmer adapter applies the model-required `>>khm<<` target token internally. Model identifiers, licenses, language pairs, required files, and size guidance live in the registry rather than QML. The adapter uses direct `AutoTokenizer` + `AutoModelForSeq2SeqLM` loading from the Phase 7 managed local folder with `local_files_only=True`; no hidden Hugging Face network download occurs from Translation. Transformers/PyTorch are imported lazily. Auto device selection intentionally prefers CPU for these relatively small models unless the user explicitly chooses CUDA, reducing unnecessary competition with VoxCPM2/Whisper.

The model licenses and canonical identifiers above were verified on 2026-09-11. Application code licensing and model licensing remain separate; the app does not assume that arbitrary open weights are commercially redistributable.

### Review and protection workflow

Transcript translation preserves the Phase 10 segment ID plus start/end timestamps. Script translation preserves enabled section IDs/order/title metadata and excludes disabled sections. Original transcripts/scripts are never modified. The Translation workspace focuses on **SOURCE | TRANSLATION** review with search/filter, debounced editing, Reviewed and Lock states, per-row reset/retranslate, source playback for transcript rows, review progress, approval, and translated/bilingual UTF-8 TXT export.

Machine translation and reviewed text are deliberately separate. Bulk retranslation skips locked rows and protects manually edited rows by default. Retranslating a manually edited row requires an explicit replacement choice. Cancellation keeps successfully completed rows as Draft and Resume processes remaining/failed rows rather than discarding finished work.

Placeholder/term protection covers template placeholders, URLs, email-like tokens, and explicit Keep Terms. Simple post-generation checks flag empty output, missing numbers/protected terms, same-as-source long text, extreme length ratios, and model control tokens as **Needs Attention**; these are review heuristics, not invented confidence scores.

### Source synchronization

Translation documents use SHA-256 source fingerprints and each translation row has a source hash. If the underlying transcript or script changes, the translation becomes **Out of Date** without deletion. **Sync Source** preserves unchanged reviewed/locked translations, updates pure reorder operations, creates Pending rows for new source segments, marks removed rows Orphaned, and marks only changed source rows Needs Attention. This avoids throwing away human localization work.

Project duplication creates independent translation/segment IDs and remaps duplicated transcript/script source IDs while preserving reviewed text, manual edits, and locks. Project deletion removes project-owned translation records through SQLite cascade without touching global models, voice profiles, source media, or external files.

### Future subtitle and dubbing contracts

`get_reviewed_translation_segments()` returns reviewed target text with source timing for the future subtitle engine. `get_dubbing_segments()` exposes source/target/timing/review metadata for a future dubbing phase; Phase 11 itself does not generate translated speech or subtitle files.

### Testing real local translation

Normal tests use `FakeTranslationEngine` and never download real model weights. Real local-model testing is opt-in:

```powershell
$env:SPVS_RUN_TRANSLATION_INTEGRATION="1"
$env:SPVS_TRANSLATION_EN_KM_PATH="C:\path\to\managed\en-km-model"
$env:SPVS_TRANSLATION_KM_EN_PATH="C:\path\to\managed\km-en-model"
pytest -m translation tests/test_translation_integration.py
```

A non-empty generated result is only an integration check. English→Khmer and Khmer→English publication quality still requires human review, especially for names, numbers, quotes, and domain terminology.

Phase 11 does **not** implement dubbing, translated TTS, final subtitle files/styling, scenes, timeline editing, News research, or rendering.


## Professional subtitle engine and Subtitle Studio

Phase 12 stores subtitles as editable project data rather than as an SRT/VTT/ASS text blob. SQLite schema version **9** adds `subtitle_tracks`, `subtitle_cues`, `subtitle_words`, `subtitle_styles`, and global `subtitle_user_presets`. Tracks can originate from a Phase 10 transcript, a reviewed Phase 11 translation, an aligned bilingual transcript+translation pair, an imported subtitle file, or a new manual track.

A `SubtitleCue` keeps integer-millisecond start/end timing, primary and optional secondary text, source mapping/hash metadata, edit/lock state, and optional `SubtitleWord` rows. Transcript-generated tracks preserve real Whisper word timestamps. Translated tracks deliberately do **not** invent target-language word timing; word highlighting is available only when the displayed language has genuine word timing. Subtitle edits are independent from their transcript/translation source and are never pushed back automatically.

### Source synchronization and project lifecycle

Source links are stable IDs plus SHA-256-derived cue hashes. **Sync Source** preserves manually shortened/rephrased subtitle text, marks changed source cues instead of overwriting them, adds new source cues, and keeps deleted/missing-source tracks editable/exportable. Bilingual alignment uses the translation row's `source_segment_id`, not row position.

Project duplication creates new track/style/cue/word IDs and remaps duplicated transcript/translation source IDs, including bilingual transcript metadata. Project deletion removes project-owned subtitle rows through the normal database lifecycle but leaves global user subtitle presets untouched. Track deletion never deletes its transcript, translation, or media source.

### Styling, presets, and preview

Built-in versioned presets live in `resources/subtitles/presets.json`: **Clean, News, Bold, Minimal, Creator, Karaoke, Documentary**. Applying a preset copies its effective values into a project-owned `SubtitleStyle`, so later preset updates do not unexpectedly restyle existing projects. Users can save/delete their own global presets; built-ins are protected.

Styles use domain values for font, reference-resolution font size, weight, colors, outline, shadow, optional background, alignment, normalized margins/vertical position, line limits, highlight colors, and bilingual secondary scale. The preferred default family is **Noto Sans Khmer** when available, with normal system/font fallback behavior. The QML preview uses the existing Phase 5 player plus a lightweight overlay and binary-search/current-index timing updates; it does not query SQLite on every playback frame.

The optional **Render Preview** action writes a temporary ASS file under the project cache and runs FFmpeg/libass in the existing worker pool to produce only a short burn-in test clip. It is not the final video renderer. Subtitle/filter paths are escaped centrally for Windows drive colons, spaces, brackets, quotes, and Unicode/Khmer paths.

### Timing and validation

The timing service supports add/delete, split at a reviewed time/text boundary, merge adjacent cues, chronological order normalization, shift-all/selected timing, and safe negative-time rejection. Validation distinguishes hard errors from quality warnings. Hard errors include invalid/negative timing. Warnings cover overlaps, very short/long cues, excessive line count, safe-margin concerns, and language-aware reading speed; Khmer uses character-based heuristics instead of English whitespace word assumptions.

Playback cue lookup and word lookup are binary-search based. A 1,000-cue regression test verifies that large project tracks can be loaded, validated, searched through the model, and resolved by playhead without database polling per frame.

### Subtitle import/export

Subtitle project data is format-neutral. Dedicated exporters produce:

- **SRT** with UTF-8 and `HH:MM:SS,mmm` timing.
- **WebVTT** with its own `WEBVTT` structure and period millisecond timing.
- **ASS** with generated Script Info, style and event sections, proper ASS color conversion/alpha handling, escaping, alignment, and bilingual line output.

SRT and VTT imports preserve multiline Unicode text/timing. Basic ASS event import is supported; arbitrary third-party ASS override-tag/style round-trip is intentionally not claimed. Importing external subtitle files creates independent editable tracks with a selected app preset.

English and Khmer export/import are UTF-8. During Phase 12 validation, FFmpeg 7.1.5 + libass successfully rendered a short Khmer ASS preview using the installed **Noto Sans Khmer** font with visible Khmer glyphs and no missing-box rendering in the inspected frame.

Phase 12 did not include scenes or rendering; Phase 13 now adds the reusable scene/storyboard layer while final rendering and the advanced timeline remain future work.


## Scene engine and storyboard editor

Phase 13 introduces one generic scene architecture shared by future normal-video, Shorts, Story, News, documentary, translation and other workflows. Scenes are project-owned editable composition records; workflow-specific automation can add metadata later instead of creating separate scene models.

SQLite schema version **10** adds:

```text
scenes
scene_layers
scene_overlays
```

A `Scene` has a stable ID, deterministic zero-based order, explicit millisecond duration, enabled state, optional visual/narration/subtitle references, optional script/transcript/translation source relationships, media source range, fit mode, background, audio preferences, transitions and metadata. `SceneLayer` and `SceneOverlay` use normalized 0.0–1.0 geometry so future rendering is independent from the desktop preview size. Overlay records support text/headline, lower-third, label and logo foundations without introducing keyframe animation or a full compositing timeline.

### Scene creation and source relationships

The storyboard can create empty scenes manually, create one scene for each enabled script section, or group a transcript into practical time ranges. Script-created scenes preserve the source section ID and SHA-256 source hash, use narration-duration estimates, and attach the latest completed section narration when available. Transcript-created scenes reuse the project-managed source video and preserve source start/end ranges; they do not create new trimmed files.

Source relationships never make a scene a live mirror. If a script section changes, the scene is marked **Source Changed** while its media, overlays, duration edits and other composition work remain untouched. Deleted script sources become **Source Missing** and the scene remains editable. Explicit **Sync Script** / **Sync Scene from Script** actions update relationship metadata without silently resetting visuals or overlays.

### Storyboard editing

The project workspace now includes **Scenes** with a lightweight storyboard + visual preview + inspector. Users can add, move, duplicate, delete, enable/disable and rename scenes; assign project images/videos; choose Fill/Fit/Stretch; configure a simple video source range; enable a solid background; select generated narration and project subtitle tracks; configure source/narration audio preferences; and choose Cut/Fade/Crossfade/Slide transition metadata.

Scene cards use existing media thumbnails and never instantiate their own media player. **Play Scene** routes through the existing Phase 5 `PlaybackController`; generated narration preview also reuses the shared external-audio playback path. The QML composition preview draws images/thumbnails and normalized overlays interactively, while actual video playback remains in the shared player. This is a preview approximation, not final mix/render accuracy.

### Overlays and Khmer text

Scenes support basic Headline, Lower Third and Logo overlays. Text and positions are stored as Unicode/domain data rather than QML pixel state. English, Khmer and mixed text persist directly through SQLite/JSON serialization. Logo assets reference project media and keep PNG/WebP alpha for the QML preview. Overlay opacity is clamped and geometry is normalized; validation warns when important overlay bounds move outside the recommended safe region.

### Duration, validation and render preparation

Scene duration is always explicit. New scenes default to five seconds. Script-created scenes use estimated narration duration unless a completed section narration supplies a real duration. Users may explicitly **Match Scene Duration to Narration**; the system never silently truncates narration or changes a user-edited duration.

`SceneValidationService` reports missing visual/narration/subtitle assets, invalid video ranges, video-shorter-than-scene warnings, invalid overlay timing/bounds and excessive transition duration. Disabled scenes remain stored but are excluded from total enabled duration and future render sequences.

`ScenePreviewService` produces renderer-neutral data through:

```text
build_scene_render_spec(scene_id)
build_project_scene_sequence()
```

The project sequence contains enabled scenes in stable order with cumulative `startMs`/`endMs` positions. Phase 13 uses a documented **sequential, no-overlap preview timeline**. Crossfade overlap semantics are preserved as transition metadata for the future renderer rather than pretending final render math is already implemented.

### Project lifecycle

Project duplication creates new scene/layer/overlay IDs and remaps all project-owned relationships to the duplicate: media IDs, generated-audio IDs, script-section IDs, transcript/translation segment IDs and subtitle-track IDs. Logo/layer media references are remapped as well. No writable scene child row is shared between projects. Scene deletion removes only scene-owned rows; it never deletes project media, generated narration or subtitle tracks. Project deletion removes scene data through the normal project cascade.

Phase 13 intentionally did **not** implement AI scene generation, the advanced timeline, final FFmpeg rendering, automated News/Story workflows, keyframe motion graphics or batch rendering. Phase 14 now adds structured production planning above this scene foundation without rendering or generating factual content.


## AI Director foundation

Phase 14 adds an offline-first production-planning layer that produces **typed structured data**, not chat prose. SQLite schema version **11** adds `director_plans` and normalized `director_scene_plans`; recommendations remain schema-versioned structured data with a recorded Director rule-engine version so saved plans remain understandable as planning rules evolve.

The current provider is `DeterministicDirectorProvider`. It requires no network, no credentials, and never sends project content outside the application. The Director provider contract is structured-output oriented so a future LLM provider must return data that can be parsed and validated into the same `DirectorPlan` domain before it can be shown or applied. Phase 14 deliberately includes no cloud model, web research, factual News generation, automatic final-script writing, AI image/video generation, rendering, or timeline automation.

### Requests, sources, and deterministic rules

`DirectorRequest` supports the creative workflows `news`, `story`, `translate`, `video`, and `shorts`; platforms `tiktok`, `youtube_shorts`, `instagram_reels`, `youtube`, `facebook`, and `generic`; English/Khmer project language; fixed or custom millisecond duration; audience/style/pace/tone preferences; and source types Idea, Script, Transcript, Translation, or Existing Scenes.

Platform/workflow rules are centralized in typed profiles rather than QML conditionals. They deterministically recommend aspect ratio, effective pace, script-length target, scene count/distribution, structural hook/outro guidance, voice category, subtitle preset, visual style, transition style, and music level. Existing Script analysis reuses the established English WPM and Khmer character-duration heuristics instead of treating Khmer as whitespace-delimited English. The same request under the same rule version produces the same plan; Phase 14 uses no randomness.

Manual News ideas receive structure only. The Director explicitly warns that factual News Studio generation will require sources later and does not invent claims, quotes, sources, or research. Story planning provides structural stages only; Translate planning can recommend target-language/dual subtitles and voice direction without generating dubbing.

### Plans, review, locking, and regeneration

A `DirectorPlan` stores stable IDs, workflow/platform/language/target duration/aspect ratio, status, schema/rule versions, source fingerprint, structured recommendations, and editable `DirectorScenePlan` rows. Projects can keep multiple plans for different platforms/durations, select one active plan, duplicate/delete plans, and reopen all choices after restart.

Recommendation cards show a concise value + reason and remain user-editable. Users can lock important choices and regenerate only unlocked recommendations, or regenerate a selected category such as Scenes, Voice, Subtitles, or Visuals. Manual/locked recommendations are preserved. Editing the planned scene count rebuilds structured scene-plan rows while keeping their combined duration aligned with the target. Plan validation checks supported identifiers, positive duration/counts, scene timing tolerance, and currently available voice/subtitle recommendation targets before approval/apply.

Source fingerprints use SHA-256 over relevant source structure for Script, Transcript, Translation, Existing Scenes, or the stored manual idea. Changed project source data marks a saved plan **Out of Date** rather than deleting it. Refresh/regeneration preserves locked/user-modified choices where possible.

### Applying plans and Scene Engine integration

Approval and Apply are intentionally separate. `DirectorApplyService` presents impact information and supports explicit modes:

- **Settings Only** — the safe default when scenes already exist.
- **Add Planned Scenes** — creates new placeholders through the existing `SceneService`.
- **Replace Existing Scenes** — explicit/destructive and never chosen silently.

Application can update project aspect ratio, an explicitly selected existing Voice Studio voice, the project default subtitle preset preference, Director metadata, and planned scenes. It never regenerates narration/audio automatically and never rewrites existing subtitle tracks. Each planned scene is converted through the Phase 13 Scene Engine with duration/transition/source mapping and generic visual notes; renderer logic never parses QML state.

Project duplication creates independent Director plan/recommendation/scene-plan IDs and remaps project-owned Script/Transcript/Translation sources and scene-related references to duplicated entities where available. Deleting a plan never deletes scenes, scripts, media, voices, or subtitles; deleting a project removes project-owned Director data through the normal database lifecycle.

### Privacy and next phase

The Phase 14 Director is entirely local/deterministic and can operate with network access disabled. No project text is uploaded anywhere. The UI labels this as **Local Director / Offline Planning** rather than presenting it as an online generative chatbot.

The recommended next phase is **Phase 15 — FFmpeg Rendering Engine**.

## Production FFmpeg rendering engine

Phase 15 adds a renderer that consumes the renderer-neutral scene specifications created by the Phase 13 Scene Engine. The UI never constructs FFmpeg commands. The production flow is:

```text
Project → SceneService render specs → RenderPlan snapshot → staged FFmpeg renderer
        → output validation → persistent RenderOutput history
```

SQLite schema version **12** adds `render_jobs` and `render_outputs`. A render job records settings, progress/state, expected and actual duration, the immutable render-plan snapshot, FFmpeg version, actual encoder, failure details, and timing metadata. Successful outputs are separate immutable history records; subsequent project edits or renders do not rewrite an old successful video.

### FFmpeg runtime and encoders

Phase 15 was tested with **FFmpeg/FFprobe 7.1.5-0+deb13u1**. Runtime capability discovery parses the actual `ffmpeg -encoders` / `ffmpeg -filters` output once per configured FFmpeg path. The tested build exposes `libx264`, `h264_nvenc`, `h264_qsv`, AAC, libass, HarfBuzz and FriBidi; AMF is not compiled into this build. Encoder presence is not treated as proof that hardware is usable: NVENC/QSV are also probed with a tiny real encode. In the current Linux validation environment neither hardware encoder passed that runtime probe, so **libx264 is the verified mandatory fallback**. Auto mode may use a hardware encoder only after its runtime probe succeeds.

Basic quality choices are mapped inside encoder adapters rather than QML: Fast/Balanced/High Quality map to codec-appropriate x264/NVENC/QSV/AMF options. Phase 15 outputs MP4 with H.264, `yuv420p`, AAC, 48 kHz stereo, and `+faststart` by default.

### Render snapshot and staged composition

Each render takes a stable `RenderPlan` snapshot before FFmpeg starts. Users may keep editing while a worker renders, but the active render continues from its original scene IDs, asset paths/metadata, durations, overlays, transitions, subtitles and settings. Render specs are schema-versioned and record the renderer/FFmpeg version for diagnostics.

Scene composition uses project-managed assets without modifying originals. Image scenes use centralized Fit/Fill/Stretch scale/crop/pad filters. Video scenes use accurate requested source starts/ranges, output FPS normalization and FFmpeg's normal rotation handling. Background-only scenes use a generated color source. Every scene is normalized to the target canvas and a consistent 48 kHz stereo audio stream.

For maintainability and transition reliability, Phase 15 uses **lossless FFV1 + PCM in a NUT intermediate container** per scene. NUT preserves the constant-frame-rate metadata required by FFmpeg 7 `xfade`; no H.264 generation loss is introduced between scene composition and the final encode. Cut-only sequences use stream-copy concat. Crossfade/Slide use `xfade` plus `acrossfade`, with transition overlap subtracted from the expected project duration. Fade is represented as restrained scene fade-out/fade-in semantics. The final stage performs only the production H.264/AAC encode.

### Overlays, Khmer, subtitles, and audio

Scene logos are normal FFmpeg alpha overlays using normalized Phase 13 coordinates, scale, opacity and timing. Text/headline/lower-third overlays are written to temporary ASS and rendered through libass instead of character-by-character `drawtext`; this keeps complex Unicode shaping consistent. The validated default font is **Noto Sans Khmer** when available. An actual Phase 15 output frame containing `ព័ត៌មានថ្មីថ្ងៃនេះ` was visually inspected with shaped Khmer glyphs and no missing boxes.

Project subtitle tracks are burned from the Phase 12 domain through a render-resolution ASS file. English + Khmer bilingual output was also rendered and visually inspected with both lines present and Unicode intact. Windows drive colons, spaces, brackets and Khmer/Unicode subtitle paths use the centralized FFmpeg filter-path escaping helper rather than shell quoting.

Scene audio can include source-video audio and generated narration with their Phase 13 normalized volume settings. Inputs are resampled/formatted to 48 kHz stereo, then mixed with `amix` plus a conservative limiter. Scenes without audio receive a matching silence stream so scene concatenation remains deterministic. Narration longer than a scene is a blocking pre-render validation error; the renderer never silently truncates it.

### Validation, progress, cancellation, and history

Pre-render validation checks FFmpeg availability, enabled scenes, durations, missing visual/logo/narration assets, unresolved video ranges, low-resolution media warnings, libass availability when required, subtitle availability/staleness, aspect-ratio mismatch warnings, actual encoder readiness, output location and conservative temporary disk-space requirements. A doomed render does not start.

FFmpeg progress uses `-progress pipe:1` machine-readable output. The parser handles both current `out_time_us` and the historic microsecond-valued `out_time_ms` key, including temporary `N/A` values. Overall UI progress is deterministic across scene rendering, scene combination and final encoding. Rendering runs through the existing worker pool and only one production render runs at a time.

Cancellation first terminates the active FFmpeg process and escalates to kill after a timeout when necessary; partial `.part.mp4` output and guarded job temp directories are removed. A real `-re` 20-second synthetic FFmpeg run was cancelled during Phase 15 validation and its process exited cleanly. Application shutdown also asks the RenderController to cancel the active render.

After final encoding, FFprobe verifies a non-empty readable video stream, expected dimensions/FPS, duration within tolerance and the expected audio stream before the job becomes Completed. A thumbnail is created with the existing thumbnail service. Render history persists across restart and completed files can be played through the single Phase 5 playback stack or revealed in their folder.

### Project lifecycle and performance check

Project renders live under `project/renders/`; render intermediates live under the guarded `project/cache/render/<job-id>/` directory. Managed-output deletion refuses paths outside the project render folder. Project deletion follows normal project-owned cleanup. **Project duplication deliberately does not copy `renders/` or render cache/history**, avoiding potentially huge derived artifacts; it creates a clean empty render folder for the duplicate.

The normal automated suite uses tiny fixtures. A separate Phase 15 performance smoke rendered a real **60-second 1920×1080 / 30 fps** sequence of six alternating image/video scenes using software `libx264` Fast quality. On this validation host it completed in **24.73 seconds (~2.43× realtime)**, produced a 59.967-second validated video, and the Python process reported roughly 102 MiB peak RSS. This is a functional smoke on simple synthetic content, not a hardware performance guarantee.

Phase 15 intentionally does **not** add the advanced timeline, News/Story/Shorts automation, dubbing workflow, Batch Factory, publishing, cloud rendering, or the polished Phase 16 export experience.

## Polished export workflow and platform presets

Phase 16 adds a dedicated Export layer **above** the Phase 15 renderer. The export UI never creates FFmpeg commands and does not contain a second rendering implementation. The production flow is now:

```text
ExportPreset → ExportRequest → Export validation → RenderPlan snapshot
             → existing RenderService → RenderOutput / export history
```

### Export presets

Builtin presets are stored in the versioned `resources/export/presets.json` registry rather than QML. The registry currently provides TikTok, YouTube Shorts, Instagram Reels, YouTube, Facebook Vertical/Square/Landscape, Generic Vertical/Landscape/Square, and an editable Custom starting point. These are MMO Video Studio defaults, not claims that a platform accepts only one resolution or duration.

Vertical presets start at 1080×1920 / 9:16 / 30 FPS, square at 1080×1080, and landscape at 1920×1080. YouTube can follow the project FPS. Basic quality remains Fast/Balanced/High Quality and delegates to the Phase 15 encoder-quality mappings. Encoder choices are friendly names backed by the Phase 15 runtime encoder registry; hardware entries are shown only when the FFmpeg build exposes them **and** the runtime probe succeeds. Software H.264 remains the safe fallback.

SQLite schema version **13** adds `export_presets` for user-created presets and `project_export_profiles` for per-project last-used export choices. Builtin presets are immutable. Users can duplicate any preset into a custom preset, rename/edit/delete user presets, and save the current settings as a new preset. Custom preset data survives restart without mutating builtin definitions.

### Filenames, output folders, and conflicts

`ExportFilenameService` preserves normal Unicode—including Khmer—while replacing only invalid filesystem characters and reserved device names. MP4 extension normalization converts inputs such as `video`, `video.mp4`, or `video.mov` to one clear `.mp4` filename instead of producing double extensions.

File conflicts are explicit: **Keep Both** (default) produces `video_2.mp4`, **Replace** targets the recorded path intentionally, and **Cancel** refuses to start. Output folders are checked/created and write-tested before export. Export history records whether the output is managed under the project or is an external user-selected path. Managed deletion remains path-guarded; external files require an explicit stronger confirmation and only the exact recorded output is eligible for deletion.

### Subtitle and audio behavior

Export can use no subtitles, burn a selected Phase 12 subtitle track into the video, or export SRT/VTT/ASS beside the completed MP4. External subtitle serialization delegates to `SubtitleService`; Phase 16 does not duplicate SRT/VTT/ASS writers. The project default subtitle track is preferred when one exists. Bilingual tracks continue through the validated Phase 12/15 ASS/libass path.

Audio may be enabled with Standard or High AAC quality, or disabled entirely. No-audio output is implemented as a small Phase 15 setting extension: scene composition stays deterministic, while the final MP4 encode omits the audio stream and output validation expects no audio.

### Export UX, progress, and history

The project workspace now exposes **Export** and `Ctrl+E` opens the same workflow. Users choose a preset, review resolution/FPS/quality/encoder/subtitles, choose Fit/Fill/Stretch behavior for aspect conversion, select folder/filename/conflict policy, validate, then start export. Validation reuses Phase 15 project/render checks and adds informational platform/aspect-duration warnings plus an explicitly labeled estimated output size.

Before export starts, Script, Transcript, Translation, and Subtitle autosaves are flushed. A failed save prevents the export snapshot from starting. Once started, settings are immutable for that render job and progress/cancellation come directly from the existing RenderService machine-readable FFmpeg progress path. The UI does not invent a second progress system or imply that rendering continues after the app exits.

Completed exports show Play Video, Open File, Open Folder, and Export Another Version. Playback reuses the Phase 5 player. Export Again restores the settings saved in the previous `RenderOutput` metadata but renders the **current** project content. Recent exports remain persistent after restart, expose missing-file state safely, and can be removed from history without crashing if a user moved/deleted a file externally.

### Phase 16 validation

The normal suite uses small deterministic fixtures, while real FFmpeg integration verifies the Export layer against the Phase 15 renderer. Validated outputs include a real TikTok 1080×1920 export, YouTube 1920×1080 export, Khmer burned subtitle output in a Khmer-named directory/file, external UTF-8 Khmer SRT, Keep Both collision generation, and render-history reload after a new application container is created. Phase 15's real bilingual English+Khmer burn, cancellation, output validation, and hardware-fallback tests continue to run unchanged.

Phase 16 remains fully local: no upload, social-platform API, cloud render service, telemetry, advanced timeline, News/Story/Translate&Dub workflow, or Batch Factory is introduced. The recommended next phase is **Phase 17 — Advanced Timeline Editor**.

# Phase 39 — Windows 11 Manual QA Checklist

Use a disposable QA project root. Do not use production/customer projects. Record failures in `docs/known-issues.md` with severity, workflow, reproduction, workaround and target fix.

## Environment matrix

- [ ] Windows 11, current supported Python, non-admin user
- [ ] Project root path containing spaces
- [ ] Unicode path/profile if feasible: Khmer `ខ្មែរ`, Thai `ไทย`, Vietnamese `Việt`
- [ ] CPU-only/no CUDA machine
- [ ] CUDA machine when available
- [ ] 100% display scale
- [ ] 150–200% display scale
- [ ] Light theme
- [ ] Dark theme
- [ ] Offline/disconnected mode

## Fresh install-like developer run

- [ ] Start with empty disposable app-data/project roots
- [ ] App launches without crash
- [ ] First-run onboarding is optional/skippable
- [ ] Continue Without AI enters editor
- [ ] FFmpeg-missing state is actionable and does not block manual editing
- [ ] Create first Blank Video project

## Normal Video

- [ ] Import video, image and audio
- [ ] Add/move/select timeline clips
- [ ] Split a selected clip by keyboard and mouse
- [ ] Add overlay text containing Khmer/Thai/Vietnamese characters
- [ ] Add/edit SpeechBlock text
- [ ] Assign a voice
- [ ] Generate with installed engine or deterministic dev fake
- [ ] Create/edit subtitles
- [ ] Add music and verify mixer controls/ducking
- [ ] Open Export dialog
- [ ] Render H.264/libx264 MP4 and play it externally

## News / Reporter News / Interview News

- [ ] Create News project and add local/source fixture
- [ ] Create/approve a grounded claim
- [ ] Generate/build News script without losing source provenance
- [ ] Reporter mode: reporter speaker + green-screen presenter + B-roll + lower third
- [ ] Reporter mode: subtitles, reporter voice, music ducking
- [ ] Render 16:9 and 9:16 as practical
- [ ] Interview mode: Reporter + Guest with distinct voices
- [ ] Interview mode: split-screen/PIP composition
- [ ] Interview mode: subtitles/mixer/render
- [ ] Reopen and verify provenance/source metadata remains attached

## Story

- [ ] Create Story plan and beats
- [ ] Create Narrator + Character
- [ ] Build/edit script
- [ ] Map beats to scenes
- [ ] Add music/ambience
- [ ] Create subtitles
- [ ] Render and reopen project

## Translate & Dub

- [ ] Import source video
- [ ] Run STT if model installed; otherwise confirm manual/offline path remains usable
- [ ] Translate to a supported target language
- [ ] Review/edit translation before TTS
- [ ] Create SpeechBlocks and assign target voice
- [ ] Adjust dub timing
- [ ] Mix original/dub audio
- [ ] Generate target subtitles
- [ ] Render target MP4

## Shorts

- [ ] Import a long-enough source
- [ ] Set manual In/Out
- [ ] Create Short
- [ ] Verify 9:16 reframe
- [ ] Add/edit hook and captions
- [ ] Add B-roll
- [ ] Render portrait output

## Templates

- [ ] Open Reporter News template
- [ ] Resolve placeholders using Asset Library
- [ ] Apply to a new project
- [ ] Edit/delete template afterward and verify applied project remains independent
- [ ] Import/export `.mmovtemplate` and verify hostile/corrupt package is rejected

## Asset Library

- [ ] Import reusable B-roll
- [ ] Use the same asset from two projects
- [ ] Detach one reference to project-local media
- [ ] Relink referenced asset
- [ ] Confirm delete guard blocks unsafe removal while referenced

## Batch Factory

- [ ] Load a small CSV/JSON input
- [ ] Use Minimal/Reporter template
- [ ] Include language/platform variants
- [ ] Start tiny jobs
- [ ] Pause and resume
- [ ] Force one recoverable failure and retry
- [ ] Verify completed tiny outputs and no orphan FFmpeg process

## Recovery

- [ ] Modify project and wait/create recovery state
- [ ] Simulate unclean shutdown in disposable QA data
- [ ] Reopen and recover
- [ ] Verify text/media/timeline state
- [ ] Render recovered project
- [ ] Corrupt a disposable snapshot and verify safe error/no data overwrite

## Migrations

- [ ] Copy a supported legacy fixture/project
- [ ] Open and allow migration
- [ ] Verify automatic backup exists
- [ ] Edit migrated project
- [ ] Render migrated project
- [ ] Test a project marked with a future schema: it must stay unchanged and offer Open Folder/Cancel
- [ ] Test injected/known migration failure: Diagnostics/backup actions appear

## Storage and cache

- [ ] Inspect Storage settings
- [ ] Change cache location to a safe disposable path
- [ ] Clean cache and confirm projects/assets remain
- [ ] Low disk warning is actionable
- [ ] Repeated cleanup leaves no temp/partial files

## Diagnostics

- [ ] Run Quick Check
- [ ] Run Full Diagnostics and cancel once
- [ ] Confirm no AI model auto-load/download
- [ ] Generate local Support Bundle
- [ ] Inspect bundle for secret/path redaction and absence of project/media/private voice content

## Theme, accessibility, DPI and keyboard

- [ ] Light theme readable at 100%/200%
- [ ] Dark theme readable at 100%/200%
- [ ] Strong focus indicator visible
- [ ] Reduced Motion preference respected
- [ ] Larger interface text does not clip critical buttons
- [ ] Keyboard can create/open project and reach Timeline/Speech/Export basics
- [ ] Command Palette opens, searches and dispatches a safe command
- [ ] Modal dialogs restore focus reasonably
- [ ] Narrator spot-check: major buttons/fields expose useful accessible names

## Multilingual/Unicode

For English, Khmer, Thai and Vietnamese:

- [ ] Unicode project name
- [ ] Script text
- [ ] SpeechBlock text
- [ ] Subtitle text
- [ ] Overlay text
- [ ] Export filename
- [ ] Template name
- [ ] Asset tag
- [ ] Render path/output where supported

## Offline mode

- [ ] Disconnect network
- [ ] Open/create/edit project
- [ ] Manual Timeline/Speech/Subtitles/Mixer remain usable
- [ ] Local deterministic/installed engines work as configured
- [ ] News URL fetch reports offline failure safely
- [ ] No model is downloaded automatically

## Optional real engines

- [ ] VoxCPM2: query actual supported languages, then short English/Khmer smoke only if officially supported/configured
- [ ] Whisper: tiny local sample and language detection/transcription
- [ ] Translation: configured local model, only supported language pairs
- [ ] Unload engines and verify memory/process activity settles

## FFmpeg / hardware encoders

- [ ] `libx264` mandatory software render passes
- [ ] NVENC only if enumerated **and hardware smoke succeeds**
- [ ] QSV only if enumerated **and hardware smoke succeeds**
- [ ] AMF only if enumerated **and hardware smoke succeeds**
- [ ] Cancel active FFmpeg render; confirm no orphan process


## Application updates (Phase 42)

- [ ] Settings → Updates shows current version and Stable channel
- [ ] Manual Check for Updates does not download an installer automatically
- [ ] Disable Automatically Check, restart, and confirm the preference persists
- [ ] Offline check reports `Could not check for updates.` without interrupting editing
- [ ] With a controlled HTTPS test origin, newer version shows the update dialog and plain-text release notes
- [ ] Cancel a download and confirm no `.part`/staged Setup EXE remains; Retry then succeeds
- [ ] Alter the test installer while keeping the original manifest SHA-256; confirm it is rejected/deleted and never launched
- [ ] If release signing is configured, confirm Authenticode publisher validation succeeds for the expected signer and fails for a different signer
- [ ] Start a disposable render and Batch job; Install Now must remain blocked until active work is stopped/finished
- [ ] Make unsaved edits, prepare the update, and verify a pre-update recovery point plus successful autosave flush before handoff
- [ ] Force an autosave failure in disposable QA data and confirm the installer is not launched
- [ ] Confirm the Setup EXE launches as the existing Phase 41 installer and the app exits only after successful process launch
- [ ] After upgrade, confirm settings/models/assets/projects/recovery/logs remain under `%LOCALAPPDATA%\\MMOVideoStudio`
- [ ] Confirm normal Phase 38 migrations run on first launch and the pending marker finalizes only under the intended newer version
- [ ] Storage cleanup may remove stale Update Temp files only while no update is downloading/validating/ready/installing and no pending-update marker exists
- [ ] No automatic downgrade/rollback or forced-update lockout is offered

## Release sign-off

- [ ] `python scripts/run_release_qa.py FAST` passes
- [ ] `python scripts/run_release_qa.py INTEGRATION` passes
- [ ] `python scripts/run_release_qa.py E2E` passes
- [ ] `python scripts/run_release_qa.py PACKAGING_SMOKE` passes
- [ ] Phase 37 security regression passes
- [ ] Phase 38 migration regression passes
- [ ] No open P0
- [ ] Prefer no open P1
- [ ] `test-results/summary.md` and JUnit reviewed

## Phase 43 final production acceptance additions

Run these on the **actual Release build and Setup EXE** in a disposable clean Windows 11 x64 profile. These items are intentionally not considered satisfied by source/configuration tests.

### Clean machine / installer lifecycle

- [ ] Python is not installed and no repository checkout exists on the test profile
- [ ] No developer FFmpeg is on `PATH`; no project-specific environment variables are set
- [ ] Use a non-admin user and install through the Phase 41 per-user installer
- [ ] Fresh install → launch → uninstall → reinstall succeeds without a reboot
- [ ] Upgrade a real previous installer N to candidate N+1 without a manual uninstall
- [ ] Default uninstall preserves `%LOCALAPPDATA%\\MMOVideoStudio` projects/settings/models/assets/templates/recovery/logs/managed exports
- [ ] Explicit optional managed-data removal removes only the documented managed root and leaves external project/export paths untouched
- [ ] Final installed/packaged directory contains no `.env`, credentials, Git metadata, test databases, private media, source screenshots, developer home paths or unnecessary test files

### First launch / display / visual consistency

- [ ] Release executable opens with no console window, raw traceback, missing QML module/plugin or developer error text
- [ ] Onboarding can be completed or skipped and does not require AI models
- [ ] Inspect every primary page at 1366x768 and 100%/200% DPI for token consistency, spacing, buttons, hover/active state, dialogs and typography
- [ ] Khmer and Thai combining marks are not clipped in project names, editor text, subtitles, overlays, Timeline labels and dialogs
- [ ] Force common missing-file/read-only-folder/offline errors; user-facing UI remains actionable and does not show a raw traceback as the primary error

### Paths / files

- [ ] Create/open/export through a path containing spaces
- [ ] Create/open/export through Khmer `ខ្មែរ`, Thai `ไทย` and Vietnamese `Việt` path components
- [ ] Exercise a long Windows path where OS policy/support permits it
- [ ] Use an external referenced asset, then move it and complete relink
- [ ] Attempt a write into a read-only folder; the operation fails safely without corrupting project state

### Render / audio matrix

- [ ] Software `libx264` H.264 passes at 16:9, 9:16 and 1:1
- [ ] Output audio is AAC, 48 kHz, stereo where the export preset requires audio
- [ ] Render subtitles, chroma key, PIP, B-roll and multi-speaker composition
- [ ] Listen manually for clear voice, music ducking, clipping, fades, interview voice balance and dub mix
- [ ] If NVENC/QSV/AMF is present, force a hardware-encoder failure and confirm the workflow falls back safely to software encoding where designed

### Performance / long session

- [ ] Compare startup and representative interaction timings to the recorded Phase 31 baseline on the same workstation class
- [ ] Exercise approximately 1,000 assets, 1,000 Batch items, 1,000 subtitles and 100 audio clips using disposable/generated data
- [ ] Keep the app open for an extended edit/render/project-switch session; record memory, thread count, subprocess count and temporary storage growth
- [ ] Finish/cancel heavy work and verify worker/subprocess/temp usage settles rather than growing without bound

### Recovery / interruption

- [ ] Crash with unsaved disposable edits and recover the project successfully
- [ ] Interrupt a Batch job; restart and verify recovery/retry state is coherent
- [ ] Interrupt a render; restart and verify no stale render state or orphan FFmpeg process blocks future renders

### Update round trip

- [ ] With a controlled test update origin, validate newer-version discovery, offline behavior, cancel/retry, bad-checksum rejection and active-render/Batch protection on the packaged application
- [ ] Complete installer handoff from the updater and verify N+1 launches normally, migrations complete and `last-update.json` finalizes for the intended version only
- [ ] Verify update staging/cleanup never deletes projects, models, exports, recovery data or an in-progress/pending update

### Release notices / signing

- [ ] Review the exact package inventory from the final build and ship all license/notice texts required by the exact PySide6/Qt, Python/runtime and optional AI packages actually bundled
- [ ] Review the exact staged FFmpeg `LICENSE.txt`, `SOURCE.txt` and configure flags before distribution
- [ ] Replace/supplement `APPLICATION_LICENSE_NOTICE.txt` with owner-approved public distribution/application terms
- [ ] If Authenticode signing is part of the release policy, sign the application/installer and configure the updater expected publisher subject; verify a mismatched signer is rejected

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

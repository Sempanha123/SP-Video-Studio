# Phase 35 — Onboarding + First-Run Experience

Phase 35 is a lightweight layer over the completed Phase 34 application. It does not replace project creation, Settings, System Readiness, Model Manager, Language Registry, Templates, performance profiles, accessibility, or editor workflows.

## First-run architecture

`OnboardingService` persists only first-run state in `settings/phase35_onboarding.json`. Normal preferences continue through the existing `SettingsService`. The state contains `status`, `onboarding_version`, current step, default project content language, Continue-Without-AI choice, first project ID, migrated-existing-user flag, dismissed contextual tips, and update time.

States are `not_started`, `in_progress`, `completed`, and `skipped`; current version is `1`. Progress is written after each meaningful step, so closing the wizard preserves valid choices and the last step. Reopening setup never deletes or resets projects, assets, voices, models, templates, or editor data.

## Existing-user migration

If no Phase 35 state exists, `FirstRunService` checks for existing projects and meaningful existing configuration. Configured users are migrated directly to `completed`, avoiding a forced first-run wizard after upgrade. A genuinely fresh default installation starts at `not_started`.

## Setup steps

The compact wizard is: Welcome; Language & Appearance; Projects Folder; System Readiness; AI Features; First Project; Done. It is optional, skippable, closable, keyboard-focused, vertically scrollable, and bounded for 1366×768-class windows. No marketing hero, heavy animation, telemetry, or online tutorial is added.

## Language setup

The wizard uses the existing Language Registry and presents native/display names. English, Khmer, Thai, and Vietnamese sort first, followed by other registered languages. The selection is explicitly a **content language**, not an application UI translation. Engine support text comes from existing registry capabilities rather than invented support tables.

## Appearance and accessibility

System/Light/Dark, Reduce Motion, and Larger Text reuse existing Phase 34 settings. A separate density control is intentionally not invented because the current Phase 28 design system has no real shared Comfortable/Compact preference.

## Project-folder setup

The existing `SettingsService.validate_directory()` remains authoritative for creation/writability. When available, Phase 29 `DiskMonitorService` supplies central disk-health thresholds. Drive roots are rejected as an unsafe project target. Changing the location updates `ProjectService` only for newly created projects and does not move existing projects.

## System readiness

Readiness is requested lazily through the existing Phase 3 `SystemReadinessService` and shared worker pool. The wizard shows FFmpeg, storage, CPU, GPU and optional AI status. No GPU is presented as CPU mode, not app failure. Missing FFmpeg clearly explains that rendering is unavailable while manual editor entry remains allowed.

## AI optionality and models

No model is downloaded automatically. Opening the AI step performs only model discovery, and only when that step is visited. Install/Manage actions hand off to the existing Phase 7 Model Manager. Download sizes are not invented. `Continue Without AI` persists an explicit choice and remains available even if discovery fails or the computer is offline.

Voice generation is described as VoxCPM2, speech recognition as faster-whisper, and translation as configured translation engines. Voice cloning/reference-voice collection is not part of onboarding.

## Performance

The wizard exposes Auto, Low Memory, Balanced, and Maximum Quality through the existing Settings/Phase 31 performance profile path. Auto is the default. No heavy AI model is loaded at startup.

## First-project creation

Blank Video, News, Story, Translate & Dub, and Shorts use the existing `ProjectController.createProject()` path with only name, content language, aspect ratio and existing default FPS. Starting from Template hands off to the existing Phase 24 Template Browser instead of duplicating template application logic. News copy reminds users to add sources before factual production.

## Home, contextual learning and Quick Guide

Home keeps Quick Create, Recent Projects and System Readiness, adds a simple first-project beginner state, Continue Editing, Templates, Getting Started and Quick Guide. A dismissible Project Media vs Asset Library hint demonstrates the persisted contextual-tip system. Setup and Quick Guide can be reopened from the application chrome without resetting data.

The Quick Guide covers creating a project, importing media, adding voice, subtitles, Timeline use and export. Speaker and Voice terminology remains distinct.

## Accessibility and DPI

The wizard uses Phase 34 controls, accessible names, visible focus, keyboard-operable buttons, scrollable content, bounded dimensions and multilingual sample text. The UI is designed to fit 1366×768 class desktops and adapt under high DPI. Live 200%-DPI and Windows Narrator verification still require the real Windows/PySide6 environment.

## Offline and privacy behavior

Onboarding does not require internet. Model discovery/install failure does not block completion. Local-processing copy is deliberately qualified: projects/local models remain local unless the user has configured an online provider.

## Known limitations

- Live PySide6/QML rendering, Windows Narrator and 200% Windows DPI could not be executed in the current sandbox.
- Phase 35 delegates actual model downloads to the existing Model Manager; its downloader behavior is not duplicated.
- A separate UI density option is deferred because no genuine shared density setting exists yet.
- The current app UI remains English; multilingual strings are content/fallback-font test material, not a claim of translated UI.

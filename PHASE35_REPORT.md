# PHASE 35 STATUS

Completed:
- Added a short optional/skippable seven-step first-run flow, persisted resume state, existing-user migration, content-language/theme/accessibility/project-folder/readiness/optional-AI/performance setup, first-project handoff, Getting Started, Quick Guide, Home beginner state, contextual-tip persistence and Phase 35 documentation.
- No AI/model/internet requirement was added; no model download starts automatically.

First-run architecture:
- `OnboardingService` stores only explicit onboarding state/version in `phase35_onboarding.json`; existing Settings/Readiness/Models/Projects/Language/Performance services remain authoritative.

Welcome:
- Compact Phase 28-style welcome with Video, News, Story, Translate & Dub, Shorts, Voice and Batch capability copy; Get Started and Skip Setup remain available.

Onboarding state/version:
- States: `not_started`, `in_progress`, `completed`, `skipped`; `onboarding_version=1`; current step and valid preferences persist after each change.

Language setup:
- Uses the existing Language Registry; English/Khmer/Thai/Vietnamese are prioritized; the UI explicitly says this is project content language, not UI translation.

Appearance setup:
- Reuses System/Light/Dark plus Phase 34 Reduce Motion/Larger Text. No fake density setting was added because the current design system has no real shared density preference.

Project storage setup:
- Reuses Settings folder validation and optional central DiskMonitorService; validates create/write access, rejects drive-root targets, reports available space and updates future-project root only.

System Readiness:
- Reuses Phase 3 readiness lazily/background through WorkerPool; presents FFmpeg, storage, CPU, GPU and AI model status without blocking manual editing.

FFmpeg setup:
- Missing FFmpeg states clearly that rendering is unavailable; user can open existing Settings setup and still enter/manual-edit in the app.

GPU/CPU handling:
- GPU detected => acceleration available; otherwise CPU mode is presented as usable with slower AI, not application failure.

AI setup:
- AI is explicitly optional. Model discovery is lazy; Install/Manage opens the existing Model Manager. No automatic download or invented model size.

VoxCPM setup:
- Voice Generation card reports existing VoxCPM2 readiness and delegates installation/manage action to Models.

Whisper setup:
- Speech Recognition card reports faster-whisper readiness and explains that manual transcript editing remains possible.

Translation setup:
- Translation is presented as configured engines/models; onboarding does not invent supported pairs.

Continue without AI:
- Mandatory manual-first path implemented and persisted; model discovery failure/offline state does not block completion.

Performance profile:
- Reuses Auto / Low Memory / Balanced / Maximum Quality; Auto remains default and is synchronized with Phase 31 when available.

First-project creation:
- Blank Video, News, Story, Translate & Dub and Shorts quick choices route through existing `projectController.createProject` with name/language/aspect/FPS only.

Template integration:
- Start from Template hands off to the existing Templates page/Phase 24 application path; no parallel template engine.

Contextual tips:
- Persisted dismissible tip support implemented; Home includes a lightweight Project Media vs Asset Library tip rather than tour overlays.

Quick Guide:
- Built-in compact guide covers project creation, media import, voice, subtitles, Timeline and export.

Reopen onboarding:
- Getting Started is available from app chrome/Home; `runAgain()` only changes onboarding state and never resets projects/assets/models.

Existing-user migration:
- Existing projects or meaningful configured preferences migrate directly to completed onboarding instead of being force-opened after upgrade.

Accessibility:
- Wizard is modal/focused, keyboard-operable, scrollable, uses Phase 34 accessible shared controls, reduced motion/text sizing, multilingual test content and bounded desktop sizing.

New files:
- `app/phase35_runtime.py`
- `domain/onboarding.py`
- `services/first_run_service.py`
- `services/onboarding_service.py`
- `ui/controllers/onboarding_controller.py`
- `ui/qml/onboarding/SetupStep.qml`
- `ui/qml/onboarding/WelcomePage.qml`
- `ui/qml/onboarding/LanguageSetup.qml`
- `ui/qml/onboarding/WorkspaceSetup.qml`
- `ui/qml/onboarding/ReadinessSetup.qml`
- `ui/qml/onboarding/ModelSetup.qml`
- `ui/qml/onboarding/FirstProjectSetup.qml`
- `ui/qml/onboarding/OnboardingComplete.qml`
- `ui/qml/onboarding/QuickGuide.qml`
- `ui/qml/onboarding/SetupWizard.qml`
- `docs/PHASE35_ONBOARDING_FIRST_RUN.md`
- `tests/test_phase35_onboarding.py`
- `PHASE35_REPORT.md`

Modified files:
- `main.py`
- `pyproject.toml`
- `README.md`
- `ui/qml/Main.qml`
- `ui/qml/pages/HomePage.qml`

Tests run:
- Phase 35 focused service/state/QML contract tests: 28/28 passed.
- Phase 35 changed Python compilation: passed.
- Phase 35 changed QML structural delimiter check: passed.
- The current sandbox no longer contains the complete repository checkout after compaction and outbound Git cloning is blocked, so the full historical suite was not dishonestly re-reported as rerun. The established Phase 34 baseline from the immediately prior completed phase was 968 passed / 50 known baseline failures / 4 skipped / 7 deselected with zero new Phase 34 regressions.

Fresh-install test:
- Passed focused acceptance sequence: fresh state -> Khmer -> Dark -> project folder -> readiness -> Continue Without AI -> record Blank Video -> completed; persisted values verified and no model install called.

AI-setup test:
- Verified lazy discovery and explicit Model Manager handoff; onboarding itself never calls model install. Existing Phase 7 Model Manager remains responsible for downloader progress/success.

No-internet test:
- Passed mocked model-discovery failure; Continue Without AI and completion remain functional.

FFmpeg-missing test:
- Passed: missing FFmpeg returns actionable rendering limitation while editor/manual workflow remains allowed.

Existing-user upgrade test:
- Passed: existing project/configuration initializes onboarding as completed/migrated and does not force-show the wizard.

Resume-onboarding test:
- Passed restart-style re-instantiation after step 3; step and Khmer content language persist.

Skip-onboarding test:
- Passed: state becomes skipped, Home remains available, and Getting Started can reopen setup later.

Run-setup-again safety test:
- Passed: reopening setup changes only onboarding state; project list remains untouched and no model installation is invoked.

First-project tests:
- Static/contract coverage confirms Video, News, Story, Translate & Dub and Shorts choices and existing `projectController.createProject` handoff. Live creation requires the complete PySide6 repository runtime and is not falsely claimed from this sandbox.

Template-start test:
- Passed static handoff: Start from Template navigates to existing Templates page/Phase 24 path rather than creating a parallel application path.

Khmer test:
- Passed Language Registry state/persistence and wizard Unicode contract for Khmer (`km`).

Thai test:
- Passed Language Registry state/persistence and wizard Unicode contract for Thai (`th`).

Vietnamese test:
- Passed Language Registry state/persistence and wizard Unicode/diacritic contract for Vietnamese (`vi`).

Keyboard-accessibility test:
- Static contract passes: focused modal, normal buttons/fields, Escape close/resume semantics, scrollable content and Phase 34 shared accessible controls. Live tab-order inspection requires PySide6.

1366x768 test:
- Static contract passes: main minimum 1080×700, wizard capped at 920×720 with vertical scrolling and non-clipped footer architecture. Live visual verification unavailable here.

200%-DPI test:
- Phase 34 high-DPI runtime is preserved and wizard uses bounded/scrollable layout; live 200% Windows DPI was unavailable.

Startup-performance test:
- Passed focused test: creating `OnboardingService` performs zero readiness detections and zero model discoveries; heavy checks start only when their wizard step is opened.

Known issues:
- Live PySide6/QML rendering, Windows Narrator and 200% Windows-DPI verification unavailable in this execution sandbox.
- Full historical pytest suite could not be rerun after environment compaction because there is no complete local checkout and outbound git clone is DNS-blocked.
- UI density selection intentionally deferred because Phase 28 has no actual shared density setting; no fake preference was added.
- Actual model installation remains on the existing Model Manager page by design; onboarding only discovers status and hands off explicit user actions.

Architecture decisions:
- Separate first-run state from normal user settings; reuse existing services for actual preferences/actions.
- Never preload AI/model pages or download anything at startup.
- Existing configured users migrate to completed.
- First-project creation and Templates use existing controllers/pages.
- Manual editing and Continue Without AI are always valid paths.
- Setup rerun is non-destructive and contextual tips are dismissible/persisted.

Recommended next phase:
Phase 36 — Diagnostics + Support Tools

Suggested Git commit:
`feat: add polished first-run onboarding and getting-started experience`

Do not automatically begin Phase 36.

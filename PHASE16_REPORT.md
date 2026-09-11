# PHASE 16 STATUS

Completed:

* Polished Export workflow layered above the existing Phase 15 `RenderService`; no second FFmpeg/render implementation was introduced.
* Versioned builtin platform preset registry, persistent custom presets, per-project last-used export profile, validation/summary, output folder/filename/conflict handling, progress/cancel/result/history UX, Export Again, safe export deletion, and UTF-8 external subtitle export.
* Project workspace Export module plus `Ctrl+E`, with pre-export autosave flushing before an immutable render snapshot starts.

Export architecture:

* `ExportPreset` → typed `ExportRequest` → `ExportValidationService` → Phase 15 `RenderPlan` → existing `RenderService` → `RenderOutput`.
* Export-specific policy lives in `ExportService`; FFmpeg argv/filter construction remains entirely inside Phase 15 rendering/media modules.
* Schema v13 adds `export_presets` and `project_export_profiles`; successful export settings are also embedded in `RenderOutput.metadata` for Export Again/history.

Builtin presets:

* TikTok, YouTube Shorts, Instagram Reels, YouTube, Facebook Vertical, Facebook Square, Facebook Landscape, Generic Vertical, Generic Landscape, Generic Square, and Custom.
* Registry is versioned in `resources/export/presets.json`; user-facing names are not used as identifiers.

TikTok:

* Default 1080×1920, 9:16, 30 FPS, MP4/H.264/AAC, Balanced quality, burned-subtitle recommendation when a default subtitle track exists.
* Actual FFmpeg export test produced a valid 1080×1920 video.

YouTube Shorts:

* Default 1080×1920, 9:16, 30 FPS, with 60 FPS available as an edit; longer-than-recommended content produces an informational warning only.

Instagram Reels:

* Default 1080×1920, 9:16, MP4/H.264/AAC; no watermark/branding is added.

YouTube:

* Default 1920×1080, 16:9, project-FPS aware; 24/25/30/50/60 FPS remain selectable.
* Actual FFmpeg export test produced a valid 1920×1080 video.

Facebook:

* Separate Vertical 1080×1920, Square 1080×1080, and Landscape 1920×1080 presets.

Custom presets:

* Current settings can be saved as a user preset, duplicated, renamed and deleted; builtin presets cannot be deleted.
* Custom 1080×1920 / 60 FPS / High Quality restart-persistence path is covered by repository tests.

Subtitle export modes:

* None.
* Burn Into Video via the existing Phase 12/15 ASS/libass subtitle path.
* Export SRT, VTT or ASS beside the completed MP4 using `SubtitleService.export`; serialization is not duplicated.
* Default subtitle track selection respects `project.default_subtitle_track` state where available.

Filename/path handling:

* Unicode/Khmer filenames are preserved; only invalid filesystem characters/reserved device names are sanitized.
* MP4 extension normalization avoids `video.mov.mp4` ambiguity.
* Keep Both creates deterministic `_2`, `_3`, ... names; Replace is explicit; Cancel raises a typed conflict.
* Output folders are created/write-tested before start. Managed versus external output classification controls safe deletion behavior.

Export progress:

* Uses Phase 15 render progress/cancellation directly; no fake progress or duplicate FFmpeg process control.
* UI surfaces preparing, scene render, combining, finalizing, completed/failed/cancelled states and current FFmpeg speed when available.

Export history:

* Reuses `RenderOutput` records and extends metadata with preset ID, export request, managed/external classification, subtitle behavior, and external subtitle paths.
* Missing external files remain readable history entries; users can remove the record without crashing.
* Managed file deletion remains inside project render/export roots; external file deletion requires explicit confirmation.

Recent exports:

* Project Export page lists persistent recent outputs with file status, resolution/duration, Play, Open Folder, Export Again, and delete/remove-history actions.
* A new container/repository instance reloads completed outputs and restores Export Again settings.

New files:

* `domain/export_preset.py`
* `domain/export_profile.py`
* `domain/export_request.py`
* `resources/export/presets.json`
* `services/export_filename_service.py`
* `services/export_preset_service.py`
* `services/export_service.py`
* `services/export_validation_service.py`
* `storage/migrations/m013_create_export_presets.py`
* `storage/repositories/export_preset_repository.py`
* `tests/test_export_phase16.py`
* `tests/test_export_ffmpeg_integration.py`
* `ui/controllers/export_controller.py`
* `ui/qml/export/ExportComplete.qml`
* `ui/qml/export/ExportDialog.qml`
* `ui/qml/export/ExportHistory.qml`
* `ui/qml/export/ExportPage.qml`
* `ui/qml/export/ExportPresetCard.qml`
* `ui/qml/export/ExportProgress.qml`
* `ui/qml/export/ExportSettingsPanel.qml`
* `ui/qml/export/ExportSummary.qml`
* `PHASE16_REPORT.md`

Modified files:

* `README.md`
* `app/bootstrap.py`
* `domain/render_settings.py`
* `rendering/renderer.py`
* `services/platform_service.py`
* `services/render_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/__init__.py`
* `storage/repositories/render_output_repository.py`
* `ui/qml/pages/ProjectWorkspacePage.qml`
* prior migration-version regression assertions and Phase 15 workspace assertion updated for schema v13 / Export workspace.

Tests run:

* Full automated suite: **419 passed, 7 skipped**.
* Phase 16 focused backend/export integration: **35 passed**.
* `python -m compileall -q app domain engines media rendering services storage ui workers` passed.
* Static delimiter audit passed for all **9 Phase 16 QML files** (the eight new Export components plus the modified Project Workspace).
* Expected skips are unchanged: two PySide6 live-runtime checks unavailable in this sandbox; opt-in VoxCPM/faster-whisper/translation tests; unavailable real hardware encoder; opt-in 60-second Phase 15 performance render.

TikTok export test:

* Real Phase 15 renderer invoked through `ExportService`; output validated at **1080×1920**, MP4/H.264 with no-audio mode selected for the test fixture.

YouTube export test:

* Real export validated at **1920×1080** using software `libx264` Fast for the test fixture.

Khmer subtitle export test:

* Real 9:16 export burned a Khmer subtitle (`ព័ត៌មានថ្មីថ្ងៃនេះ`) through the existing ASS/libass renderer successfully.
* Existing Phase 15 bilingual English+Khmer real-render regression remains passing in the full suite.

Khmer path test:

* Real export succeeded to a Unicode directory `វីដេអូ ចេញ` with output filename `ព័ត៌មានថ្មី.mp4`.

File-conflict test:

* Keep Both produced `same_2.mp4` on a second export without overwriting the first output.
* Replace and Cancel policy resolution are covered by deterministic filename-service tests.

Custom-preset restart test:

* Saved custom preset settings reload from SQLite with the same resolution/FPS/quality after repository reinitialization.

Recent-exports restart test:

* A completed real export was persisted, a fresh application container reopened the same database, the output remained in render/export history, and Export Again restored its saved settings.

Known issues:

* PySide6 is not installed in this packaging sandbox, so live QML launch/runtime smoke remains skipped; static QML structure/delimiter checks pass.
* Platform presets are application defaults and intentionally are not presented as guaranteed/current platform acceptance rules.
* External user-selected outputs can only be physically deleted after explicit confirmation; the default history delete path refuses them.
* Phase 16 does not upload/publish anywhere and cannot continue exporting after the application exits.
* Exact output-size prediction is impossible with quality-based encoding; the UI labels file size as Estimated.

Architecture decisions:

* Export is a policy/UX layer only; the tested Phase 15 renderer remains the single source of FFmpeg behavior.
* Builtin preset values live in a versioned local JSON registry; project/export history stores the effective settings actually used so future preset updates do not reinterpret old outputs.
* Export-level Fit/Fill/Stretch modifies only the immutable render-plan scene snapshot, never persisted Scene data.
* No-audio export is implemented as one small `RenderSettings.include_audio` extension; scene intermediate audio remains stable while the final MP4 can omit audio cleanly.
* Export Again uses previous settings with **current project content**; Phase 16 does not store expensive full source snapshots for byte-identical rerenders.
* Khmer/Unicode filesystem names remain first-class rather than being transliterated to ASCII.

Recommended next phase:
Phase 17 — Advanced Timeline Editor

Suggested Git commit:
`feat: add polished export workflow and platform presets`

Do not automatically begin Phase 17.

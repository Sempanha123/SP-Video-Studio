# PHASE 27 STATUS

Completed:

* Implemented Phase 27 local autosave, atomic persistence, crash recovery, interrupted-job recovery, recovery UI, and clean-shutdown coordination on top of the Phase 26 runtime.
* Kept normal persistence and recovery as separate mechanisms; no cloud backup, remote sync, alternate project format, or automatic heavy-job restart was added.
* Preserved existing Script/Translation/Subtitle/Scene/Timeline/Batch/Render/TTS/STT/News/Story/Shorts repositories and services instead of replacing them.

Autosave architecture:

* Added a central `AutosaveService` with per-project dirty topics, domain-aware debounce, critical flush, retry, failure state, and registered domain save handlers.
* Existing Script, Translation, and Subtitle autosave timers are bridged into the central coordinator at runtime rather than running conflicting independent save loops.
* User-facing states remain Saved, Saving…, Unsaved changes, and Save failed; successful autosaves do not generate repetitive toasts.

Revision tracking:

* Added persistent `project_revision`, `saved_revision`, last-modified, last-saved, status, failure, and dirty-topic state.
* Every meaningful reported mutation increments the project revision.
* Save completion only marks the exact revision actually saved; an edit arriving during an older save remains dirty.

Debounce/coalescing:

* Text-oriented Script/Translation/Subtitle/SpeechBlock/News/Story changes use approximately 1.5-second debounce.
* Structural Scene/Timeline/Speaker/template/Batch changes record immediately after their authoritative transaction succeeds.
* Repeated dirty notifications coalesce into the newest required save instead of writing synchronously for every keystroke/pointer movement.

Atomic writes:

* Added `storage/atomic_write.py` using same-directory staging, flush/fsync, `os.replace`, best-effort directory fsync, and staging cleanup on failure.
* Recovery marker/snapshot JSON is UTF-8 and preserves Unicode with `ensure_ascii=False`.
* A forced failure before final replace leaves the previous valid file readable.

Database transactions:

* Project recovery restore uses `BEGIN IMMEDIATE`, deferred foreign keys, dependency-aware delete/reinsert ordering, and rollback on failure.
* SQLite now requests WAL + `synchronous=NORMAL` best-effort while retaining safe fallback behavior.
* Added SQLite backup-API support; active WAL databases are never backed up via unsafe raw file copy.
* Fresh-database smoke: schema version 24, journal mode WAL, `quick_check(1)` = ok, SQLite backup file created successfully.

Recovery snapshots:

* Added checksummed `.spvrecovery` snapshots outside user project folders under the application recovery root.
* Snapshot payload contains project-scoped structured SQLite rows, small project JSON, working text/timeline/mapping state, and media IDs/paths/fingerprints.
* Source media, generated TTS audio, and reference-voice recordings are referenced rather than copied into every snapshot.
* Snapshot types support periodic, pre-render, pre-export, pre-Batch, pre-close, crash-recovery, and pre-restore backup use cases.

Snapshot retention:

* Default periodic recovery interval is 180 seconds and runs only while a project is dirty.
* Runtime retention is bounded to 8 recent snapshots per project.
* Low disk safely pauses periodic snapshots without disabling normal autosave.

Startup recovery:

* Added atomic session markers with clean/unclean shutdown detection.
* An unclean startup runs lightweight integrity checks, scans snapshots, and inspects interrupted jobs/temp state.
* Saved projects are never automatically overwritten; recovery requires explicit user action.

Recovery UI:

* Added `RecoveryHost.qml`, `RecoveryDialog.qml`, `RecoveryCard.qml`, `RecoveryComparison.qml`, and `RecoveryStatus.qml` plus `RecoveryController`.
* Supports Recover, Open Saved Version, Review, Discard Recovery, and Later per recoverable project.
* Comparison shows simple category-level change summaries instead of raw database terminology.
* A subtle global save status is displayed without success-toast spam.

Script recovery:

* Script and `script_sections` rows are captured/restored through the project-scoped FK walk.
* Version A → unsaved Version B crash/recovery behavior is covered by Phase 27 tests.
* Script controller save scheduling is bridged to central autosave rather than adding another timer.

Subtitle recovery:

* Subtitle tracks/styles/cues and edited text/timing are captured and transactionally restored.
* Debounced text remains separate from immediate structural timing/cue operations.

Timeline recovery:

* Timeline/project-owned scene/layer/overlay state is captured and restored transactionally.
* Interaction commits are designed to report final changes rather than per-pixel database writes.
* Layer position/scale/chroma values are covered by creative-state recovery fixtures.

Speaker/SpeechBlock recovery:

* Speaker profiles and SpeechBlocks are captured/restored with their project relationships, speaker assignments, text, voice overrides, and metadata.
* Multi-speaker TTS resume reuses valid previously generated block audio and generates only missing blocks after explicit user action.

News/Story/Shorts recovery:

* Project-scoped News claims/brief/mappings, Story structure/beats, Shorts metadata/reframe/caption state, and layered green-screen state are included through existing schema relationships.
* Recovery does not change approved evidence semantics; it restores the captured project-owned state.

Batch recovery:

* Phase 26 Batch stage checkpoints remain authoritative and are unified with unclean-session recovery.
* Mandatory 100-item crash fixture passes: 30 completed remain completed, 1 active item becomes interrupted, 69 remain pending, and Batch becomes paused.
* Completed Batch items are not automatically rerendered.

Render recovery:

* Render jobs found active after an unclean exit are marked interrupted, never falsely completed.
* Partial output is not promoted to completed output.
* Retry uses the existing saved render/project state; mid-FFmpeg byte-level resume is intentionally not implemented per the Phase 27 specification.

TTS/STT recovery:

* TTS preserves completed generated SpeechBlock audio and skips it when explicitly resuming remaining blocks.
* Interrupted STT is marked for a safe full retry while prior completed transcript data remains authoritative.
* Translation and Dub preserve completed segments and mark active work interrupted for explicit resume/retry.
* No heavy job automatically resumes after reboot.

Shutdown handling:

* Added `ShutdownService` with pre-close recovery snapshot, bounded autosave flush, heavy-job shutdown hooks, and clean-session marking only on success.
* Failed bounded save deliberately leaves the session marker unclean so startup recovery can inspect the work.
* Global manual save uses the same central flush path rather than duplicate serialization logic.

New files:

* `domain/autosave_state.py`
* `domain/recovery_errors.py`
* `domain/recovery_session.py`
* `domain/recovery_snapshot.py`
* `app/phase27_runtime.py`
* `services/interrupted_job_recovery_service.py`
* `services/project_integrity_service.py`
* `services/project_snapshot_codec.py`
* `services/recovery_snapshot_service.py`
* `services/shutdown_service.py`
* `services/temp_recovery_service.py`
* `storage/atomic_write.py`
* `storage/recovery_store.py`
* `storage/migrations/m024_create_autosave_recovery.py`
* `storage/repositories/recovery_repository.py`
* `ui/controllers/recovery_controller.py`
* `ui/qml/recovery/RecoveryCard.qml`
* `ui/qml/recovery/RecoveryComparison.qml`
* `ui/qml/recovery/RecoveryDialog.qml`
* `ui/qml/recovery/RecoveryHost.qml`
* `ui/qml/recovery/RecoveryStatus.qml`
* `tests/test_phase27_recovery.py`
* `docs/PHASE27_AUTOSAVE_RECOVERY.md`
* `PHASE27_REPORT.md`

Modified files:

* `app/paths.py`
* `main.py`
* `pyproject.toml`
* `services/autosave_service.py`
* `services/recovery_service.py`
* `services/multispeaker_tts_service.py`
* `storage/database.py`
* `storage/migrations/__init__.py`

Tests run:

* Phase 27 targeted tests: 38/38 passed.
* Combined Phase 22–27 regression: 166/166 passed.
* Phase 21 dubbing regression: 19/19 passed.
* Python `compileall`: passed.
* Phase 27 static/runtime architecture checks: 13/13 passed.
* Fresh SQLite WAL/quick-check/backup smoke: passed (schema 24, WAL, quick_check ok, backup created).
* Full Qt GUI runtime and `qmllint` were not executed because PySide6/qmllint are unavailable in this sandbox.

Atomic-save test:

* Passed. Simulated failure before final atomic replacement and verified the previous valid JSON remained unchanged/readable.

Revision-race test:

* Passed. A newer edit arriving during an older revision save remains dirty; completion of the older save cannot incorrectly mark the newer revision saved.

Unclean-shutdown test:

* Passed. Leaving the session marker causes the next startup recovery scan to identify the previous session as unclean; a clean shutdown removes the marker and produces no false recovery state.

Creative-project recovery test:

* Passed with tiny fixture data covering multilingual Script state, Translations, Subtitles, Scenes, Timeline/project-owned overlays/layers, Speakers/SpeechBlocks, News/Story/Shorts metadata, and green-screen/layer transform state.

Batch crash-recovery test:

* Passed. 100 mocked items with 30 completed + 1 active + 69 pending recover to 30 completed + 1 interrupted + 69 pending; Batch is paused and completed work is preserved.

Render-interruption test:

* Passed. An active RenderJob becomes interrupted after simulated restart and is never marked completed solely because a partial output exists.

Unicode recovery test:

* Passed exact UTF-8 round-trip/recovery for English, ខ្មែរ, ไทย, and Tiếng Việt.

Large-project autosave performance:

* Passed. Recovery snapshot fixture with 100 scenes and 1,000 subtitle cues completed below the 3-second acceptance threshold.

Clean-exit test:

* Passed. Dirty state is flushed during normal shutdown, the recovery session is marked clean, and restart does not produce a false unclean-session prompt.

Known issues:

* PySide6 and `qmllint` are unavailable in this sandbox, so full interactive QML end-to-end/runtime lint was not executed; static QML/runtime checks passed 13/13.
* A real local `git status` could not be inspected because this sandbox has a reconstructed test workspace rather than a Git clone; the authoritative GitHub head was verified as Phase 26 commit `9eca2d155025d867eebbfb5af8823e7eb39cac71` before implementation.
* Mid-process FFmpeg resume is intentionally not supported; interrupted renders retry from saved state as specified.
* Optional Phase 27 extras—Restore as New Project, full text/visual diff, dedicated Recovery Center page, manual recovery points, and user-facing recovery interval toggles—were not added.

Architecture decisions:

* Recovery remains separate from normal autosave and never becomes the primary project database.
* Existing repository/service serializers stay authoritative; Phase 27 coordinates them instead of rewriting every repository.
* Project snapshots use actual SQLite FK relationships and explicit exclusions for global Assets/Templates/Batch/recovery/model tables.
* Recovery is project-scoped and local-only; large media is referenced, not copied.
* Heavy jobs are detected/marked interrupted but never auto-resumed after reboot.
* WAL improves concurrency where supported, but correctness relies on atomic writes and explicit transactions rather than WAL alone.

Recommended next phase:
Phase 28 — Cache Management

Suggested Git commit:
feat: add resilient autosave and crash recovery system

Do not automatically begin Phase 28.

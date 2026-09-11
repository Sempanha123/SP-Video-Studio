# Phase 27 — Autosave + Recovery

Phase 27 adds local resilience to SP Video Studio without adding cloud backup, remote sync, a second project format, or a second job system. Normal persistence remains authoritative; recovery is a separate safety layer for recent unsaved/interrupted work.

## Autosave architecture

`AutosaveService` is the central coordinator for project dirty state. Controllers and structural services report meaningful mutations by topic instead of writing on every UI event. Text-oriented changes use short debounce windows, structural mutations are recorded immediately after their existing transaction succeeds, and critical operations explicitly flush outstanding work before proceeding.

The service exposes the user-facing states `Saved`, `Saving…`, `Unsaved changes`, and `Save failed`. Successful background saves are intentionally quiet. A failed critical flush raises `AutosaveFailed`, allowing render/export/Batch or close workflows to stop rather than silently continue with stale data.

Existing Script, Translation, and Subtitle controller timers are bridged into the central coordinator at Phase 27 runtime startup. Their repository-specific save methods remain the serialization authority; Phase 27 does not create a second serializer or continuously write the database.

## Dirty-state and revision model

Each project has persistent autosave state with:

- `project_revision`
- `saved_revision`
- `last_modified_at`
- `last_saved_at`
- current autosave status and dirty topics

Every meaningful mutation increments `project_revision`. A successful save only advances `saved_revision` to the revision that was actually written. If revision 11 arrives while revision 10 is saving, completion of revision 10 cannot claim that revision 11 is saved. The newer change remains dirty and is scheduled again.

Multiple dirty notifications are coalesced so revisions 20/21/22 may result in one write of the newest state rather than three redundant writes.

## Debounce policy

Defaults are domain-aware rather than global keystroke writes:

- Script / Translation / Subtitle text and SpeechBlock text: about 1.5 seconds after editing settles.
- Inspector, reframe, and interaction-end state: short debounce.
- Scene/track/speaker/template/Batch structural changes: immediately recorded after the authoritative transaction.
- Timeline interactions are expected to report the committed drag result, not every pointer pixel.

The coordinator can be ticked from the UI event loop without mutating Qt objects from a background worker.

## Critical flush

Pending autosaves are flushed before derived or destructive work that must see current state. Phase 27 wraps existing render/export and Phase 26 Batch start paths so a failed flush cancels the operation. Shutdown also performs a bounded flush. Project switch/close continues to use the existing controller/service flush paths, now tied into central revision state.

Global `Ctrl+S` is exposed through the recovery controller as an immediate central flush; it reuses the same registered save handlers.

## Atomic writes

`storage/atomic_write.py` uses same-directory staging files, flush + `fsync`, and `os.replace`. On systems where directory syncing is available, the parent directory is synced best-effort after replacement. Failure before final replacement removes the staging file and leaves the previous valid destination untouched.

Recovery session markers, snapshot envelopes, and Phase 27 small JSON state use this atomic helper. Unicode is written as UTF-8 with `ensure_ascii=False`.

## SQLite transactions, WAL, and backups

Related recovery restores use explicit SQLite transactions with deferred foreign-key checking so parent/child project state cannot be committed halfway. The application database keeps foreign keys and busy timeout enabled.

Phase 27 requests SQLite WAL mode and `synchronous=NORMAL` as a best-effort startup configuration. If WAL is unavailable, the database remains usable with SQLite's returned journal mode; recovery correctness does not depend on WAL.

`SQLiteDatabase.backup_to()` uses SQLite's backup API instead of copying a live database/WAL pair as raw files. Startup after an unclean session can run lightweight `quick_check(1)` and foreign-key checks rather than a full expensive integrity scan every launch.

## Recovery sessions

A local session marker is created when the Phase 27 runtime starts. A clean shutdown archives/clears it only after the bounded autosave/shutdown sequence succeeds. If a marker remains on the next launch, the previous session is treated as unclean and recovery scanning is enabled.

Session metadata contains only local application/session information. No recovery data is uploaded.

## Recovery snapshots

Snapshots are stored outside user project folders under the application recovery root. The default periodic interval is 180 seconds (3 minutes) and periodic snapshots are created only while a project is dirty.

Snapshot types include periodic, pre-render, pre-export, pre-Batch, pre-close, crash-recovery, and pre-restore backup. A snapshot contains structured project-owned rows, small project JSON, working text/timeline/mapping state, and media references/fingerprints. Source video/audio, generated TTS audio, and reference-voice recordings are not duplicated into each snapshot.

Each `.spvrecovery` envelope includes a SHA-256 checksum. Creation is staged and atomically replaced only after serialization succeeds. Checksum mismatch blocks restore and marks the copy unusable rather than attempting a partial restore.

## Snapshot retention and disk protection

The runtime retains a small rolling history (8 recent snapshots per project by default). Old safe snapshots are pruned as new ones are created; retention is bounded rather than infinite.

Before snapshot creation, the recovery store checks free space with a reserved-space threshold. Low disk pauses periodic recovery protection, but normal project autosave remains active. The warning state can be surfaced without repeatedly spamming successful-save toasts.

## Project-state capture and restore

`ProjectSnapshotCodec` captures project-scoped SQLite rows by following real foreign-key relationships. This preserves Script sections, Translations, Subtitle tracks/cues/styles, Scenes and layered-video rows, Timeline rows, Speakers/SpeechBlocks, News/Story/Shorts data, and related project-owned metadata without rewriting each repository.

Global Assets, Templates, Batch tables, recovery metadata, model state, and unrelated application-wide tables are deliberately excluded from project snapshots.

Restore behavior is conservative:

1. verify snapshot checksum/schema/app compatibility;
2. create a pre-restore backup of the currently saved project state;
3. restore captured rows in one transaction with dependency-aware ordering;
4. atomically restore small project JSON;
5. if restore fails, roll back the SQLite transaction and attempt to restore the pre-restore backup.

Phase 27 never silently overwrites a saved project during startup. The user chooses Recover, Open Saved Version, Review, or Discard Recovery.

## Media references and missing media

Media records in recovery contain IDs, existing file paths, sizes, and lightweight fingerprints. The media bytes are not copied. During review/recovery, missing or changed referenced files generate warnings. Existing media/Asset Library relink workflows remain the mechanism for reconnecting unavailable files.

## Startup recovery and UI

`RecoveryController` exposes recoverable snapshots, comparison summaries, interrupted jobs, and global save state. `RecoveryHost.qml` mounts a compact status indicator and recovery dialog over the existing application shell without creating another navigation system.

The dialog supports independent handling of multiple recoverable projects:

- Recover
- Open Saved Version
- Review
- Discard Recovery
- Later

Review uses category-level summaries (Script, Scenes, Timeline, Subtitles, Translation, Speakers, News, Story, Shorts) instead of exposing raw database details. A recovery copy remains available when the user chooses the saved version; discard removes only the selected recovery snapshot.

## Batch recovery

Phase 26 Batch checkpoints remain authoritative. On unclean startup, `BatchRecoveryService` converts an active item to interrupted/resumable state and pauses the Batch. Completed items stay completed and pending items remain pending. Phase 27 does not automatically resume production work after reboot.

A Batch start performs a critical autosave flush and may create pre-Batch recovery snapshots for dirty projects before scheduling work.

## Render/export interruption

Render jobs found in queued/preparing/rendering/validating states after an unclean shutdown are marked `interrupted`, never `completed`. Partial output is metadata for review/cleanup only; it is not presented as a valid finished video. Mid-FFmpeg continuation is intentionally not implemented—retry starts from the existing saved render snapshot/state.

Export recovery follows render behavior because export delegates to the render pipeline.

## TTS, STT, Translation, and Dub interruption

Heavy AI/media jobs are not automatically restarted after reboot.

- Multi-speaker TTS reuses SpeechBlocks whose generated-audio record and project-managed audio file are still valid, then generates only missing blocks when the user explicitly resumes.
- Interrupted STT is marked for a safe restart; the previously completed transcript is not falsely overwritten by partial work.
- Translation keeps completed segment rows and marks an interrupted document for explicit resume/retry.
- Dub processing preserves completed segments and marks active segments interrupted so only missing/failed work needs regeneration.

## Temporary-file recovery

Temporary job directories may contain a small recovery manifest. Startup classification distinguishes recoverable, stale, safe-to-delete, and unknown directories. Cleanup only removes paths classified safe-to-delete after age/job checks and path-containment validation. Recoverable temp state is not deleted before the user/job recovery decision.

## Project deletion

Intentional project deletion removes Phase 27 recovery snapshots by default after the authoritative project deletion succeeds. This follows the recommended permanent-delete behavior and prevents hidden recovery copies from accumulating indefinitely. Recovery discard never deletes the actual project.

## Shutdown flow

`ShutdownService` performs a bounded close sequence:

1. create pre-close snapshots for dirty projects where possible;
2. flush central autosaves;
3. invoke registered heavy-job shutdown hooks;
4. mark the recovery session clean only on successful persistence.

If the bounded save fails, the session marker is intentionally left unclean so startup recovery can inspect recent work instead of falsely claiming a clean exit.

## Privacy and storage

Recovery is local-only user data under the normal application storage root. Phase 27 adds no cloud provider, telemetry upload, remote sync, or collaboration. Recovery logs record actions/status, not full project text. Snapshots avoid unnecessary copies of large or sensitive media.

## Performance considerations

The recovery snapshot path serializes immutable database rows and small metadata instead of media content. Autosave coalescing prevents per-keystroke synchronous writes. A Phase 27 test fixture with 100 scenes and 1,000 subtitle cues must snapshot in under 3 seconds in the test environment.

## Optional items deliberately not added

The spec marks several features optional rather than acceptance requirements; Phase 27 keeps the first implementation focused. It does not add Restore-as-New, a full visual/text diff system, a dedicated Recovery Center page, manual recovery-point management, cloud backup, project Save As, or infinite history.

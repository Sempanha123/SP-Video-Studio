# Phase 29 — Cache Management + Storage Cleanup

## Scope

Phase 29 adds one application-wide cache/storage safety layer. It does not create a second project, media, render, model, Asset Library, Batch, or recovery ownership system. Cache is treated as disposable only when the storage classification and containment checks say it is safe.

## Storage classification

`domain/storage_category.py` is the source of truth for categories and safety classes:

- `SAFE_TO_CLEAR`: preview cache, thumbnails, render temp, transcription temp, translation cache, Asset thumbnails, Template cache, Batch intermediate data, old logs.
- `REGENERATABLE`: unreferenced generated audio.
- `PROTECTED`: recovery snapshots and AI models.
- `USER_DATA`: project data, project media, Asset Library source files, final exports.
- `EXTERNAL`: referenced files outside managed MMO Video Studio storage.

External references are shown separately and never added to owned-storage totals.

## Cache root and layout

`CacheService` centralizes the managed cache root and creates only application-owned subdirectories:

```text
cache/
├── preview/
├── thumbnails/
├── render/
├── audio/
├── transcription/
├── translation/
├── templates/
├── assets/
└── batch/
```

The cache location preference lives in `settings/phase29_storage.json`. `AppPaths.discover()` reads it safely on restart and falls back to the default application cache if the preference is malformed or unsafe.

## Cache manifests and keys

Cache directories may contain `cache_manifest.json` with owner/project, timestamps, source fingerprint, cache version, and safety metadata. Manifests help classify entries but never override path-containment checks.

Preview and thumbnail keys use stable SHA-256 hashes over relevant fingerprints and cache version. Missing cache directories are recreated automatically. Missing thumbnails/previews can be regenerated on demand through the central cache service.

## Safe cleanup contract

`CleanupService` follows the mandatory order:

1. classify the entry,
2. verify canonical containment inside an approved managed root,
3. check active ownership,
4. check protection/references,
5. delete only when certain,
6. record freed/skipped/failed results.

Clear All Cache never includes projects, source media, Asset source files, recovery snapshots, AI models, final exports, or external references. Windows locked files are skipped individually instead of failing the whole cleanup.

Generated narration is handled specially: only generated audio under managed cache locations is considered, and a database reference check protects audio still used by SpeechBlock, scenes, dubbing, timeline/render-plan references, or active records. Database uncertainty fails closed and keeps the file.

## Project cache cleanup

Per-project cleanup targets Phase 29 cache ownership plus legacy project-local `cache/`, `thumbnails/`, render `.temp`, and explicit generated-audio cache folders. It never targets project media, project metadata/script/database, subtitles, or final render outputs.

Project deletion may clean project-owned cache after the existing deletion succeeds. Recovery remains owned by Phase 27 retention behavior.

## Asset and Template safety

Global Asset source files remain user data. Phase 25 Asset thumbnails are separately classified as cache and may be cleared. Template packages/resources remain data/resources; only generated previews and staging cache are disposable.

## Cache migration

`CacheMigrationService` rejects unsafe roots and active heavy jobs. Move Existing Cache uses copy-first staging and only switches the persisted root after staging succeeds. Failure leaves the previous root and settings valid. Start Fresh can switch to an empty location without deleting the old cache unless the user explicitly chooses removal.

Filesystem roots, the application source tree, the broad application-data root, Windows system folders, and Program Files are rejected. Cleanup resolves canonical paths and does not follow symlink/junction escapes.

## Automatic cleanup and LRU

Modes are Off, Conservative, and Balanced. Startup work is lightweight and asynchronous:

- Conservative: stale safe temp only.
- Balanced: stale safe temp plus cache-size enforcement.

Category-specific stale ages are used instead of one global age. LRU cleanup only considers disposable/regeneratable, inactive, contained entries; protected/user/external data is excluded.

## Disk monitoring

`DiskMonitorService` is the central Normal / Low / Critical evaluator. Defaults use both absolute and percentage thresholds:

- Low: below 10 GiB free or below 10%.
- Critical: below 3 GiB free or below 3%.

The storage page monitors cache, models, recovery, exports, and Asset Library volumes. Critical space blocks heavy work where Phase 29 can safely intercept it. Phase 26 Batch scheduling is routed through the same central monitor, and existing render/export entry points are guarded without replacing their engines.

## Storage UI

Settings → Storage follows the Phase 28 Soft Creator Studio design. It shows managed storage totals, calm category cards with safety labels, cache details, project usage sorted largest-first, disk warnings, Clear Cache preview/confirmation, per-project cache cleanup, cache location migration, maximum cache size, automatic cleanup, stale-temp policy, and old-log cleanup.

Recovery and Models are shown as protected data rather than cache-cleanup targets. External references are explicitly not counted as owned usage.

## Performance and resilience

Storage summaries use a short TTL and run through the existing worker pool when available. Cache scans stay inside known app-owned roots and do not walk the entire user disk. List UI uses reusable delegates. The LRU planner is tested with 100,000 metadata entries without creating huge real files.

If a user manually removes the cache directory, `ensure_structure()` recreates it safely and the app continues. Cache index/manifests are advisory; filesystem reality wins.

## Privacy and logging

All cache data remains local. No telemetry or upload is added. Cleanup/migration/low-disk events log operational metadata, not user content.

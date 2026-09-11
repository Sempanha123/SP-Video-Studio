PHASE 29 STATUS

Completed:

* Implemented Phase 29 only: safe application-wide cache management, storage visibility, disk protection, stale-temp cleanup, cache limits/LRU, cache migration, and regeneratable-cache recovery.

Storage architecture:

* Added one central `CacheService`, `StorageUsageService`, `CleanupService`, `CacheMigrationService`, `DiskMonitorService`, and `StaleFileService`, layered on the Phase 27 runtime while preserving Phase 28 UI and existing ownership systems.

Storage classification:

* Added central categories plus `SAFE_TO_CLEAR`, `REGENERATABLE`, `PROTECTED`, `USER_DATA`, and `EXTERNAL` safety classes.

Cache categories:

* Covers preview, thumbnails, render temp, unreferenced generated audio, transcription temp, translation cache, Asset thumbnails, Template cache/staging, Batch intermediate data, and old logs.

Storage overview:

* Settings > Storage reports managed app usage by category with readable sizes and excludes external referenced bytes from owned totals.

Project storage:

* Reports project data, media, generated audio, cache/thumbnails, and renders/exports; supports safe per-project cache cleanup without deleting project media, scripts, metadata/database, subtitles, or final outputs.

Preview cache:

* Classified safe-to-clear, keyed by stable fingerprints/version, invalidatable by source fingerprint, and regeneratable when missing.

Thumbnail cache:

* Project/media and Asset Library thumbnails are regeneratable; Asset source files remain protected user data.

Render temp:

* Safe only when not owned by an active render/heavy job; cleanup skips active or uncertain resources.

TTS/audio cache:

* Generated audio is regeneratable only when unreferenced; DB reference checks protect active/current narration and dubbing audio.

Transcription cache:

* Temporary extracted/transcription working files are cache; transcript data/models remain outside Clear Cache.

Template/asset cache:

* Generated Template previews/staging and Asset thumbnails are cache; Template packages/resources and Asset sources are not.

Batch cache:

* Batch intermediate cache is disposable; persistent Batch projects/outputs are not. Phase 26 low-disk scheduling is routed through the central disk monitor.

Recovery protection:

* Phase 27 recovery data is `PROTECTED`, shown in storage totals, and excluded from Clear All Cache and LRU cleanup.

Model protection:

* AI models are `PROTECTED`; no Clear Models action is added and external/shared package caches are untouched.

Export protection:

* Final exports are `USER_DATA` and never automatically deleted; stale render/cache intermediates are separate.

Cache location:

* Added persisted cache-root selection with safe-root validation and restart restoration.

Cache migration:

* Move Existing Cache uses copy-first staging with rollback safety; Start Fresh switches only to an empty safe location; active heavy jobs block migration.

Automatic cleanup:

* Added Off, Conservative, and Balanced policies. Startup performs lightweight asynchronous stale-temp cleanup only; Balanced may also enforce the cache limit.

Cache size limit:

* Default is 25 GiB with 10/25/50/100 GiB, Unlimited, and controller support for custom numeric values.

LRU cleanup:

* Approximate least-recently-used planning removes oldest safe inactive cache first and excludes protected, user, external, unsafe, and active entries.

Disk monitoring:

* Added Normal/Low/Critical status using absolute + percentage free-space thresholds across relevant managed volumes.

Low-disk integration:

* Phase 26 Batch uses the central monitor for new heavy stages; existing render/export service entry points are guarded when available. Critical disk raises before expensive work.

Path safety:

* Cleanup requires canonical containment, rejects traversal, filesystem roots, broad app-data root, source tree, Windows/Program Files roots, and symlink escapes; it never cleans general OS/Python/Hugging Face caches.

New files:

* `app/phase29_runtime.py`
* `domain/cache_entry.py`
* `domain/cache_errors.py`
* `domain/cleanup_policy.py`
* `domain/storage_category.py`
* `domain/storage_usage.py`
* `services/cache_service.py`
* `services/storage_usage_service.py`
* `services/cleanup_service.py`
* `services/cache_migration_service.py`
* `services/disk_monitor_service.py`
* `services/stale_file_service.py`
* `ui/controllers/storage_controller.py`
* `ui/qml/storage/StoragePage.qml`
* `ui/qml/storage/StorageOverview.qml`
* `ui/qml/storage/StorageCategoryCard.qml`
* `ui/qml/storage/ProjectStorageList.qml`
* `ui/qml/storage/CleanupDialog.qml`
* `ui/qml/storage/CacheLocationDialog.qml`
* `tests/test_phase29_storage.py`
* `docs/PHASE29_CACHE_STORAGE_MANAGEMENT.md`
* `PHASE29_REPORT.md`

Modified files:

* `app/paths.py`
* `main.py`
* `pyproject.toml`
* `ui/qml/pages/SettingsPage.qml`

Tests run:

* Phase 29 focused suite: 37/37 passed.
* Available Phase 22–29 cumulative suite: 236/236 passed.
* Phase 21 dubbing regression: 19/19 passed.
* Python compilation passed for all Phase 29 Python files.
* PySide6/qmllint are unavailable in this sandbox, so live QML launch/lint was not run here.

Clear-all-cache safety test:

* PASS — preview, thumbnail, and render temp are removed; models, recovery, Asset sources, project media, and final exports remain.

Active-render protection test:

* PASS — active render temp is skipped and reported.

Generated-audio protection test:

* PASS — referenced/current generated audio remains; unreferenced managed generated cache may be removed.

Recovery protection test:

* PASS — recovery category is excluded from Clear Cache and protected by Phase 27 ownership.

Model protection test:

* PASS — model category is excluded from Clear Cache/LRU.

Export protection test:

* PASS — final exports remain user data and are excluded.

Path-escape test:

* PASS — malicious `../../` cleanup paths are rejected without touching outside files.

Symlink/junction safety test:

* PASS where symlinks are supported — outside target remains untouched; symlink entry is rejected as unsafe. Windows junction behavior follows the same canonical-containment rule but was not executable on this Linux sandbox.

Cache-migration test:

* PASS — staged move updates settings/root after success; simulated copy failure keeps old cache and preferences valid.

Cache-limit/LRU test:

* PASS — oldest safe entries are selected to reach limit; protected entries are never selected.

Disk-monitor test:

* PASS — mocked Normal, Low, and Critical states behave correctly and Critical blocks heavy work.

Batch low-disk test:

* PASS structural integration — Phase 29 replaces the Phase 26 scheduler disk predicate with central `DiskMonitorService.can_start_heavy`; existing Phase 26 low-disk behavior remains regression-tested.

Unicode-path test:

* PASS — Khmer, Thai, and Vietnamese managed cache paths clean safely.

Large-cache performance test:

* PASS — 100,000 metadata entries are planned by LRU in the test threshold without allocating 100 GiB of real files.

Known issues:

* PySide6 and qmllint are not installed in this execution sandbox, so real desktop Storage-page launch/visual QA could not be executed here.
* Render/export disk guarding is attached to existing service entry points when those services are present in the full runtime; no second render engine was introduced.
* Filesystem deletion is intentionally non-transactional; uncertain/locked files are skipped instead of risking unrelated data.

Architecture decisions:

* Filesystem manifests/scanning are preferred over a new cache-entry database table because cache is disposable and path ownership is clearer at the managed-root boundary.
* Existing Phase 25 Asset, Phase 26 Batch, Phase 27 Recovery, model, project, and render ownership remain authoritative.
* Cleanup safety is prioritized over maximizing bytes freed; database/activity-check failures fail closed.
* External references are visible but never counted as MMO Video Studio-owned storage.

Recommended next phase:
Phase 30 — Audio Mixer

Suggested Git commit:
feat: add safe cache and storage management system

Do not automatically begin Phase 30.

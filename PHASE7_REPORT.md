# PHASE 7 STATUS

## Completed:

- Production local AI Model Manager foundation
- Central model registry with model families/variants
- Persistent model installation metadata in SQLite schema version 4
- Background install / verify / repair / remove operations
- One active model download at a time
- Download progress, cancel, retry/backoff, partial-file resume support
- Interrupted-download recovery
- Manifest-based integrity verification
- Safe atomic installation and staged repair
- Safe managed-directory removal guards
- Installed/invalid/incomplete filesystem discovery
- Hardware compatibility guidance
- System Readiness integration
- Functional Models page with filters, search, details, progress and status-specific actions
- Measured model storage reporting

## Model registry:

- Stable internal IDs separate from display names
- Static definitions separated from runtime installation state
- Centralized source identifiers, licenses, approximate sizes, language metadata, hardware guidance, dependencies, required files and install paths
- Concrete Hugging Face source revisions are used during a download snapshot
- Source metadata verified 2026-09-11

## Supported model families:

- VoxCPM2
  - ID: `voxcpm2`
  - Source: `openbmb/VoxCPM2`
  - License: Apache-2.0
  - Public repository size: approximately 4.96 GB
  - Purpose: Text-to-Speech / Voice
  - English and Khmer are included in its multilingual language list
- faster-whisper
  - `whisper-small` → `Systran/faster-whisper-small` (~486 MB)
  - `whisper-medium` → `Systran/faster-whisper-medium` (~1.53 GB)
  - `whisper-large-v3` → `Systran/faster-whisper-large-v3` (~3.09 GB)
  - License: MIT
  - Purpose: Speech-to-Text

## Model installation:

- Managed model root from Phase 3 `AppPaths.models`
- Final paths are registry-defined below the managed root
- Downloads stage under `models/.downloads/<model-id>/`
- Source file list is fetched dynamically from the public Hugging Face model API
- Documentation-only repository files are skipped
- Completion is committed only after manifest creation and verification
- Existing final installation is staged aside during repair before the verified replacement is committed

## Download manager:

- Uses existing WorkerPool through ModelController
- HTTP Range resume where supported by the source
- `.part` files remain resumable after cancellation/interruption
- Three attempts with bounded exponential backoff for recoverable source failures
- Rolling download-speed display
- Byte progress and current-file display
- Cancellation never marks a model Installed
- Restart refresh converts interrupted downloads to Paused/Incomplete state

## Verification:

- `model_manifest.json` schema version 1
- Checks model identity, manifest version and safe relative paths
- Checks required files and non-empty files
- Checks expected sizes
- Checks SHA-256 when the official source metadata provides it
- Symlink/path escape protection through resolved-path containment guards
- Missing/invalid manifests become Repair Required

## Repair:

- Repair performs a safe staged reinstallation
- Valid final installation is replaced only after the repaired staging directory verifies
- Partial source-specific repair is intentionally deferred until it can be implemented without weakening integrity guarantees

## Safe removal:

- Model ID must exist in registry
- Target must equal its registry-managed install path
- Target must resolve below Models root
- Models root and drive root are never deletion targets
- Loaded/in-use state is already represented and blocks removal
- Projects, scripts, media and generated outputs are not touched

## Hardware compatibility:

- Uses Phase 3 SystemReadiness structure
- RAM guidance
- CUDA availability
- VRAM guidance where available
- CPU support flag
- Compatible / Limited / Not Recommended / Unknown states
- Whisper recommendation heuristic selects Small / Medium / Large V3 based on detected hardware
- Disk capacity is checked separately before installation with safety margin

## System Readiness integration:

- Phase 3 model-folder placeholder detection is replaced by ModelService family state
- VoxCPM2 and faster-whisper report Installed / Repair Required / Not Installed
- ModelController state changes trigger readiness recheck
- Home readiness reflects Repair Required
- Settings → Storage shows measured model storage

## New files:

- `domain/ai_model.py`
- `domain/model_installation.py`
- `engines/model_registry.py`
- `engines/model_sources.py`
- `services/model_compatibility_service.py`
- `services/model_download_service.py`
- `services/model_verification_service.py`
- `storage/migrations/m004_create_model_installations.py`
- `storage/repositories/model_repository.py`
- `ui/controllers/model_controller.py`
- `ui/models/model_list_model.py`
- `ui/qml/components/CompatibilityBadge.qml`
- `ui/qml/components/ModelCard.qml`
- `ui/qml/components/ModelDownloadProgress.qml`
- `ui/qml/components/ModelStatusBadge.qml`
- `tests/test_model_phase7.py`
- `tests/test_model_qml_structure.py`
- `PHASE7_REPORT.md`

## Modified files:

- `app/bootstrap.py`
- `services/model_service.py`
- `services/system_readiness_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/qml/Main.qml`
- `ui/qml/components/StatusBadge.qml`
- `ui/qml/pages/HomePage.qml`
- `ui/qml/pages/ModelsPage.qml`
- `ui/qml/pages/SettingsPage.qml`
- `tests/test_database.py`
- `tests/test_media_phase4.py`
- `tests/test_script_phase6.py`
- `README.md`

## Tests run:

- `python -m compileall -q app domain engines services storage workers ui`
- `pytest -q`
- 145 passed
- 2 skipped Qt-runtime checks because PySide6 is unavailable in this packaging sandbox
- Phase 0–6 regression coverage remains green after schema expectation update to version 4

## Download tests:

- Tiny mocked model source normal download
- Retry after recoverable failure
- Cancellation
- Partial/interrupted recovery
- Successful atomic install
- Failed verification does not create a false final installation
- Manifest/hash/size validation
- Unsafe source path rejection
- Tests do not download multi-GB models

## Manual checks:

- Official model source IDs/licenses/layout guidance checked against current public repositories
- Functional Models QML replaced Phase 1 placeholder actions
- Models page filters/search/status actions statically checked
- Storage and Home readiness wiring checked
- Live QML execution remains unavailable in this sandbox because PySide6 is not installed

## Restart persistence test:

- SQLite installation metadata is restart-safe
- Refresh reconciles persisted metadata with filesystem/manifest state
- Interrupted staging directories become resumable Paused state
- Valid installation can be rediscovered when its DB row is missing

## Real-model verification:

- Current official source metadata was verified for `openbmb/VoxCPM2` and Systran faster-whisper Small / Medium / Large V3
- Production download URLs use the current source API and pin the returned repository revision per download session
- Full multi-GB real-model downloads were not executed in this sandbox, so Phase 7 does not claim an end-to-end bandwidth/storage test of those complete weights

## Known issues:

- Live PySide6/QML smoke remains skipped in this sandbox
- Full real-model downloads are intentionally not part of automated CI
- HTTP resume depends on the source server honoring Range requests; otherwise the individual file restarts cleanly
- Repair currently reinstalls the model rather than downloading only individual damaged files
- Model source authentication is not implemented because the initial supported repositories are public
- Local-folder model adoption is deferred; unmanaged folders are not trusted automatically

## Architecture decisions:

- No AI model is loaded or executed in Phase 7
- Public Hugging Face model files are downloaded individually instead of extracting untrusted archives
- Static model definitions, installation state, source transport, verification and UI controller are separate layers
- Filesystem and manifest are part of installation truth; SQLite metadata alone cannot make a model Installed
- Progress stays in memory while meaningful status checkpoints are persisted
- Managed Models root remains stable in Phase 7; no automatic model moving is introduced

## Recommended next phase:
Phase 8 — VoxCPM2 TTS Engine

## Suggested Git commit:
`feat: add AI model manager and model installation system`

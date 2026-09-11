# PHASE 6 STATUS

## Completed:

- Persistent manual script editor foundation
- Automatic primary script creation per project
- Hook / Body / Outro defaults
- Add, rename, duplicate, reorder, enable/disable, and delete sections
- Lightweight future scene-source marker metadata
- Plain-text long-form editor with native text undo/redo
- Debounced autosave and manual Ctrl+S save
- Save-state / dirty-state handling
- English and Khmer language support
- Narration duration estimates with Slow / Normal / Fast pace
- UTF-8/BOM TXT import and UTF-8 TXT export
- Combined enabled-section text and future TTS section boundaries
- Project duplication/deletion integration
- Existing Phase 5 database upgrade to schema version 3

## Script architecture:

- `Script` domain model with stable UUID, project ownership, language, status, pace, version, notes, metadata, timestamps
- `ScriptSection` domain model with stable UUID, order, type, title, content, notes, enabled state, metadata, timestamps
- `ScriptRepository` owns all SQL
- `ScriptService` coordinates script lifecycle and ownership safety
- `ScriptAnalysisService` owns language-aware metrics and duration estimates
- `ScriptController` is the QML-facing autosave/editing layer
- `ScriptSectionListModel` exposes incremental section roles to QML

## Section system:

- Default section types: hook, body, outro
- User-created section types: body, custom
- Visible section titles remain independent from internal type
- Sequential zero-based ordering is normalized after structural changes
- Duplicates receive new section IDs and are inserted immediately after the source
- Non-empty deletion requires UI confirmation
- Disabled sections retain content but are excluded from narration totals and combined TTS text
- `scene_source` metadata can mark/unmark sections for future scene generation without implementing scenes

## Autosave:

- Content/statistics update without database writes on every keystroke
- Stats debounce: approximately 400 ms
- Autosave debounce: approximately 1.5 seconds
- Saves on section switch and workspace exit through controller flush
- Ctrl+S saves immediately
- Application close flushes the script controller
- Project-switch guard refuses a switch when current script changes cannot be saved
- Failed save keeps dirty in-memory content and reports a user-friendly error

## Analysis/statistics:

- English token-oriented word count
- Khmer non-whitespace character metric
- Character count available for all languages
- Slow / Normal / Fast pacing profiles
- Estimated narration duration only; no claim of exact synthesized timing
- Enabled sections only contribute to project narration totals
- Future TTS preparation returns combined text plus section character boundaries

## English support:

- Word-count metric
- Pace-based WPM duration estimate
- Unicode punctuation preserved
- Mixed Unicode content stored without rewriting

## Khmer support:

- Native Unicode database persistence
- Khmer-safe editing/storage/import/export architecture
- Character metric instead of misleading whitespace-only exact word count
- Character-rate duration heuristic
- Restart persistence verified

## Import/export:

- Import `.txt` using UTF-8 with BOM support
- Add imported text as a section
- Replace current script with one Imported Script section after explicit replace choice
- Export enabled section titles/content to UTF-8 TXT
- Khmer export/import covered by automated tests
- Copy Full Script uses enabled sections in order

## Project duplication compatibility:

- Duplicate project gets a new script ID
- Every duplicated section gets a new section ID
- Order, language, pace, text, notes, enabled flags, and metadata are preserved
- Original and duplicate do not share writable script records

## Project deletion compatibility:

- Script rows and section rows are cleaned by the existing project database lifecycle
- Deleting one project does not alter another project's script
- Remove-from-library behavior remains consistent with project-owned database records

## New files:

- `domain/script.py`
- `domain/script_section.py`
- `storage/migrations/m003_create_scripts.py`
- `storage/repositories/script_repository.py`
- `services/script_service.py`
- `services/script_analysis_service.py`
- `ui/controllers/script_controller.py`
- `ui/models/script_section_model.py`
- `ui/qml/editor/ScriptEditor.qml`
- `ui/qml/editor/ScriptToolbar.qml`
- `ui/qml/editor/ScriptStatsBar.qml`
- `tests/test_script_phase6.py`
- `tests/test_script_qml_structure.py`
- `PHASE6_REPORT.md`

## Modified files:

- `app/bootstrap.py`
- `services/autosave_service.py`
- `services/project_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/controllers/project_controller.py`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- `tests/test_database.py`
- `tests/test_media_phase4.py`
- `README.md`

## Tests run:

- `python -m compileall -q app domain services storage ui`
- `pytest -q`
- 125 passed
- 2 skipped because PySide6 is unavailable in this packaging sandbox
- Existing Phase 0–5 regression tests remain green
- Fresh schema and Phase-5-to-Phase-6 migration paths tested

## Manual checks:

- Script default creation flow exercised through service integration tests
- Add/rename/duplicate/reorder/delete/enable operations verified
- Combined text and TTS boundaries verified
- English/Khmer language behavior verified
- TXT add/replace/export behavior verified
- Project duplicate/delete behavior verified
- New QML delimiter/static structure checks passed
- Live Qt window playback/editor smoke remains unavailable in this sandbox because PySide6 is not installed

## Large-script test:

- Automated analysis test uses an 18,000-character script and completes without special buffering or whole-project rewrites
- Editor design debounces statistics/autosave rather than recalculating/persisting every keystroke

## Restart persistence test:

- Passed for section names/order/content, language, and enabled flags using a reopened SQLite database
- Khmer text remains intact after reload

## Known issues:

- Live QML runtime smoke remains skipped in this sandbox because PySide6 is unavailable
- Structural add/delete/reorder operations are not part of the TextArea native undo stack; non-empty deletion is confirmed instead
- Exact narration duration will only be known after future TTS generation
- Khmer segmentation is intentionally not presented as an exact word count in Phase 6

## Architecture decisions:

- Scripts remain generic and workflow-agnostic
- Sections are persisted separately instead of one giant text blob
- Script language changes metadata only and never translates user text
- Autosave is controller-managed and debounced; SQL remains repository-only
- Future TTS receives enabled ordered section boundaries without model-specific preprocessing
- Future scene support is metadata-only in Phase 6
- Script data uses SQLite schema version 3 and upgrades existing databases in place

## Recommended next phase:
Phase 7 — AI Model Manager

## Suggested Git commit:
`feat: add persistent script editor and narration foundation`

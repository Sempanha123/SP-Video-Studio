PHASE 25 STATUS

Completed:
* Global reusable Asset Library added without replacing the project-specific Media Library.
* Managed/reference imports, metadata, thumbnails, fingerprints, organization, project reuse, relink, safety and persistence implemented.

Asset architecture:
* One global Asset model/framework for video, image and audio plus organizational subtypes.
* Existing MediaAsset remains the Scene/Timeline/render unit; global reuse creates lightweight project MediaAsset references with globalAssetId.

Managed assets:
* Stored under the configurable local Asset Library root with UUID physical filenames.
* Managed-file deletion is root-guarded and staged import uses temporary files before atomic replace.

Referenced assets:
* External absolute path is stored without copying the file.
* Removing a referenced Asset never deletes the user's external original.

Video assets:
* B-roll, presenter, reporter, character, interview, background, intro, outro, green-screen, overlay-video and general subtypes.

Image assets:
* Logo, background, overlay, lower-third, texture, thumbnail and general subtypes with alpha-preserving source reuse.

Audio assets:
* Music, SFX, voice-clip, intro, outro, ambience and general subtypes. Loopable/mood/genre remain manual metadata.

Collections:
* Many-to-many user collections with create/rename/delete/membership behavior; deleting a collection leaves Assets intact.

Tags:
* Many-to-many normalized Unicode tags with NFKC/case-folded uniqueness and original display text preservation.

Search/filter:
* Unicode-safe search over name/tags/collections/subtype/notes.
* Type, favorites, missing, unused, green-screen, presenter, reporter, B-roll, music and SFX filters plus metadata-only sorting.

Favorites:
* Global favorite state persists in SQLite.

Usage tracking:
* AssetUsage records project, project-media ID, usage type and used-at time; recent-use is updated on actual insertion, not preview.

Project integration:
* Adding an Asset creates/reuses a normal Project MediaAsset pointing to the global file with no physical duplicate by default.
* Make Project Copy updates the same media ID to a project-managed copy so Scene/Timeline references remain valid.
* Project duplication retains the same global Asset references; project deletion removes usage only.

News integration:
* Timeline Library panel provides News-oriented B-roll/Reporter/Presenter/Background/Logo filters and resolves dropped Assets through normal Project Media/Timeline logic.
* News provenance/claims are not modified by Asset insertion.

Story integration:
* Story-oriented Character/B-roll/Background/Music filtering routes through normal Scene/Timeline media.

Shorts integration:
* Shorts-oriented B-roll/Presenter/Music/SFX/Overlay filtering uses the same project media and Phase 22/23 Timeline path.

Template integration:
* Phase 24 local placeholder resolutions can accept globalAssetId or asset:<id>; Phase 25 converts these to normal project Media IDs before template apply.
* Portable template packaging continues to use Phase 24 rules rather than embedding local Asset IDs as a new format.

Green-screen assets:
* Chroma-ready metadata supports key color, similarity and layout recommendations; Scene insertion reuses Phase 22 ChromaKeySettings/VisualLayerService.

Presenter/Reporter assets:
* Presenter/reporter/character labels and layout hints are reusable metadata only; no permanent project SpeakerProfile identity is inferred or created silently.

Rights metadata:
* User-entered owned/licensed/royalty-free/public-domain/unknown/custom state, source URL, license label and optional attribution are persisted.
* No automatic copyright determination is implemented.

Relink system:
* Missing referenced media can be relinked; deterministic type/size/fingerprint/duration/dimension checks expose Exact Match, Likely Match or Manual Review.
* Successful relink updates every project MediaAsset referencing the global Asset.

Delete safety:
* In-use deletion is blocked by default.
* Safe explicit options support project localization before removal or library-record removal while keeping the physical file.
* Managed paths outside the library root are refused; external referenced files are never deleted.

Library storage:
* Default root is AppPaths.assets; persisted library-root setting supports Move/Copy Managed Library.
* Referenced external paths do not move; storage-use summary reports managed totals by type.

New files:
* PHASE25_REPORT.md
* docs/PHASE25_UNIVERSAL_ASSET_LIBRARY.md
* app/phase25_runtime.py
* domain/asset.py
* domain/asset_collection.py
* domain/asset_errors.py
* domain/asset_license.py
* domain/asset_usage.py
* services/asset_import_service.py
* services/asset_library_service.py
* services/asset_project_integration_service.py
* services/asset_relink_service.py
* services/asset_search_service.py
* services/asset_template_integration_service.py
* services/asset_usage_service.py
* services/asset_validation_service.py
* storage/migrations/m022_create_asset_library.py
* storage/repositories/asset_repository.py
* tests/test_phase25_assets.py
* ui/controllers/asset_library_controller.py
* ui/qml/assets/AssetCard.qml
* ui/qml/assets/AssetCollectionSidebar.qml
* ui/qml/assets/AssetFilterBar.qml
* ui/qml/assets/AssetGrid.qml
* ui/qml/assets/AssetImportDialog.qml
* ui/qml/assets/AssetInspector.qml
* ui/qml/assets/AssetLibraryPage.qml
* ui/qml/assets/AssetRelinkDialog.qml
* ui/qml/assets/ProjectAssetPanel.qml

Modified files:
* app/paths.py
* main.py
* pyproject.toml
* storage/migrations/__init__.py
* ui/qml/pages/AssetsPage.qml
* ui/qml/timeline/TimelineEditor.qml

Tests run:
* Phase 25 targeted suite: 28 passed.
* Phase 22–25 combined regression: 80 passed.
* Phase 21 regression: 19 passed.
* Python compilation: passed.
* Full historical repository suite could not be executed because this environment has connector access plus phase patch workspaces, not a complete repository checkout.

Basic import test:
* Passed video/image/audio managed import, metadata, thumbnails, search-ready persistence and SQLite reopen.

Duplicate test:
* Passed deterministic fingerprint duplicate detection, Use Existing and explicit Cancel behavior.

Project-use test:
* Passed two projects referencing the same global physical file without unnecessary media copies.

Delete-in-use test:
* Passed mandatory default guard when a reusable Asset is used by projects.

Relink test:
* Passed missing referenced file detection, validated relink and propagation to all project media references.

Green-screen asset test:
* Passed presenter/chroma metadata application through Phase 22 VisualLayer/ChromaKey integration.

Reporter News integration test:
* Reporter subtype/project layer path and News-oriented filters are wired; speaker identity remains user-confirmed rather than inferred.

Template-placeholder test:
* Passed Phase 24 placeholder resolution from global Asset ID to normal project MediaAsset ID.

Managed-delete safety test:
* Passed managed deletion plus explicit outside-library path rejection.

Referenced-delete safety test:
* Passed: deleting a referenced Asset record leaves the original external file intact.

Khmer search test:
* Passed name/tag search for វីដេអូព័ត៌មានទីក្រុង / ព័ត៌មាន and Unicode persistence.

Thai search test:
* Passed วิดีโอผู้สื่อข่าว / ข่าว Unicode tag search.

Vietnamese search test:
* Passed Phóng viên công nghệ / công nghệ with diacritics preserved.

1,000-asset performance test:
* Passed metadata-only 1,000-asset insertion/search threshold without decoding media on search/startup.

Restart persistence test:
* Passed assets, collections, Unicode tags, favorites and library-root metadata reopening from SQLite.

Known issues:
* Qt GUI/QML runtime lint was not available in this sandbox because PySide6/qmllint is not installed; QML integration is structurally covered and backend tests are green.
* Full historical tests before Phase 21 are unavailable in the patch-only execution workspace.
* Global video/audio preview in the main Asset route does not introduce a second player; Project Media/Timeline continues to use the existing playback path after an Asset is added. Thumbnail/metadata inspection is available globally.
* No automatic filesystem watcher, waveform generator, stock search, cloud sync, asset-sharing package, sensitive-trait classifier or copyright classifier is included by design.

Architecture decisions:
* Keep Global Asset and project MediaAsset as separate concepts and tables.
* Use project MediaAsset globalAssetId references to avoid file duplication while preserving all existing editors/renderers.
* Localize by updating the same project media ID so downstream Scene/Timeline references never need remapping.
* Reuse Phase 4 classifier/probe/thumbnail infrastructure, Phase 22 layered/chroma engine, Phase 24 template apply/package logic and the existing Timeline.
* Persist managed paths relative to the library root; keep referenced files external and undeletable by default.
* Use deterministic fingerprints/matching and user-entered rights/speaker metadata only.

Recommended next phase:
Phase 26 — Batch Factory

Suggested Git commit:
feat: add reusable global asset library

Do not automatically begin Phase 26.

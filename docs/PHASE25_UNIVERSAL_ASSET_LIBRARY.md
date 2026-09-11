# Phase 25 — Universal Asset Library

Phase 25 adds an application-wide reusable Asset Library while keeping the existing project Media Library authoritative for editing and rendering.

## Architecture

A global `Asset` describes reusable media, organization, rights metadata, storage mode, thumbnails, deterministic fingerprints and lightweight media metadata. It does not replace `MediaAsset`. When an Asset is used in a project, `AssetUsageService` creates or reuses an ordinary project `MediaAsset` whose metadata contains `globalAssetId`; Scene, Timeline, News, Story, Shorts, Phase 22 layers and the renderer continue to use normal project media IDs.

This keeps two clear concepts:

- **Asset Library:** reusable media available across projects.
- **Project Media:** media records currently used by one project.

## Managed and referenced assets

Managed assets live under the application Asset Library root (`AppPaths.assets`) using internal UUID filenames grouped by video/image/audio. Referenced assets keep an absolute external path and are never deleted from disk by Asset Library removal. Managed deletion is guarded so paths outside the configured library root are refused.

The library root is persisted locally and may be moved/copied with `AssetLibraryService.migrate_library`. Only managed files migrate; referenced external media is untouched.

## Import, metadata and thumbnails

Phase 25 reuses the existing Phase 4 classifier, FFprobe service and thumbnail service. Import supports the same video/audio/image extensions as Project Media. Small and normal files use full SHA-256 fingerprints; files above 256 MiB use a deterministic partial SHA-256 of the first/last chunks plus file size to avoid repeatedly hashing multi-gigabyte media. Duplicate detection never uses the filename alone.

Video/image thumbnails are stored under the global library `thumbnails/` folder. Startup performs lightweight existence/mtime/size checks only; there is no continuous filesystem watcher and no full-file hashing on every launch.

## Collections, tags and search

Collections are many-to-many. Deleting a collection only deletes membership. Tags use Unicode NFKC normalization plus case-folding for uniqueness/search while retaining the user's original Unicode display value. Search covers asset name, tags, collection names, subtype and notes. Filters include media type, favorites, missing, unused, green screen, presenter, reporter, B-roll, music and SFX.

English, Khmer, Thai, Vietnamese and mixed Unicode names/tags are stored without ASCII conversion.

## Project references and portability

`add_to_project()` creates a lightweight project `MediaAsset` referencing the global file and records `AssetUsage`. Adding the same Asset to multiple projects does not duplicate the physical file. `make_project_copy()` copies the file into project-managed media and updates the same project MediaAsset ID, so existing Scene/Timeline relationships remain valid while the project becomes independent of the global Asset.

Project duplication keeps global references pointing to the same global Asset instead of copying physical files. Project deletion removes usage rows but never deletes a global Asset.

## Missing files and relink

Referenced assets that disappear become `missing`. Relink compares deterministic media type, size/fingerprint and available duration/dimensions. Results use **Exact Match**, **Likely Match** and **Manual Review**; no AI confidence is fabricated. A successful relink updates every project MediaAsset referencing that global Asset, so all projects recover together.

## Green-screen, presenter and reporter assets

Video subtype metadata can describe `presenter`, `reporter`, `character`, `green_screen`, default position, key color, chroma similarity, crop/scale hints and an optional speaker label. These are recommendations only; an Asset never stores a permanent project `SpeakerProfile` ID. Adding a chroma-ready asset to a Scene reuses Phase 22 `VisualLayerService` and `ChromaKeySettings`.

## News, Story, Shorts and normal Video

The Timeline contains a **Library** panel alongside Video/Shorts controls. Global Asset cards drag with `sp-global-asset`; dropping resolves/creates normal Project Media and then uses the existing universal Video Studio/Timeline operation. Workflow filters expose useful subtypes for News (B-roll/Reporter/Presenter/Background/Logo), Story (Character/B-roll/Background/Music) and Shorts (B-roll/Presenter/Music/SFX/Overlay). News provenance, Story structure and Short metadata are not changed by Asset insertion.

## Template integration

Phase 24 placeholder resolutions may use `{ "globalAssetId": "…" }` or `asset:<id>` locally. Phase 25 resolves that to a normal Project Media ID before Phase 24 applies the template. Portable template export remains governed by Phase 24 packaging rules; local Global Asset IDs are not a new portable package format.

## Rights and attribution metadata

Rights status is user-entered only: `owned`, `licensed`, `royalty_free`, `public_domain`, `unknown` or `custom`. The default is `unknown`. Optional source URL, license name, notes and attribution text are stored locally. `attribution_summary(project_id)` lists used assets that the user marked as requiring attribution. Phase 25 never determines copyright ownership automatically and never automatically inserts attribution into a video.

## Delete safety

Unused managed assets may delete their managed file after path validation. Referenced Asset deletion removes only the library record. An in-use Asset is blocked by default. Explicit safe alternatives are:

- **Create Project Copies then Remove:** localize every project reference first.
- **Remove from Library but Keep File:** detach global metadata and preserve the physical file.

There is no automatic cleanup/deletion policy.

## Performance

The card/index path loads SQLite metadata and thumbnail paths rather than decoding media. Grid/List QML uses reusable delegates. The Phase 25 test suite covers a 1,000-asset metadata search without opening media files.

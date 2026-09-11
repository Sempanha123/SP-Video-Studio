# PHASE 11 STATUS

## Completed:

- Provider-based multilingual translation architecture
- English → Khmer and Khmer → English launch language pairs
- Local Marian/OPUS adapter using app-managed offline model folders
- Manual Translation provider that works without AI/model installation
- Structured translation + translation-segment SQLite persistence
- Transcript, Script, and Manual Text source foundations
- Side-by-side human Translation Review workspace
- Separate immutable machine output and editable reviewed translation
- Reviewed / edited / locked / needs-attention / orphaned states
- Bulk translation, per-segment retranslation, retry and resume
- Locked/manual-edit protection during bulk retranslation
- Stable source/document fingerprints and per-segment SHA-256 hashes
- Source synchronization preserving unchanged reviewed work
- Placeholder, URL, number, and Keep Terms safety checks
- UTF-8 translated and bilingual TXT export
- Transcript segment playback through the existing Phase 5 player
- Project duplication/deletion compatibility
- Translation Model Manager category and AI-resource coordination

## Translation architecture:

- `TranslationEngine` remains provider-neutral.
- `TranslationEngineManager` owns Local Marian and Manual providers.
- `TranslationService` owns document lifecycle, source mapping, translation jobs, review, synchronization, export and duplication.
- `TranslationReviewService` protects placeholders/terms and performs non-confidence quality heuristics.
- `TranslationChunkingService` uses lossless paragraph/sentence-aware chunks instead of silent tokenizer truncation.
- SQL remains inside `TranslationRepository`; QML uses `TranslationController`.

## Providers:

- Local Translation — offline, model-backed `LocalMarianEngine`.
- Manual Translation — no model/network; produces editable review rows with empty targets.
- Provider interfaces already expose capability/network/credential concepts for future cloud/LLM engines without implementing them now.

## Local model(s) tested:

- Registry/API adapter: `Helsinki-NLP/opus-mt-en-mkh` for English → Khmer.
- Registry/API adapter: `Helsinki-NLP/opus-mt-mkh-en` for Khmer → English.
- Standard CI uses FakeTranslationEngine; real model loading is opt-in and was not executed in this sandbox.

## Model licenses verified:

- `Helsinki-NLP/opus-mt-en-mkh` — Apache-2.0.
- `Helsinki-NLP/opus-mt-mkh-en` — Apache-2.0.
- Canonical identifiers/license metadata were verified against current upstream model pages on 2026-09-11.
- Models are not automatically bundled with the application.

## English → Khmer:

- Registry pair `translation-en-km-opus`.
- Adapter applies the upstream-required `>>khm<<` target token internally.
- English source, Unicode placeholders, numbers, URLs and Keep Terms are preserved/reviewed through the shared safeguards.

## Khmer → English:

- Registry pair `translation-km-en-opus`.
- Khmer source text is stored/exported as Unicode without English-style token normalization.
- Manual and fake-engine reverse-pair tests pass.

## Transcript translation:

- Each source transcript segment maps to an independent translation segment.
- Original source segment ID/start/end timestamps are preserved exactly.
- Transcript words remain on the source transcript; target-language word timings are not fabricated.
- Source segment playback reuses the shared player.

## Script translation:

- Enabled script sections become ordered translation units.
- Disabled sections are excluded.
- Section IDs, order and titles are preserved as source metadata.
- Original script content is never overwritten.

## Review editor:

- Professional SOURCE | TRANSLATION rows.
- Search and filters for Unreviewed / Reviewed / Edited / Needs Attention / Locked.
- Review progress and document approval.
- Sync Source, translated TXT export, bilingual TXT export and copy actions.
- Debounced target-text autosave through the controller.

## Manual editing:

- `machine_translation` preserves original provider output.
- `translated_text` stores the human-reviewed version.
- Reset restores machine output without calling the provider again.
- Manual edits survive restart and project duplication.

## Lock/protection system:

- Locked rows cannot be overwritten by bulk retranslation.
- Bulk retranslation protects manually edited rows by default.
- Per-row replacement of manual edits requires an explicit replace action.
- Mandatory lock regression test passes.

## Source synchronization:

- Document SHA-256 fingerprint plus per-row source hashes.
- Changed source row → Needs Attention while preserving prior target text.
- Unchanged reviewed/locked row remains intact.
- New source row → Pending.
- Deleted source row → Orphaned rather than silently discarded.
- Script reorder with unchanged content updates ordering without invalidating reviewed target text.

## Cancellation/resume:

- Cancellation is checked between segments/chunks.
- Completed translations remain persisted as Draft.
- Pending/failed rows remain resumable.
- Resume/retry skips protected reviewed/locked/manual-edited work according to policy.

## Model Manager integration:

- New Translation model purpose/category.
- Two Apache-2.0 OPUS/Marian models registered with canonical source IDs, license, pair metadata, size guidance and managed install paths.
- Translation page never initiates hidden model downloads.
- Missing local model leaves Manual Translation available.
- Loaded/in-use state uses existing ModelService acquire/release APIs.

## AI resource coordination:

- Translation joins the existing `AIResourceManager` used by VoxCPM2 and faster-whisper.
- Auto local translation is CPU-first to avoid unnecessary VRAM contention.
- Explicit CUDA requests coordinate/unload idle heavy engines and refuse conflicts with active jobs.

## New files:

- `domain/language.py`
- `domain/translation.py`
- `domain/translation_segment.py`
- `domain/translation_profile.py`
- `domain/translation_job.py`
- `engines/translation/errors.py`
- `engines/translation/types.py`
- `engines/translation/local_marian_engine.py`
- `engines/translation/manual_engine.py`
- `engines/translation/fake_engine.py`
- `engines/translation/manager.py`
- `services/translation_service.py`
- `services/translation_review_service.py`
- `services/translation_chunking_service.py`
- `storage/migrations/m008_create_translations.py`
- `storage/repositories/translation_repository.py`
- `ui/controllers/translation_controller.py`
- `ui/models/translation_segment_model.py`
- `ui/qml/editor/TranslationPage.qml`
- `ui/qml/editor/TranslationToolbar.qml`
- `ui/qml/editor/TranslationSegmentRow.qml`
- `ui/qml/editor/TranslationInspector.qml`
- `ui/qml/editor/TranslationSetupDialog.qml`
- `ui/qml/editor/TranslationStatsBar.qml`
- `tests/test_translation_phase11.py`
- `tests/test_translation_adapter.py`
- `tests/test_translation_qml_structure.py`
- `tests/test_translation_integration.py`
- `PHASE11_REPORT.md`

## Modified files:

- `README.md`
- `pyproject.toml`
- `app/bootstrap.py`
- `domain/ai_model.py`
- `engines/model_registry.py`
- `engines/translation/base.py`
- `engines/translation/__init__.py`
- `services/project_service.py`
- `services/script_service.py`
- `services/transcription_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/qml/pages/ModelsPage.qml`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- migration-version regression tests for existing phases

## Tests run:

- `python -m compileall -q app domain engines services storage ui workers`
- `pytest -q`
- 254 passed
- 5 skipped: two PySide6 live-runtime checks plus opt-in VoxCPM2, faster-whisper, and real translation-model integrations
- Phase 0–10 regression tests remain green
- Phase 11 focused translation suite: 34 passed, 1 opt-in integration skip

## Fake-engine tests:

- Both English → Khmer and Khmer → English.
- Transcript/script/manual source creation.
- Review/edit/reset/lock/approve/search/export.
- Partial cancellation + resume.
- Mandatory lock protection.
- Mandatory source-update preservation.
- Project ownership, restart persistence and duplication/deletion behavior.

## Real local-model integration test:

- Opt-in test exists for both managed local model folders.
- It is disabled in normal CI and no real model weight download/load was performed in this sandbox.

## English → Khmer quality check:

- Automated checks verify non-empty/Unicode-safe plumbing, target-token routing, placeholders/numbers and source mapping.
- Human Khmer translation quality was not claimed or manually reviewed in this sandbox; fluent review remains required before publication.

## Khmer → English quality check:

- Automated checks verify reverse pair routing and Unicode persistence.
- Human semantic-quality listening/review was not performed here; production content still requires review.

## Restart persistence test:

- Machine output, manually edited target text, reviewed state, locks, source mappings, timestamps, language pair and document state persist through reopened SQLite repositories.

## Known issues:

- Live QML runtime smoke is unavailable in this sandbox because PySide6 is not installed.
- Real Marian/OPUS weights were not downloaded for CI; use the explicit opt-in integration test on the target machine.
- Translation quality varies by content/domain; the UI intentionally requires human review and never presents a fabricated confidence score.
- Phase 11 stores translated scripts independently rather than replacing/creating a second primary Phase 6 Script automatically.

## Architecture decisions:

- Provider-neutral engine/domain; no model-specific database schema.
- CPU-first local translation to reduce GPU contention.
- Direct Transformers tokenizer/model generation, not deprecated translation pipeline helpers.
- Local loading uses app-managed model folders and `local_files_only=True`.
- Machine output and human-reviewed output are separate fields.
- Locks and manual edits are protected by default.
- Source sync is hash-based and preserves unchanged localization work.
- Translation timing remains segment-level; target-language word timings are deliberately not fabricated.
- No cloud translation requests exist in Phase 11.

## Recommended next phase:
Phase 12 — Subtitle Engine and Subtitle Studio

## Suggested Git commit:
`feat: add multilingual translation engine and review workflow`

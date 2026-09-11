# PHASE 18 STATUS

Completed:

* Source-grounded News Studio implemented for existing `workflow = news` projects using the mandatory Source → Evidence → Claim → Review → Script path.
* Schema v15 adds normalized News sources/snapshots, claims/evidence, briefs/items, and claim-to-Script mappings without creating duplicate Script/Voice/Subtitle/Scene/Timeline/Render systems.
* Manual/local News workflows work offline; URL fetching is an explicit user-requested operation and all downstream video production reuses the existing Phase 6–17 services.

News architecture:

* `NewsService` coordinates project metadata, overview/readiness, duplication, and the News editorial workflow while generic Project remains canonical.
* News-specific domain models cover project metadata, sources/snapshots, claims/evidence, briefs/items, and Script provenance mappings only.
* `NewsController` exposes the editorial workflow to QML and routes Script, Voice, Scenes, Subtitles, Timeline, Director, and Export back to existing shared workspaces.
* `engines/news` provides a structured deterministic/offline provider boundary for future claim/script providers; no cloud provider is configured in Phase 18.

Source types:

* Web Link (public HTTP/HTTPS only), Manual Text, and Local TXT/Markdown/HTML document sources.
* Local files are copied into `project/sources/`; the user's external original is never moved, edited, or deleted.
* PDF/DOCX extraction is intentionally not added because Phase 18 permits it only where a safe existing parser already exists.

URL security:

* `PublicURLPolicy` rejects non-HTTP schemes, embedded credentials, localhost/`.local`, loopback, private, link-local, and any other non-global IPv4/IPv6 address.
* Every redirect destination is revalidated; redirect count is bounded and public→private redirects are rejected.
* Response size is capped at 5 MiB by default, timeout is bounded, content type is restricted to HTML/plain text, and 403/404/410/429/5xx responses map to typed News errors.
* No JavaScript execution, link crawling, authenticated scraping, paywall bypass, or internet-wide research is performed.

Source extraction:

* Pluggable `SourceExtractor` interface includes HTML article and plain-text implementations.
* HTML extraction prefers article/main text and removes common navigation/header/footer/script/style clutter while reading common title/author/published metadata.
* Charset handling preserves UTF-8/Khmer; dynamic JavaScript-only or difficult paywalled pages fall back to manual source text rather than bypass behavior.

Source snapshots:

* Source content used as evidence is stored in immutable versioned snapshots with SHA-256 content hashes.
* URL refresh/manual edit creates a new snapshot; old snapshots remain resolvable for existing evidence.
* Manual-source edits do not destroy prior provenance, and fetched snapshot text is not silently rewritten.

Claims:

* Claim states: candidate, needs review, approved, rejected, unsupported, and conflicting.
* Users can create claims manually from evidence, use deterministic candidate helpers, edit/lock/reject/approve them, merge probable duplicates, and search/filter them.
* Approval normally requires evidence; an unsupported claim cannot silently become approved.
* Importance and uncertainty are editorial metadata, not a fabricated confidence/truth score.

Evidence:

* Evidence links a claim to a specific source + immutable snapshot and stores only the relevant excerpt/offset metadata.
* Claims can have multiple supporting sources; source count is provenance information only.
* Source removal preserves historical News data while marking claims unsupported when their final active support disappears.

Conflict handling:

* Deterministic number/date discrepancy checks can mark competing claims `conflicting`.
* News Studio never selects a winner automatically; review supports keep A, keep B, keep both as uncertainty, reject both, or edit through the claim service.
* Duplicate detection is advisory and never silently merges claims.

Quotes:

* Quote claims store quote text, speaker, quote kind, source evidence, and original wording.
* `translated_quote` preserves the original source quote; paraphrases are never automatically converted to direct quotations.

News Brief:

* `NewsBrief` organizes approved claim IDs into flexible Lead / What Happened / Key Details / Background / Why It Matters / What Happens Next sections.
* Brief items retain claim IDs instead of copying unsupported factual text into an opaque document.
* Approved-claim/source fingerprints allow a prior brief to be marked Out of Date without deleting it.

Script grounding:

* `NewsScriptService` creates/updates the normal Phase 6 Script/ScriptSection domain; no `NewsScript` replacement exists.
* Deterministic offline script building uses approved brief/claim facts plus clearly connective language for Straight News, Explainer, Short Update, or Documentary News structure.
* `NewsScriptMapping` links factual Script text snapshots to claim IDs. Unsupported factual-looking sentences are flagged, and editing a mapped factual sentence marks its mapping Needs Review without altering the claim.
* Script duration continues to use `ScriptAnalysisService`; no facts are auto-deleted to meet a duration target.

Translation integration:

* News translation delegates to Phase 11 `TranslationService` and stores News claim-provenance metadata on the translated version.
* Original grounded News claims remain the provenance layer across language changes; no second factual News layer is generated.

Voice integration:

* News uses the existing Voice Studio/TTS pipeline. The News workflow can recommend the existing News Anchor category, but creating a News script does not auto-generate narration.

Scene integration:

* Scene creation delegates to the existing Phase 13 `SceneService` using the standard Script sections.
* Scenes keep generic Scene records with small `news_role` metadata only; no News-specific Scene architecture or Phase 19 graphics are introduced.

AI Director integration:

* News Studio invokes the existing Director with `workflow = news` and grounded-News metadata.
* Director remains structure-only for News: duration, scene count, pace, voice, subtitles, and transitions; it does not invent facts/sources/quotes.

Source export:

* TXT-style source list and structured JSON provenance export are supported.
* Article body text is excluded by default; full snapshot content is exported only through the explicit `include_content` option.
* Source list text is suitable for manual copy into a video description; Phase 18 never uploads/publishes automatically.

New files:

* `domain/news_brief.py`
* `domain/news_claim.py`
* `domain/news_project.py`
* `domain/news_script_mapping.py`
* `domain/news_source.py`
* `engines/news/__init__.py`
* `engines/news/base.py`
* `engines/news/deterministic.py`
* `services/news_brief_service.py`
* `services/news_claim_service.py`
* `services/news_errors.py`
* `services/news_extraction_service.py`
* `services/news_review_service.py`
* `services/news_script_service.py`
* `services/news_service.py`
* `services/news_source_fetch_service.py`
* `services/news_source_service.py`
* `services/news_validation_service.py`
* `storage/migrations/m015_create_news_studio.py`
* `storage/repositories/news_repository.py`
* `workers/news_extraction_worker.py`
* `workers/news_source_worker.py`
* `ui/controllers/news_controller.py`
* `ui/qml/news/NewsBrief.qml`
* `ui/qml/news/NewsClaimRow.qml`
* `ui/qml/news/NewsClaims.qml`
* `ui/qml/news/NewsReadiness.qml`
* `ui/qml/news/NewsScriptBuilder.qml`
* `ui/qml/news/NewsSetup.qml`
* `ui/qml/news/NewsSourceCard.qml`
* `ui/qml/news/NewsSourceInspector.qml`
* `ui/qml/news/NewsSources.qml`
* `ui/qml/news/NewsStudio.qml`
* `tests/test_news_phase18.py`
* `tests/test_news_qml_structure.py`
* `PHASE18_REPORT.md`

Modified files:

* `README.md`
* `app/bootstrap.py`
* `domain/news.py` (foundation placeholder upgraded to compatibility exports for the real News domain)
* `services/project_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/__init__.py`
* `ui/qml/pages/ProjectWorkspacePage.qml`
* prior schema-version regression assertions updated to v15.

Tests run:

* Phase 18 focused domain/service/QML suite: **46 passed**.
* Non-integration Phase 0–18 suite: **485 passed, 2 expected PySide6 skips**.
* Existing real FFmpeg media/render/export/timeline integration partition: **12 passed, 2 expected skips** (runtime hardware encoder unavailable; 60-second performance test opt-in).
* Real faster-whisper / VoxCPM2 / Marian translation integrations remain opt-in: **3 expected skips**.
* Combined verified test partitions: **497 passed, 7 expected skips**.
* `python -m compileall` and final QML delimiter/static structure checks pass in the packaging environment.

SSRF/security tests:

* Mandatory loopback/private/link-local IPv4/IPv6 cases are rejected: `127.0.0.1`, `::1`, `10/8`, `172.16/12`, `192.168/16`, and `169.254/16`.
* `file://`, FTP, and other non-HTTP schemes are rejected.
* Public→private redirect regression is rejected before the redirected request is issued.
* Size-limit, 429, and timeout behavior are covered by deterministic fake-opener tests.

Source-version test:

* Snapshot A remains immutable after a source refresh/manual edit creates Snapshot B.
* B becomes latest while claims/evidence linked to A continue resolving against A.

Claim-support test:

* Approval without evidence is blocked/marks the claim unsupported.
* After evidence is linked to an immutable snapshot, the same claim can be explicitly approved.

Conflict test:

* Competing values (100 vs 120) and competing dates are marked conflicting.
* No automatic winner is chosen.

Script-grounding test:

* Factual deterministic News script sentences map to valid approved claim IDs.
* Injecting an unsupported factual sentence is detected as unsupported/needs review.
* Editing the meaning of mapped factual text invalidates the Script mapping while preserving the approved claim itself.

English News workflow test:

* Three source fixtures + five approved claims build a provenance-linked brief and Short Update Script.
* Grounding validation reports no unsupported generated factual sentence in the deterministic draft.

Khmer News workflow test:

* Khmer source text, claims, brief, Script, search, restart persistence, and UTF-8 storage pass without mojibake/corruption.

Project duplication test:

* Completed News data duplicates with new source/snapshot/claim/evidence/brief/mapping IDs.
* Managed source file copies are recreated inside the duplicated project and no duplicated provenance points to original project-owned IDs.
* URL sources are not refetched during duplication.

Restart persistence test:

* Fresh SQLite repository instances reload News project metadata, sources, immutable snapshots, multi-source evidence, approved claims, briefs, and Script mappings with all provenance relationships intact.

Known issues:

* PySide6 is not installed in this packaging sandbox, so live News QML/worker-interaction QA is not executed here; QML structure/delimiter tests pass.
* HTML extraction is intentionally lightweight and standard-library based. JavaScript-only article bodies, complex publisher layouts, and inaccessible/paywalled pages may require `Paste Source Text Manually`.
* Initial local-document extraction supports TXT/Markdown/HTML. PDF/DOCX are not added until a safe parser is deliberately integrated.
* Deterministic candidate extraction is conservative and is not a semantic fact checker; human review remains mandatory.
* No cloud LLM News provider, web-wide research, search-engine crawling, breaking-news monitoring, scheduled refresh, automatic publishing, News-specific graphics, or automatic maps/charts are implemented.
* Removed sources are soft-removed so evidence history stays inspectable; project deletion performs the final project-owned data/file cleanup.

Architecture decisions:

* Existing `Project.workflow = news` is reused; NewsProject is metadata/provenance, not a second Project type.
* Source snapshots are stored in SQLite for deterministic offline provenance/restart portability; local original files are separately copied into managed project storage.
* News claim/evidence/brief tables are normalized instead of using one opaque `news_data_json` blob.
* Every factual Script path goes through approved claims/evidence; connective text is classified separately so grounding checks do not over-flag editorial transitions.
* Fetching remains a bounded one-source request through the worker pool; no implicit crawling/concurrent research fan-out is introduced.
* Translation, Voice/TTS, Subtitles, Scenes, Timeline, AI Director, Render, and Export remain the existing shared systems and are referenced rather than duplicated.

Recommended next phase:
Phase 19 — News Visual System and News Graphics

Suggested Git commit:
`feat: add source-grounded News Studio workflow`

Do not automatically begin Phase 19.

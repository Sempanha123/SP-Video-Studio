# PHASE 19 STATUS

Completed:

* Professional News Visual Studio implemented on top of the existing Phase 18 News provenance, Phase 13 Scene/SceneOverlay, Phase 17 Timeline, and Phase 15/16 render/export systems.
* News graphics consume approved claims, quote metadata, sources, Script/editor text, and existing scene media; Phase 19 does not create factual claims, research sources, or a News-only renderer.
* SQLite schema v16 adds project News themes, per-scene layout metadata, and visual provenance links while generic overlay geometry/text/timing remain canonical.
* Headline, breaking, fact, number/stat, quote, source attribution, lower third, topic, intro, and outro graphics are available through responsive News layouts.
* Storyboard, Timeline, News Visual Studio, render, export, project duplication, restart persistence, and Phase 18 readiness all share the same project data.

News visual architecture:

* `NewsVisualService` coordinates themes, layouts, managed generic overlays, provenance, source-change status, validation, duplication, and Phase 17 command-stack undo/redo.
* `NewsVisualElement` stores only News graphic/provenance metadata pointing at a normal `SceneOverlay`; text/geometry/timing are not duplicated into a second News rendering model.
* `NewsSceneLayoutInstance` stores applied preset/version/theme/customized state per existing Scene.
* Versioned builtin registries live under `resources/news/presets/` and `resources/news/layouts/`; QML does not own layout coordinates.

Builtin themes:

* Clean News.
* Modern News.
* Breaking News.
* Documentary News.
* Minimal News.
* Tech News.
* Themes are original restrained presets and do not reproduce identifiable broadcaster branding.

Headline cards:

* Full-screen/structured headline content can be created with optional kicker/category and source attribution.
* Headline layouts use responsive normalized geometry and theme heading typography.
* Long text is reported by validation/TextFit helpers; factual/headline words are never silently removed.

Breaking News cards:

* Restrained breaking treatment uses stronger accent/weight without flashing or high-frequency motion.
* Breaking content remains editor-provided/source-derived and does not create new News facts.

Fact cards:

* Fact cards require an approved Phase 18 News claim and retain claim/source provenance.
* A later claim change marks the card `Source Changed`; card text remains unchanged until the user explicitly chooses Update from Claim.
* Rejected/unsupported/conflicting claim links produce stronger visual/readiness warnings.

Number/stat cards:

* Number cards retain explicit raw value, unit, label, source/claim link, and display text.
* Phase 19 does not guess which number in a source is the primary statistic and does not silently round/localize sourced values.

Quote cards:

* Exact and translated quotes use quotation treatment; translated quote metadata remains distinguishable.
* Paraphrases are labeled/treated as paraphrases and are not displayed as direct quotations.
* Quote claim/source provenance is preserved.

Source attribution:

* Compact source graphics use publisher/organization/title metadata.
* Full URLs remain provenance metadata/source-list data and are not rendered on screen by default.

Lower thirds:

* Generic lower thirds support primary/secondary/category-style text and optional source metadata.
* They compile to ordinary Scene overlays, so timing changes made in Timeline remain visible in News Visual Studio.

Scene layouts:

* Headline Focus.
* Media + Headline.
* Media + Lower Third.
* Fact Focus.
* Quote Focus.
* Number Focus.
* Source Focus.
* Split Visual.
* Full Media.
* Intro.
* Outro.
* Reapplying a layout replaces only News-managed overlays; unrelated user overlays are preserved. Detach Layout converts the managed visuals to manual customization.

Aspect-ratio adaptation:

* Layout resolver supports 16:9, 9:16, and 1:1 using normalized coordinates.
* Vertical layouts can rearrange media/text rather than uniformly shrinking a 16:9 design.
* Application safe-area recommendations are validated for critical text/source regions.

Theme customization:

* Project theme supports primary/accent/background/surface/text colors, heading/body/number fonts, optional logo reference, corner radius, and spacing metadata.
* Managed overlays follow the active theme until detached/customized.
* Contrast/font/readability issues are warnings; user colors are not silently overwritten.
* Theme/layout visual operations are undoable through the Phase 17 command stack; undo history remains session-only, matching Timeline behavior.

Claim/source provenance:

* Visual elements can reference duplicated Phase 18 claim/source IDs and keep source hashes for change detection.
* Manual visual content is marked Manual instead of being presented as source-grounded fact.
* Project duplication remaps scene/claim/source/media references to the duplicated project; no original project-owned News IDs remain in duplicated visual metadata.

Khmer support:

* News headings, facts, lower thirds, source attribution, and mixed English + Khmer continue through the existing libass/Noto Sans Khmer Unicode text path.
* A real Khmer card frame was inspected with shaped Khmer glyphs and no missing-glyph boxes.
* A real vertical English + Khmer frame was inspected with both scripts readable and non-overlapping inside the selected card/safe region.

Timeline integration:

* News graphics appear only on the existing generic Overlay track.
* Open-ended overlays now map safely to scene-end duration in `TimelineMappingService`.
* A Phase 19 regression changes a News overlay's timing through `TimelineEditService` and immediately observes the same timing in News Visual Studio data.

Renderer integration:

* Generic `SceneOverlayType.SHAPE` adds reusable rectangles/panels/accent bars; it is not News-specific.
* `ScenePreview.qml`, Scene render specs, Timeline, and Phase 15 renderer all consume the same shape/text overlays.
* FFmpeg renders shapes with `drawbox` before the existing ASS/libass text renderer; no QML screenshots or second renderer are used.
* Real Phase 19 FFmpeg tests render Khmer and vertical bilingual News cards successfully.

News readiness integration:

* Phase 18 factual readiness remains intact and independent.
* News overview/readiness additionally reports News visual total/ready/warning counts.
* Visuals linked to rejected/unsupported/conflicting claims produce warnings/errors without relabeling the factual layer as a truth score.

New files:

* `domain/news_graphic_preset.py`
* `domain/news_scene_layout.py`
* `domain/news_visual_element.py`
* `domain/news_visual_theme.py`
* `resources/news/layouts/layouts.json`
* `resources/news/presets/graphics.json`
* `resources/news/presets/themes.json`
* `services/news_branding_service.py`
* `services/news_graphic_service.py`
* `services/news_layout_service.py`
* `services/news_text_fit_service.py`
* `services/news_visual_errors.py`
* `services/news_visual_service.py`
* `services/news_visual_validation_service.py`
* `storage/migrations/m016_create_news_visuals.py`
* `storage/repositories/news_visual_repository.py`
* `tests/test_news_visual_ffmpeg_integration.py`
* `tests/test_news_visual_phase19.py`
* `tests/test_news_visual_qml_structure.py`
* `ui/controllers/news_visual_controller.py`
* `ui/qml/news/visuals/FactCardEditor.qml`
* `ui/qml/news/visuals/HeadlineCardEditor.qml`
* `ui/qml/news/visuals/LowerThirdEditor.qml`
* `ui/qml/news/visuals/NewsGraphicInspector.qml`
* `ui/qml/news/visuals/NewsGraphicPicker.qml`
* `ui/qml/news/visuals/NewsSceneLayoutPicker.qml`
* `ui/qml/news/visuals/NewsThemePanel.qml`
* `ui/qml/news/visuals/NewsVisualStudio.qml`
* `ui/qml/news/visuals/QuoteCardEditor.qml`
* `ui/qml/news/visuals/SourceCardEditor.qml`
* `PHASE19_REPORT.md`

Modified files:

* `README.md`
* `app/bootstrap.py`
* `domain/scene_overlay.py`
* `rendering/overlay_renderer.py`
* `rendering/scene_renderer.py`
* `services/news_service.py`
* `services/project_service.py`
* `services/timeline_mapping_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/__init__.py`
* schema-version regression assertions in prior Phase tests updated to v16
* `ui/qml/editor/ScenePreview.qml`
* `ui/qml/news/NewsStudio.qml`
* `ui/qml/pages/ProjectWorkspacePage.qml`

Tests run:

* Phase 19 focused domain/service tests: **31 passed**.
* Phase 19 QML/static structure tests: **5 passed**.
* Non-integration Phase 0–19 regression partition: **523 passed, 2 expected PySide6 skips**.
* Real media/render/export/timeline + Phase 19 FFmpeg partition: **14 passed, 2 expected skips** (unusable hardware encoder in this runtime; 60-second performance check remains opt-in).
* Real faster-whisper / Marian translation / VoxCPM2 model integrations: **3 expected opt-in skips**.
* Combined verified partitions: **537 passed, 7 expected skips**.
* `python -m compileall` passes.
* Full single-process `pytest -q` was also attempted but exceeded the container command timeout during the known real-media portion; the same suite is therefore reported from the clean deterministic partitions above.

Fact-source-change test:

* PASS — changing a linked approved claim marks the fact visual Source Changed while preserving current display text; Update from Claim changes it only after explicit user action.

Rejected-claim test:

* PASS — a visual created from an approved claim becomes `unsupported_source` with a rejected-claim validation issue after the claim is rejected, and News visual readiness reports the problem.

Quote-type test:

* PASS — exact, translated, and paraphrase variants preserve their distinct metadata/treatment; paraphrase does not receive direct-quote quotation styling.

Khmer render test:

* PASS — real FFmpeg output with `ព័ត៌មានបច្ចេកវិទ្យាថ្មី` and `ក្រុមហ៊ុនបានប្រកាសផលិតផលថ្មីនៅថ្ងៃនេះ។` renders through libass; extracted frame manually inspected with shaped Khmer and no tofu/missing glyph boxes.

Bilingual render test:

* PASS — real 9:16 FFmpeg output renders `OpenAI` with `បច្ចេកវិទ្យាថ្មី`; extracted frame manually inspected for readability, no overlap, and safe panel placement.

Timeline synchronization test:

* PASS — News card overlays are ordinary Phase 17 Overlay-track clips; a timing edit through `TimelineEditService` is immediately returned by News Visual Studio from the same canonical overlay record.

Render-parity test:

* PASS for the shared data/render path — core News cards compile into generic shape + text Scene overlays/render specs, and real FFmpeg output validates that geometry/colors/text/timing are consumed by Phase 15.
* Representative Khmer and bilingual frames were manually compared against the normalized card design. Live Qt pixel-perfect comparison is unavailable because PySide6 is absent in this validation container.

Project duplication test:

* PASS — News themes/layouts/elements duplicate with new IDs; scene/claim/source/media provenance links map into duplicated project entities and do not retain original project-owned IDs.

Restart persistence test:

* PASS — a custom News theme plus three News scenes (headline, fact card, lower third), provenance links, and customized-layout state persist after reopening repositories from the same database.

Known issues:

* PySide6 is not installed in the validation container, so live QML runtime smoke remains an expected skip; QML is covered by static structure tests and the shared data model.
* QML card preview supports rounded rectangle radius, while Phase 19 FFmpeg generic shapes use `drawbox`; exported card corners are square in this phase. Text, geometry, opacity, colors, timing, and safe-area placement share the same canonical data.
* No keyframe/motion-graphics engine is introduced; News graphics are static except for pre-existing renderer capabilities.
* User-global News visual preset CRUD is optional in the Phase 19 specification and is not added; builtins are versioned and effective scene values are persisted when applied.

Architecture decisions:

* Generic Scene/SceneOverlay remains canonical; News tables store only theme/layout/provenance metadata.
* A single generic `shape` overlay primitive was added so future non-News workflows can reuse panels/rectangles without renderer-specific hacks.
* Facts/quotes/numbers never originate from the visual layer; sourced cards reference Phase 18 entities and manual cards are explicitly marked Manual.
* Layout coordinates are normalized and resolved in Python services for 16:9/9:16/1:1 rather than hardcoded in QML.
* Layout replacement is scoped to News-managed overlays to protect unrelated Storyboard edits.
* News visual undo/redo reuses the Phase 17 command stack and stores metadata/overlay snapshots only, never media payloads.

Recommended next phase:
Phase 20 — Story Studio

Suggested Git commit:
`feat: add professional News visual system and graphic presets`

Do not automatically begin Phase 20.

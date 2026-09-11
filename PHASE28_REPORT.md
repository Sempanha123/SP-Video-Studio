PHASE 28 STATUS

Completed:

* Completed Phase 28 only on top of pushed Phase 27 commit `d05f8144a196980a1f89b4abedda27d1455b2ad3`.
* Added an application-wide Soft Creator Studio presentation system without changing backend/domain behavior.
* Preserved Phase 27 autosave/recovery, Phase 26 Batch, Phase 25 Assets, Timeline editing, News, Story, dubbing, Shorts, Templates, Models and Voice logic.

Design direction:

* Soft, friendly, low-saturation creator desktop UI with calm lavender/indigo accents and neutral layered surfaces.
* Avoids neon, strong blue dominance, glow-heavy hover, excessive gradients, confetti and childish styling.

Theme system:

* Expanded semantic Theme/Colors/Typography/Spacing/Radius/Animation tokens while retaining compatibility with existing QML token names.
* Added comfortable/compact density state and reduced-motion-aware animation durations.
* Added semantic preview, Timeline, selected, disabled and dialog-overlay colors.

Light theme:

* Off-white background, softly tinted surfaces, dark neutral text, muted lavender accent and gentle semantic statuses.

Dark theme:

* Deep neutral gray rather than pure black, raised surfaces, muted borders and softened accent/status colors.
* Preview and Timeline remain dedicated dark-neutral creator surfaces.

Color system:

* Feature controls now use semantic colors for background/surfaces/text/borders/accent/status/editor surfaces.
* Reconstructed QML audit leaves one intentional media-overlay text color in `AssetCard.qml`; the previous Batch `Qt.rgba` stripe and dialog raw scrim were replaced with semantic tokens.

Typography:

* Compact desktop hierarchy: page title 22 px, section title 16 px, body 14 px, secondary/caption 12–13 px and Timeline labels 11 px.
* Segoe UI remains the Windows UI default with documented Noto fallback families.

Khmer typography:

* Added Khmer fallback metadata and a 1.5 multilingual line-height policy to avoid clipped combining marks and squeezed text.

Thai typography:

* Added Thai fallback metadata and increased multilingual line height so above/below marks have vertical room.

Vietnamese typography:

* Standard Unicode UI fonts, non-clipping line-height policy and long-text/elision rules retain Vietnamese diacritics cleanly.

Navigation:

* Polished soft active state, muted hover and compact editor/smaller-window navigation behavior.
* Active navigation uses a small accent indicator rather than a saturated full-row blue block.

Home:

* Existing Home content and business bindings preserved; shared card/button/status/theme updates give it the new creator styling without a risky page rewrite.

Project creation:

* Existing Create workflow remains fast and intact while inheriting the compact input/button/card system and workflow tints.

Editor workspace:

* Main shell now emphasizes project/page title, Phase 27 save state, system readiness and essential actions.
* Ctrl+S delegates to the existing Phase 27 save path rather than adding duplicate serialization logic.
* Preview/editor areas use dedicated creator-workspace surfaces and practical minimum sizing.

Timeline:

* Existing Timeline behavior preserved while ruler, track and preview surfaces use dedicated dark-neutral tokens.
* Muted clip families are available for video/audio/voice/subtitle/overlay content and selection remains accent-outline based.
* No expensive per-clip effects or continuous decorative animation added.

Inspector:

* Added reusable `InspectorSection.qml` for compact collapsible Transform/Crop/Green Screen/Audio/Speaker/Voice/Timing/Style-style groups and progressive disclosure.

Voice Studio:

* Existing Voice Studio retains all functionality and inherits softer cards, buttons, inputs, status colors, typography and multilingual language selection.

News Studio:

* Directly polished `NewsStudio.qml` with `PageHeader`, shared workflow stepper and compact tabs while preserving existing source/claim/brief/script/visual controllers.
* Stepper presents Sources → Claims → Script → Voice → Visuals → Export.

Story Studio:

* Directly polished `StoryStudio.qml` with the shared stepper and compact tabs while preserving the deterministic Story workflow.
* Stepper presents Idea → Outline → Script → Voice → Scenes → Export.

Translate & Dub:

* Directly polished `TranslateDubStudio.qml` with Video → Transcript → Translation → Voice → Dub → Export progression.
* Source transcript and translation remain readable side by side; existing dubbing controller and audio/timing logic are unchanged.

Shorts Maker:

* Added a focused dark surrounding canvas with centered 9:16 preview and compact Hook/Reframe/Captions/Style/Export progression.
* Existing Shorts operations remain intact.

Templates:

* Template cards are preview-first with aspect/features as secondary metadata and one clear Use action.

Assets:

* Asset cards prioritize thumbnails with compact status/favorite actions and secondary metadata.
* Asset grid keeps delegate reuse/cache buffering for large libraries and the page uses shared search/filter hierarchy.

Batch Factory:

* Added Template → Data → Mapping → Variants → Review → Run progression.
* Queue uses compact semantic rows/metrics, shared progress styling and recycled delegates instead of spreadsheet-heavy visual treatment.
* Batch input table now uses semantic surfaces/shared controls and delegate reuse.

Models:

* Existing Model Manager functionality is preserved and inherits Phase 28 cards/buttons/inputs/status palette; technical behavior was not rewritten.

Settings:

* Existing category/form structure is preserved and inherits the semantic theme and compact controls.
* Theme supports comfortable/compact density and reduced-motion preparation; no backend settings architecture was redesigned.

Dialogs:

* Shared `AppDialog` now uses dialog radius, raised semantic surface, subtle border and semantic modal scrim.
* Phase 27 Recovery dialog uses the same calm visual vocabulary and plain-language actions.

Empty states:

* Added `FriendlyEmptyState.qml` for one small icon, short title, explanation and optional primary action with no oversized decorative box.

Loading/progress:

* Added `SoftProgressBar.qml` for compact semantic progress and reused it in Batch presentation.
* No rainbow gradients or blocking decorative effects were introduced.

Hover/active states:

* Buttons/cards/navigation use subtle surface changes and clear soft selected states with visible keyboard focus.
* No glow-heavy hover effects were added.

High DPI:

* New/modified QML uses logical units and standard token sizes; no physical-pixel/device-pixel assumptions were introduced.
* Shell and major list layouts retain practical minimum sizes and elision for long names.

New files:

* `PHASE28_REPORT.md`
* `docs/PHASE28_SOFT_CREATOR_UX.md`
* `tests/test_phase28_ui_system.py`
* `ui/qml/components/FriendlyEmptyState.qml`
* `ui/qml/components/InspectorSection.qml`
* `ui/qml/components/PageHeader.qml`
* `ui/qml/components/SaveStateBadge.qml`
* `ui/qml/components/SearchField.qml`
* `ui/qml/components/SegmentTabs.qml`
* `ui/qml/components/SoftProgressBar.qml`
* `ui/qml/components/WorkflowStepper.qml`
* `ui/qml/design/DesignGallery.qml`

Modified files:

* `ui/qml/Main.qml`
* `ui/qml/theme/AnimationTokens.qml`, `Colors.qml`, `Radius.qml`, `Spacing.qml`, `Theme.qml`, `Typography.qml`, `qmldir`
* `ui/qml/components/AppButton.qml`, `AppCard.qml`, `AppDialog.qml`, `AppTextField.qml`, `LanguagePicker.qml`, `SidebarItem.qml`, `StatusBadge.qml`
* `ui/qml/assets/AssetCard.qml`, `AssetFilterBar.qml`, `AssetGrid.qml`, `AssetLibraryPage.qml`
* `ui/qml/batch/BatchFactory.qml`, `BatchInputTable.qml`, `BatchItemRow.qml`, `BatchProgress.qml`, `BatchQueue.qml`
* `ui/qml/recovery/RecoveryCard.qml`, `RecoveryDialog.qml`, `RecoveryStatus.qml`
* `ui/qml/templates/TemplateCard.qml`
* `ui/qml/timeline/TimelineEditor.qml`
* `ui/qml/shorts/ShortsStudio.qml`
* `ui/qml/news/NewsStudio.qml`
* `ui/qml/story/StoryStudio.qml`
* `ui/qml/dubbing/TranslateDubStudio.qml`

Tests run:

* Existing available baseline before Phase 28: 166/166 passed.
* Phase 28 UI-system tests: 33/33 passed.
* Cumulative available Phase 22–28 suite: 199/199 passed.
* Separate Phase 21 dubbing regression: 19/19 passed.
* QML structural/token audit: 41/41 modified/new QML files passed; all referenced Theme color/type/radius/spacing tokens resolve.
* Python compile check for Phase 28 test code passed.

Light-theme visual test:

* Static semantic-color/component/layout audit passed.
* Live rendered screenshot inspection was not executable in this sandbox because PySide6 is unavailable; no claim of manual rendered visual approval is made.

Dark-theme visual test:

* Static dark-token/editor-surface/component audit passed.
* Live rendered screenshot inspection was not executable in this sandbox because PySide6 is unavailable.

1366x768 test:

* Static responsive/minimum-size checks passed; shell minimum is 1080×700 and compact navigation/layout rules preserve the 1366×768 target.
* Live rendered window testing was unavailable without PySide6.

1920x1080 test:

* Static expanded-layout/navigation checks passed; no fixed physical-pixel assumptions were added.
* Live rendered window testing was unavailable without PySide6.

High-DPI test:

* Static logical-unit/font/icon/layout audit passed for scalable Qt usage; no devicePixelRatio hardcoding introduced.
* Windows 125/150/200% live scaling could not be launched in this sandbox.

Khmer UI test:

* Phase 28 tests include `សួស្តី ព័ត៌មានថ្មីសម្រាប់ថ្ងៃនេះ`; UTF-8 preservation, fallback tokens, line height and non-lossy source handling passed.

Thai UI test:

* Phase 28 tests include `สวัสดี วันนี้เรามีข่าวใหม่`; UTF-8 preservation, Thai fallback token and multilingual line-height checks passed.

Vietnamese UI test:

* Phase 28 tests include `Xin chào, hôm nay chúng ta có tin tức mới.`; UTF-8/diacritic-preserving source and multilingual typography checks passed.

Timeline UX test:

* Static Timeline audit passed for dark workspace tokens, readable ruler/track surfaces, retained editing wiring, selection behavior and no expensive decorative effects.

1,000-asset UI test:

* Headless structural stress fixture passed; `AssetGrid` uses `GridView`, `reuseItems: true` and cache buffering for 1,000-item scale.

1,000-item Batch UI test:

* Headless structural stress fixture passed; `BatchQueue` and Batch input list use recycled ListView delegates/cache buffers with compact rows.

Known issues:

* PySide6 and `qmllint` are not installed in this sandbox, so the actual desktop application could not be launched/captured and pixel/rendered manual visual QA could not be performed here.
* Font fallback appearance still depends on fonts installed on the target Windows machine; the existing Language Registry remains the authoritative language capability layer.
* Home/Create/Projects/Voice/Models/Settings intentionally inherit the new shared presentation layer instead of being wholesale rewritten, minimizing functional regression while providing consistent common controls.

Architecture decisions:

* Phase 28 is presentation-only QML/documentation/test work; no domain, service, repository, migration or media-engine architecture was redesigned.
* Existing controllers and workflow bindings are preserved; shared semantic components replace repeated presentation patterns.
* Compatibility token names remain available so older QML continues to render while new pages use the richer semantic token set.
* Preview/Timeline remain dark-neutral in both light/dark modes; large lists use delegate reuse and lightweight effects to protect editor performance.
* Design Gallery exists as an internal component reference and is not added to production navigation.

Recommended next phase:
Phase 29 — Cache Management

Suggested Git commit:
feat: polish MMO Video Studio with cute modern creator UX

Do not automatically begin Phase 29.

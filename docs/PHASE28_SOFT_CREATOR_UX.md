# Phase 28 — Soft Creator Studio UX/UI

## Design principles
Phase 28 keeps the existing creator workflows and business logic, but standardizes their presentation around a calm desktop editing environment: low-saturation lavender/indigo accents, neutral layered surfaces, compact typography, subtle borders, clear selection, and minimal motion. “Cute” comes from friendly spacing, corners, tiny tints and empty states rather than cartoon styling, gradients, neon or glow.

## Semantic color system
`Colors.qml` owns application colors. Feature QML should use `background`, `surface`, `surfaceRaised`, `surfaceHover`, `surfaceSelected`, `textPrimary`, `textSecondary`, `textMuted`, `textDisabled`, `border`, `borderStrong`, `focus`, accent and semantic success/warning/danger/info pairs. `previewBackground` and `timelineBackground` intentionally remain dark in both themes. Timeline clip families use muted video/audio/voice/subtitle/overlay hues.

Hardcoded colors are reserved for media/content-specific rendering, such as the white timecode over a dark thumbnail or a chroma-key sample. Feature controls should not invent local blue/white/black palettes.

## Light and dark themes
Light uses an off-white app background and slightly tinted neutral surfaces. Dark uses deep neutral gray rather than pure black. Both share the same semantic hierarchy. Primary actions are selectively accented; hover and selected states use low-saturation surfaces rather than glow.

## Typography and multilingual text
The standard UI family remains Segoe UI for Windows, with Noto Sans, Noto Sans Khmer and Noto Sans Thai documented as fallback families when available through the language/font environment. Page titles are 22 px, section titles 16 px, body 14 px, secondary 12–13 px and Timeline labels 11 px. Multilingual content uses increased line-height so Khmer combining marks, Thai marks and Vietnamese diacritics have vertical room.

## Spacing, radius and motion
Spacing follows 4/6/8/12/16/20/24/32 logical units. Radius is 7 for small controls, 10 for common controls, 12 for cards and 16 for dialogs. Motion tokens are 120/180/260 ms and become zero when `Theme.reducedMotion` is enabled. Decorative continuous animation is intentionally avoided on Timeline/large lists.

## Buttons, cards, inputs and dialogs
`AppButton` supports Primary, Secondary, Quiet/Ghost and Danger variants in compact desktop heights. `AppCard` provides shared hover/selected/focus states. `AppTextField` and `SearchField` share focus treatment; SearchField includes a clear action. `StatusBadge` uses text plus semantic color. `AppDialog` uses the dialog radius, raised surface and semantic overlay scrim so dialogs stay calm in both themes.

## Shared creator components
Phase 28 adds `PageHeader`, `WorkflowStepper`, `InspectorSection`, `SaveStateBadge`, `SoftProgressBar`, `SegmentTabs`, `SearchField`, and `FriendlyEmptyState`. They are patterns for future feature work; new pages should reuse them instead of creating local button/card/tab/status styles.

## Navigation and shell
The shell uses a compact creator sidebar with a soft active state and automatically narrows in the editor or on smaller desktop widths. The top bar stays focused: page/project title, Phase 27 save state where relevant, readiness and settings. Ctrl+S delegates to Phase 27 recovery/autosave rather than adding new serialization.

## Editor workspace and Timeline
Preview and Timeline use dedicated dark-neutral tokens in both themes so video remains visually dominant. Timeline rulers/tracks use muted surfaces and clip families. Existing Timeline commands, drag/drop and editing architecture remain unchanged; Phase 28 changes presentation only. Panels retain minimum widths so 1366×768 remains usable.

## Workflow polish
- News: uses the shared Stepper for Sources → Claims → Script → Voice → Visuals → Export; semantic review states remain icon/text/color based.
- Story: uses the same Stepper pattern with a warmer story tint and Idea → Outline → Script → Voice → Scenes → Export.
- Translate & Dub: uses Video → Transcript → Translation → Voice → Dub → Export and keeps source/target information readable side by side.
- Shorts: uses a dark centered 9:16 preview and compact Hook/Reframe/Captions/Style progression.
- Templates: thumbnail-first visual cards, aspect/features as secondary metadata, and one clear Use action.
- Assets: thumbnail-first lazy grid, compact filters/search, status hierarchy and a dedicated inspector.
- Batch: Template → Data → Mapping → Variants → Review → Run, compact summary metrics and a reused-row queue rather than spreadsheet-heavy styling.
- Recovery: calm warning-soft presentation, plain-language actions and no alarming technical wording.

## Empty/loading/progress states
Friendly empty states use one small vector icon, one short title, one explanation and at most one primary action. `SoftProgressBar` is the standard compact progress treatment. No confetti is used.

## Responsive desktop and high DPI
Layouts use logical QML units, minimum panel sizes, elision where appropriate, and tooltips for compact navigation. The shell minimum size is 1080×700, leaving the mandatory 1366×768 target usable. 1920×1080 and larger layouts get expanded navigation/content naturally. No physical-pixel or device-pixel assumptions are introduced.

## Performance rules
Grid/List views use delegate reuse/cache buffers for large Asset and Batch collections. No blur layers, shaders, glow effects or animation on hundreds of Timeline elements are introduced. The semantic theme remains lightweight property binding.

## Component reuse rule
Reuse a shared component when it represents a repeated interaction pattern. Do not abstract tiny one-off layout fragments. Backend/domain services remain untouched by Phase 28.

## Existing major pages
Home, Create, Projects, Voice Studio, Models and Settings keep their existing business bindings and layout structure but inherit the Phase 28 palette, shared buttons, cards, inputs, navigation and status treatment. This intentionally avoids a risky wholesale page rewrite while making their common controls visually consistent.

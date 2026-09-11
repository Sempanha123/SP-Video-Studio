# PHASE 14 STATUS

Completed.

## Completed:

- Offline structured AI Director foundation built on the existing project, Script, Voice, Subtitle and Scene systems
- Deterministic provider that requires no network, credentials, cloud model, web research or factual-content generation
- Typed `DirectorRequest`, `DirectorPlan`, `DirectorRecommendation` and `DirectorScenePlan` domains
- SQLite schema version 11 with persistent Director plans and normalized editable scene-plan rows
- Workflow/platform profiles, target-duration planning and source-aware project audits
- Editable/lockable recommendations with selective deterministic regeneration
- SHA-256 source fingerprints and Out-of-Date detection without deleting saved plans
- Plan history, duplicate/delete/approve/active-plan behavior and restart persistence
- Explicit safe Apply modes with settings-only default when scenes already exist
- Scene Engine integration through existing `SceneService`; no duplicate scene creation logic
- English/Khmer Unicode-safe planning metadata and reuse of existing script-duration heuristics
- Project duplication remapping for Director-owned and project-owned source references
- Modern structured Director workspace; no chatbot/conversation UI

## AI Director architecture:

- `AIDirectorService` owns plan/source/review/regeneration behavior
- `DeterministicDirectorProvider` implements the current structured Director-provider contract
- `DirectorRuleEngine` centralizes deterministic platform/workflow/duration rules
- `DirectorValidationService` validates plan structure and available Voice/Subtitle targets before apply
- `DirectorApplyService` applies approved choices through existing Project/Voice/Subtitle/Scene services
- Future LLM providers must return structured data that validates into the same Director domain; no application logic depends on unstructured chat text
- Plan schema version: 1; deterministic rule-engine version: 1.0

## Deterministic rule engine:

- Same request + same rule-engine version produces the same plan
- No randomness or fake variability is used
- Platform/workflow profiles are centralized typed configuration, not scattered QML conditionals
- Recommendations include short user-facing reasons without exposing internal rule names
- Manual News ideas produce structural guidance only and never invented facts/sources/quotes

## Supported workflows:

- `news`
- `story`
- `translate`
- `video`
- `shorts`
- Batch is intentionally not a Director creative workflow

## Platform profiles:

- TikTok
- YouTube Shorts
- Instagram Reels
- YouTube
- Facebook
- Generic
- Stable internal identifiers are stored separately from display names

## Duration planning:

- Supports 15, 30, 45, 60, 90 seconds; 2, 3, 5 minutes; and validated custom millisecond targets
- Reuses Script Analysis English speaking-rate and Khmer character-duration profiles
- Effective pace considers explicit user preference plus workflow/platform defaults
- Scene-duration distributions are deterministic, varied, positive and sum exactly to the requested target in tested profiles
- Existing scripts longer than target are audited/warned rather than destructively shortened

## Scene planning:

- Produces editable `DirectorScenePlan` rows, not real Scenes until Apply
- Hook/main/outro duration distribution varies by workflow/pace instead of one fixed duration
- Planned scene purpose, generic visual guidance, overlay guidance, transition and source ScriptSection mapping are structured
- Editing Scene Count rebuilds scene-plan rows while preserving target total duration
- Existing scenes can be audited for count/total/average duration without deletion or semantic media inspection

## Voice recommendations:

- Reuses Phase 9 Voice Studio categories such as News Anchor, Storyteller, Documentary, Professional/Educational and Energetic/Creator
- Director recommends category/style first
- Available Voice Registry entries can be queried as matches
- Actual project voice changes only when the user explicitly chooses an existing voice during Apply
- No fabricated Voice IDs and no automatic narration generation

## Subtitle recommendations:

- Reuses Phase 12 preset identifiers
- Shorts favor Creator/Bold-style captions
- News favors News/Clean
- Documentary favors Documentary/Minimal
- Translate workflow may recommend bilingual or target-language subtitle direction
- Existing subtitle tracks are never restyled automatically

## Visual/audio recommendations:

- Structured visual modes include mixed media/B-roll/stills/text-led/documentary/news-style guidance without media generation
- Project media counts can influence generic visual strategy without semantic content inspection
- Transition guidance is restrained: primarily Cut, Fade, or Crossfade
- Music guidance is conceptual (`none`, `very_low`, `low`, `medium` + style), never a copyrighted-track selection/download

## Plan review:

- Project workspace now includes **Director** beside the existing production modules
- Progressive setup covers workflow, source, platform, language, duration and creative preferences
- Saved plan history supports multiple platform/duration versions per project
- Structured Overview/Script/Scenes/Voice/Subtitles/Visuals/Audio/Transitions recommendations remain editable
- Approve and Apply are separate actions
- Readiness is structural: Ready / Needs Review / Invalid; no fake optimization score is shown

## Lock/regenerate system:

- Recommendations and planned scene rows support `locked` and `user_modified`
- Regenerate All Unlocked preserves locked/manual choices
- Category-specific regeneration supports Scenes, Voice, Subtitles and Visuals
- Deterministic regeneration does not use randomness merely to appear different
- Existing working plan is preserved until regenerated data validates
- Lightweight comparison data identifies changed recommendation values

## Apply system:

- Safe default: **Apply Settings Only**
- Optional: **Add Planned Scenes**
- Explicit destructive option: **Replace Existing Scenes**
- Existing scenes are never silently removed
- Project aspect ratio can be updated through ProjectService
- Explicit selected Voice Studio voice can become project default
- Recommended subtitle preset is stored as project preference; existing tracks are not rewritten
- Applying does not regenerate TTS, translate content, research facts or render video

## Scene Engine integration:

- Planned scenes become actual Phase 13 Scenes only through existing `SceneService`
- Maps title, duration, transition and ScriptSection relationship where available
- Generic visual description stays in Scene metadata/notes
- No renderer or QML UI state parsing is introduced
- Project duplication remaps Director Script/Transcript/Translation sources and generated plan entities to duplicated project-owned IDs where available

## Offline behavior:

- Current provider ID: `deterministic`
- Displayed as Local Director / Offline Planning
- Requires network: No
- Requires credentials: No
- Project content is never sent externally in Phase 14
- No cloud LLM provider exists in this phase

## Khmer support:

- Khmer ideas/metadata persist as Unicode through request, plan, DB and restart
- Khmer script-duration target reuses the existing Khmer character-based analysis rather than English whitespace word counting
- Khmer 60-second TikTok planning produces valid vertical aspect, scene plan and compatible voice/subtitle recommendations without encoding loss

## New files:

- `domain/director_plan.py`
- `domain/director_profile.py`
- `domain/director_recommendation.py`
- `domain/director_scene_plan.py`
- `domain/director_rules/__init__.py`
- `domain/director_rules/profiles.py`
- `engines/llm/deterministic_director.py`
- `engines/llm/errors.py`
- `engines/llm/types.py`
- `services/ai_director_service.py`
- `services/director_apply_service.py`
- `services/director_rule_engine.py`
- `services/director_validation_service.py`
- `storage/migrations/m011_create_director.py`
- `storage/repositories/director_plan_repository.py`
- `ui/controllers/ai_director_controller.py`
- `ui/qml/director/AIDirectorPage.qml`
- `ui/qml/director/DirectorApplyDialog.qml`
- `ui/qml/director/DirectorPlanReview.qml`
- `ui/qml/director/DirectorRecommendationCard.qml`
- `ui/qml/director/DirectorScenePlan.qml`
- `ui/qml/director/DirectorSetup.qml`
- `tests/test_director_phase14.py`
- `tests/test_director_qml_structure.py`
- `PHASE14_REPORT.md`

## Modified files:

- `README.md`
- `app/bootstrap.py`
- `engines/llm/base.py`
- `services/project_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- Existing migration/version regression tests updated for schema v11

## Tests run:

- Baseline before Phase 14: **305 passed, 5 skipped**
- Phase 14 focused Director/QML suite: **43 passed**
- Final full suite: **348 passed, 5 skipped**
- Expected skips remain two PySide6 live runtime/QML tests plus opt-in real VoxCPM2, faster-whisper and English↔Khmer translation integration tests
- `python -m compileall -q app domain engines media services storage ui workers`: passed
- Fresh schema-v11 bootstrap/apply smoke with a Khmer 60-second TikTok plan and Settings Only apply: passed
- `git diff --check`: passed

## 60-second Shorts test:

- Shorts + TikTok + English + 60 seconds resolves to 9:16
- Effective pace is fast/suitable for short-form
- Hook recommendation is structurally strong without inventing facts
- Subtitle recommendation favors Creator/Bold-style captions
- Scene count is reasonable and planned scene durations sum to exactly 60 seconds

## News safety test:

- News + Manual Idea creates production structure only
- No facts, sources, quotes or research claims are generated
- Plan includes the required notice that factual News Studio content will require sources later
- Apply never writes factual script content

## Story planning test:

- Story + YouTube + 3 minutes uses slower/balanced pacing than Shorts
- Scene-purpose structure includes setup/development/peak/resolution concepts
- Director does not automatically write the story itself

## Translation planning test:

- Reviewed Translation source can drive target-language planning metadata
- TikTok translation plan supports Khmer-compatible voice direction and bilingual/target subtitle recommendation
- Source timing/content is analyzed only for planning; no dubbing/TTS is generated

## Lock/regeneration test:

- Locked Aspect Ratio and Voice recommendations remain unchanged during regeneration
- Manually modified recommendations remain protected
- Selected-category regeneration changes only the requested unlocked planning section
- Same unchanged deterministic inputs reproduce the same recommendations

## Restart persistence test:

- Director plan, recommendations, planned scenes, target duration, manual edits and locks persist through SQLite restart
- Active plan persists
- Schema/rule-engine version metadata reloads intact
- Source fingerprint remains available for Out-of-Date detection

## Known issues:

- PySide6 is not installed in the packaging sandbox, so live QML runtime launch remains covered by static QML/controller tests instead of a real window launch here
- Deterministic planning is intentionally heuristic; it does not semantically understand media content or generate/research factual material
- Applying an actual voice requires the user to choose a matching existing Voice Studio profile; category recommendation alone never fabricates a voice ID
- Scene sequence preview/render precision remains Phase 13 behavior; final FFmpeg composition is intentionally deferred to Phase 15
- No cloud LLM provider or external privacy flow exists yet

## Architecture decisions:

- Director output is typed/versioned structured data, never a chat paragraph as application state
- Deterministic planning is the production Phase 14 provider so offline operation is complete and testable
- Workflow/platform/duration rules stay outside QML and controllers
- Existing ScriptAnalysisService rates are reused for English/Khmer script targets
- Recommendations and Scene plans are independently editable/lockable
- Source relationships use stable SHA-256 fingerprints; stale plans survive for review
- Approve and Apply remain separate
- Settings-only is the safe Apply default when scenes already exist
- Phase 13 SceneService is the only path used to create actual scenes from plans
- Future LLM engines must pass structured parsing/type/domain validation before their plan can be applied

## Recommended next phase:

Phase 15 — FFmpeg Rendering Engine

## Suggested Git commit:

`feat: add structured AI Director planning engine`

Do not automatically begin Phase 15.

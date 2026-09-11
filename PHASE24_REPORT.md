PHASE 24 STATUS

Completed:
* Universal local template framework for reusable project structure/style, builtin/user templates, typed components/placeholders/assets, safe create/apply/save/duplicate/delete/import/export workflows, multilingual compatibility, project independence and local usage metadata.

Template architecture:
* One Template/TemplateComponent/TemplatePlaceholder/TemplateAsset framework is shared by Project, Scene, News, Story, Short, Interview, Reporter, Subtitle, Visual Layout and Speaker Layout templates.
* Template-local IDs are mapped to fresh project-owned Scene/Speaker/Subtitle IDs when applied; runtime database IDs are not embedded in builtin structure.
* Templates are snapshots of reusable structure/style, not copied projects or live dependencies.

Builtin templates:
* 16 read-only resource templates: Clean News, Modern News, Breaking News, Reporter News, Interview News, Documentary Story, 5-Beat Story, Educational Story, Creator Short, News Short, Interview Short, Minimal Vertical Video, Minimal Landscape Video, Presenter Video, Green Screen Presenter and Translate & Dub Basic.
* Builtins are versioned JSON resources and cannot be renamed/deleted as user templates.

Project templates:
* Project settings, workflow/aspect/FPS recommendations, selected structural components and informational source-template usage/version are copied into project-owned state.
* Existing projects remain independent if the template is later deleted or updated.

Scene templates:
* Scene structure/layout components create ordinary Scene records and reuse existing overlays/layers/transitions.
* Selected-scene layout replacement snapshots the existing Scene/layers/overlays for rollback and preserves media unless the chosen template/resolution explicitly replaces it.

News templates:
* Clean/Modern/Breaking/Reporter/Interview News templates route builtin theme IDs through the existing NewsVisualService and use generic headline/lower-third placeholders plus subtitle recommendations.
* Builtin News templates contain no factual claims, source URLs or project-specific News provenance.

Story templates:
* Documentary, 5-Beat and Educational Story templates route their preset IDs through the existing StoryOutlineService; they do not invent or package Story text.

Short templates:
* Creator/News/Interview Short templates reuse Phase 23 short style metadata, 9:16 recommendations, hook placeholders, subtitle presets and existing Timeline/layer systems.

Interview templates:
* Interview News/Short structures include Interviewer and Guest roles, two voice placeholders, split-screen-compatible layer geometry, lower thirds and subtitle settings.

Reporter templates:
* Reporter News includes a Reporter speaker role, compatible voice placeholder, background-video placeholder, presenter/reporter video placeholder, headline/lower-third placeholders and 16:9/9:16 support.

Green-screen templates:
* Green Screen Presenter and Reporter News reuse Phase 22 SceneLayer/chroma settings; compatibility probes installed FFmpeg for chromakey/colorkey rather than adding a second compositor.

Subtitle integration:
* Templates reference existing Phase 12 subtitle preset IDs or copy effective project subtitle style values for reproducibility; no second SubtitleStyle registry/renderer was created.

Speaker/voice placeholders:
* Phase 22 SpeakerProfile roles are created with fresh project IDs. Voice requirements are placeholders/categories, never private reference-audio paths.
* Missing voices remain explicit Voice Setup Required warnings; multiple choices are not silently auto-selected.

Language integration:
* All language compatibility uses the Phase 22 Language Registry. Generic builtins use project language; fixed/user-select modes remain supported.
* English, Khmer, Thai, Vietnamese and other registered languages can use the same template structure without hardcoded en/km arrays.

Template browser:
* Existing global Templates page is upgraded with Unicode search, category filter, recommended/recent/name sorting, fast metadata preview, required setup display, Create from Template, Apply to Current Project, duplicate, user delete, import/export and Save Current actions.

Save as Template:
* Project capture can include Project Settings, Scene/Visual structure, Speakers, SpeechBlock structure, Subtitle Style, Short Style and Export recommendation.
* Media paths become placeholders by default. Generated narration, renders, reference-voice recordings and News claims/sources are excluded. Speech/script text is excluded unless explicitly requested.

Partial application:
* Selected component types can be applied independently. Merge preserves existing content. Apply records a local-ID → project-ID mapping and recommendations without exposing database operations.

Import/export:
* Portable `.mmovtemplate` ZIP packages contain manifest.json/template.json plus optional static preview/docs/assets.
* User templates can round-trip export/delete/import. Keep Both remaps the template ID and rewrites the local manifest consistently; Replace stages the new package before swapping the old user template.

Package security:
* Import rejects ZIP traversal/absolute paths, symlinks, duplicate entries, executable extensions, unexpected roots, oversized members/packages/uncompressed payloads, invalid JSON/schema and SHA-256 mismatches.
* Extraction is controlled member-by-member; `extractall()` and executable template logic are not used.
* Packaged reusable assets are copied through MediaService into project-managed media before template entities reference them.

Versioning:
* Template version (`1.0` default) is separate from schema version. TemplateSchemaMigrator provides the upgrade path; schemas newer than the app are rejected without partial import.

New files:
* PHASE24_REPORT.md
* docs/PHASE24_UNIVERSAL_TEMPLATE_SYSTEM.md
* app/phase24_runtime.py
* domain/template.py
* domain/template_manifest.py
* domain/template_component.py
* domain/template_placeholder.py
* domain/template_asset.py
* domain/template_errors.py
* services/template_service.py
* services/template_apply_service.py
* services/template_package_service.py
* services/template_validation_service.py
* services/template_preview_service.py
* services/template_schema_migrator.py
* storage/migrations/m021_create_templates.py
* storage/repositories/template_repository.py
* ui/controllers/template_controller.py
* ui/qml/templates/TemplateCard.qml
* ui/qml/templates/TemplatePreview.qml
* ui/qml/templates/TemplateDetails.qml
* ui/qml/templates/TemplateApplyDialog.qml
* ui/qml/templates/SaveTemplateDialog.qml
* ui/qml/templates/TemplateImportDialog.qml
* 16 builtin JSON templates under resources/templates/builtin/
* tests/test_phase24_templates.py

Modified files:
* app/paths.py
* main.py
* pyproject.toml
* storage/migrations/__init__.py
* ui/qml/pages/TemplatesPage.qml

Tests run:
* Phase 24 targeted suite: 19 passed.
* Phase 22 + Phase 23 regression: 33 passed.
* Phase 21 regression: 19 passed.
* Python compileall/py_compile: passed.
* The complete historical repository test suite could not be run because this execution environment has GitHub connector access plus phase test workspaces rather than a complete network clone.

Reporter News template test:
* Passed: multilingual structure, Reporter speaker/voice placeholder, required background/reporter media placeholders, chroma settings, headline/lower-third, subtitle recommendation, 16:9/9:16, and no factual claims/URLs.

Interview template test:
* Passed: Interviewer + Guest, two voice placeholders and 50/50 split-screen layout structure.

Khmer template test:
* Passed Language Registry compatibility and Unicode template-name/placeholder round-trip coverage; template structure does not require English-only text.

Thai template test:
* Passed Language Registry compatibility plus Thai Unicode template metadata restart persistence.

Vietnamese template test:
* Passed Vietnamese diacritics through template/package JSON round-trip and registry compatibility.

Partial-apply test:
* Passed: applying only Export Recommendation creates no Scene/Speaker entities.

Import/export test:
* Passed `.mmovtemplate` round-trip plus Keep Both ID/manifest remap.

ZIP traversal test:
* Passed: `../../evil.txt` package entry rejected.

Executable-package test:
* Passed: `.ps1` package content rejected before import.

Rollback test:
* Passed forced mid-apply failure; newly created Scene/Speaker entities are removed. Service also rolls back created subtitle tracks, imported media and selected-scene snapshots.

Restart persistence test:
* Passed SQLite/user-template reopen with Thai Unicode metadata and local usage count retained.

Known issues:
* PySide6 and qmllint are not installed in this sandbox, so full GUI runtime automation/QML lint was not executed here.
* User-template static preview generation from an active rendered frame is not automated; the browser uses a static packaged preview when available and a generic template preview otherwise.
* Complex voice choice is intentionally unresolved when multiple compatible voices exist; user selection remains required.
* Full historical test/GUI suite requires a complete local repository checkout and the user machine's PySide6/FFmpeg environment.

Architecture decisions:
* Extend Phase 23 runtime rather than replace bootstrap; reuse Project/Scene/SceneLayer/Speaker/Subtitle/Timeline/Renderer/Export systems.
* Keep builtins resource-backed and user templates app-data-backed with SQLite metadata/index only.
* Never execute code from templates; only controlled placeholder identifiers are resolved.
* Keep existing News/Story/Subtitle/Export/Voice/Short style registries authoritative and reference/copy their effective values instead of creating duplicate preset engines.
* Copy packaged assets into project-managed media and keep projects detached from installed templates after application.

Recommended next phase:
Phase 25 — Asset Library

Suggested Git commit:
feat: add universal reusable template system

Do not automatically begin Phase 25.

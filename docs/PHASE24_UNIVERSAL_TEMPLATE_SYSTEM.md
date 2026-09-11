# Phase 24 — Universal Template System

Phase 24 adds one local, reusable template framework across News, Story, Shorts, normal Video, Interview, Reporter, Presenter and Translate & Dub workflows. A template stores reusable structure/style, template-local IDs and controlled placeholders; it is not a copied project and does not create a live dependency from projects back to the installed template.

## Template model

`Template` owns typed `TemplateComponent`, `TemplatePlaceholder` and optional `TemplateAsset` records. Components reference existing systems such as Scene/SceneLayer, Subtitle presets, Export presets, SpeakerProfile/SpeechBlock, News visual recommendations, Story structure and Shorts styles. Runtime database IDs are never stored in builtin template structure. Application creates fresh project-owned IDs and maintains a local-ID → project-ID map.

Builtins are read-only JSON resources under `resources/templates/builtin/`. User templates live under `AppPaths.templates` and are indexed by SQLite migration 21. The database caches metadata/usage; the template JSON/package remains the portable source. Usage is local only and tracks last-used time/use count without telemetry.

## Placeholders and languages

Only controlled `{{identifier}}` expressions are supported. There is no Python, JavaScript, shell or eval expression execution. Placeholders cover media, video, image, audio, voice, speaker, text, logo, language, subtitle and future content roles. `{{project_language}}` is resolved from the existing Phase 22 Language Registry. Template compatibility keeps language registry membership separate from STT/TTS/translation engine capability; unsupported TTS produces Voice Setup Required rather than silently choosing another language.

## Application and project independence

TemplateApplyService applies selected components to existing authoritative services. It can create ordinary Scenes, layered media, overlays, speakers and subtitle style state while leaving Timeline/Renderer/Subtitle engines authoritative. Partial application is supported. Merge never silently deletes existing content. Selected-scene layout replacement first snapshots the Scene/layers/overlays. Application uses compensating rollback for newly created Scenes, speakers, subtitle tracks and imported packaged media.

A project created from a template receives effective project-owned values. Removing/updating the template later does not alter that project. Template usage stores informational template/version provenance only.

## Existing preset integration

Phase 24 does not replace existing registries. Subtitle components reference Phase 12 preset IDs or an effective style snapshot. Export components recommend Phase 16 preset IDs. News theme components apply through the existing NewsVisualService, Story structure components apply through StoryOutlineService, and Short components reuse Phase 23 metadata; their existing specialized services remain authoritative. Phase 22 layered video/PIP/chroma and speaker architecture are reused directly.

## Safe package format

`.mmovtemplate` is a ZIP container with `manifest.json`, `template.json`, optional static preview, optional docs and `assets/`. SHA-256 values are verified for declared payloads. Import validates member count, compressed/uncompressed size limits, duplicate names, absolute/traversal paths, symlinks and executable extensions. Extraction is member-by-member into a controlled staging folder; `extractall()` is never used. Replace import is staged before swapping the previous user template.

Reference voice recordings are never packaged by Phase 24. User project capture defaults to structure only: source videos become placeholders, generated narration/rendered outputs are excluded, SpeechBlock text is excluded unless explicitly requested, and News claims/sources are excluded.

## Builtin templates

The initial registry includes Clean News, Modern News, Breaking News, Reporter News, Interview News, Documentary Story, 5-Beat Story, Educational Story, Creator Short, News Short, Interview Short, Minimal Vertical Video, Minimal Landscape Video, Presenter Video, Green Screen Presenter and Translate & Dub Basic.

Reporter News demonstrates background/presenter placeholders, Reporter speaker and voice placeholder, chroma settings, headline/lower-third placeholders and subtitle recommendation. Interview News demonstrates two speakers/voice placeholders and split-screen structure. Creator Short demonstrates 9:16, hook placeholder, Creator captions, safe-area/track recommendations and voiceover placeholder. Builtin News templates contain no factual claims.

## Browser and save-as-template

The existing global Templates page is upgraded into the browser. It supports Unicode search/filter/sort, preview, use/create, apply-to-current, duplicate, user-template deletion, package import/export and Save Current. Creating with unresolved required media/voice is allowed and clearly remains Needs Setup, matching the manual resolve-later workflow.

Save Current captures selected project structure, Scene layouts, Speaker roles, SpeechBlock structure, effective subtitle style, Shorts style and export recommendation. Media paths are replaced by placeholders by default.

## Validation notes

Final FFmpeg render remains authoritative for chroma/layer output. Phase 24 compatibility probes the installed FFmpeg filters for `chromakey`/`colorkey` before reporting green-screen compatibility. Templates do not add a renderer, Timeline, Subtitle engine, marketplace, remote sync or executable plugin behavior.

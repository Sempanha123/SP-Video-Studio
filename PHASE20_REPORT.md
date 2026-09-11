# PHASE 20 STATUS

Complete.

## Completed:

* Added an offline-first Story Studio for `workflow=story` projects.
* Added normalized Story metadata, outlines, beats, characters, and stable production mappings.
* Added deterministic Story structure planning with duration- and pace-aware beat counts.
* Added editable/lockable/reorderable/duplicable Story beats with command-based Undo/Redo support.
* Added Story → shared Script, Voice, Scene, Subtitle, Timeline, AI Director, Render, and Export integration.
* Added English/Khmer Unicode persistence and Khmer-safe duration analysis through the existing Script analysis service.
* Added schema v17 migration and safe project duplication/deletion integration.
* No cloud story writer, AI image/video generator, music generator, or Story-specific renderer was added.

## Story architecture:

* Existing `Project` remains canonical owner; Story Studio does not create a second project system.
* Story-specific records are `StoryProjectMetadata`, `StoryOutline`, `StoryBeat`, `StoryCharacter`, and stable `story_mappings`.
* Existing ScriptSections and Scenes remain canonical production records; Story mappings only preserve idea → beat → section/scene provenance.
* Future `StoryWritingProvider` is a structured protocol only; Phase 20 ships no cloud implementation.

## Story types:

* Short Story, Documentary Story, Educational Story, Motivational Story, Mystery, Drama, Adventure, Biography-style, Explainer Story, and Custom.
* Stable internal codes are used separately from user-facing labels.
* Tone, audience, pace, emotion, and visual direction are production metadata rather than forced genre behavior.

## Outline planner:

* `DeterministicStoryPlanner` works fully offline and is repeatable for the same inputs.
* Builtin structure profiles: 5-Beat Story, Explainer, Documentary, Motivational, Mystery Short, and Educational.
* Planner returns typed Story beats plus voice-category, subtitle-preset, and visual-pacing recommendations without generating cloud content.
* Refreshing structure preserves locked/user-modified beats and retained beat IDs/mappings.

## Story beats:

* Beat fields include type, title, description, target duration, emotion, visual direction, optional chapter/character/voice references, notes, lock state, and user-modified state.
* Users can add, edit, reorder, duplicate, delete, lock, refresh, and fit beats to target duration.
* Story Beat editor exposes narrative text, type, duration, emotion, visual direction, character reference, notes, and lock state.
* Structural replacement upserts retained beat IDs instead of deleting/recreating all rows, protecting existing mappings.
* Add/edit/reorder/duplicate/delete are undoable in the in-memory command stack; undo history intentionally does not survive restart.

## Duration planning:

* 30-second planning targets 3–5 beats, 60-second planning 5–8 beats, and 3-minute planning 8–14 beats at balanced pace.
* Durations use beat-type weighting rather than equal distribution.
* `Fit to Target Duration` adjusts only unlocked beats, preserves locked durations, and preserves relative weighting with a safe duration floor.
* Script duration comparison reuses `ScriptAnalysisService`, including Khmer character-based heuristics.

## Characters:

* Lightweight StoryCharacter metadata supports Narrator, Main Character, Supporting Character, Expert, Host, and Other.
* Character records may reference existing Voice profiles; deleting Story character metadata never deletes a Voice profile.
* Multi-character automation/dialogue engines are intentionally not implemented.

## Script integration:

* `StoryScriptService` writes normal Phase 6 Script/ScriptSection records; no StoryScript domain was introduced.
* Initial mapping is one beat → one ScriptSection with stable `storyBeatId` and beat source hash metadata.
* New beats can add new sections during sync.
* Changed beats mark their linked Script section `Source Changed`; manually edited section content is preserved instead of overwritten.
* Stable mappings do not rely on matching section titles.

## Voice integration:

* Story narrator/section voices use the existing Voice Studio and narration pipeline.
* Story Voice navigation opens the existing global Voice Studio rather than a duplicate Story voice editor.
* Existing project Voice assignment is recognized as narrator state when Story Studio reloads.
* No voice is generated or cloned automatically.

## Scene integration:

* `StoryApplyService` creates ordinary Phase 13 Scenes from Story beats.
* Scene metadata stores `storyBeatId`, Story role, emotion, visual direction, source hash, and target duration context.
* Beat → Scene mappings allow future one-to-many scene expansion.
* Storyboard/Timeline scene edits remain canonical and do not silently rewrite StoryBeat target duration.

## Translation integration:

* Translation continues through the Phase 11 system; no Story-specific translation engine exists.
* Story translation context exposes the existing Story Script ID and section → beat provenance map so translated versions can retain Story relationships.

## Subtitle integration:

* Story uses the existing Subtitle Studio and Subtitle tracks/styles.
* Subtitles are optional in Story readiness; recommended styles remain production guidance only.
* No Story-specific caption renderer was added.

## AI Director integration:

* Existing AI Director is invoked with `workflow=story`.
* It receives the existing Story Script when present or the Story idea as planning context otherwise.
* Director can recommend structure/pacing/voice/subtitles/transitions but does not replace Story data automatically.

## Timeline integration:

* Story-created scenes immediately derive into the existing Phase 17 Video track through canonical Scene rows.
* There is no Story-specific Timeline track/model.
* Timeline/Storyboard timing changes therefore remain synchronized with the same Scene records.

## Khmer support:

* Story metadata, outline, beat text, character metadata, Script mappings, and SQLite persistence are Unicode-safe.
* Khmer idea/title/beat/script restart tests pass without mojibake or ASCII transliteration.
* Khmer duration estimation reuses existing ScriptAnalysisService logic instead of English whitespace word counts.

## New files:

* `domain/story_project.py`
* `domain/story_outline.py`
* `domain/story_beat.py`
* `domain/story_character.py`
* `domain/story_style.py`
* `engines/llm/story_provider.py`
* `services/story_errors.py`
* `services/story_planner.py`
* `services/story_service.py`
* `services/story_outline_service.py`
* `services/story_script_service.py`
* `services/story_apply_service.py`
* `services/story_validation_service.py`
* `storage/migrations/m017_create_story_studio.py`
* `storage/repositories/story_repository.py`
* `ui/controllers/story_controller.py`
* `ui/qml/story/StoryStudio.qml`
* `ui/qml/story/StorySetup.qml`
* `ui/qml/story/StoryOutline.qml`
* `ui/qml/story/StoryBeatCard.qml`
* `ui/qml/story/StoryCharacterPanel.qml`
* `ui/qml/story/StoryScriptBuilder.qml`
* `ui/qml/story/StoryReadiness.qml`
* `tests/test_story_phase20.py`
* `tests/test_story_qml_structure.py`
* `PHASE20_REPORT.md`

## Modified files:

* `README.md`
* `app/bootstrap.py`
* `services/project_service.py`
* `storage/migrations/__init__.py`
* `storage/repositories/__init__.py`
* `ui/qml/pages/ProjectWorkspacePage.qml`
* Existing migration-version regression tests updated from schema v16 to v17 where applicable.

## Tests run:

* Complete test coverage executed in two partitions because one monolithic pytest command exceeds this container command timeout during real FFmpeg cases.
* Normal Phase 0–20 partition: **549 passed, 3 expected skips**.
* Real FFmpeg + opt-in model integration partition: **12 passed, 4 expected skips**.
* Combined: **561 passed, 7 expected skips**.
* Expected skips: unavailable PySide6 live-runtime smokes in this container, opt-in VoxCPM2/faster-whisper/translation model tests, unavailable hardware encoder runtime, and opt-in 60-second renderer performance test.
* `python -m compileall -q app domain services storage ui/controllers engines` passed.

## 60-second Story test:

* PASS — balanced English Short Story produces a reasonable 5–8 beat outline containing Hook, Setup, Development, Climax, and Resolution.
* PASS — weighted beat durations total exactly 60,000 ms.

## Outline-lock test:

* PASS — user-modified/locked Hook survives deterministic structure refresh with the same beat ID, title, lock state, and retained production mapping.

## Duration-normalization test:

* PASS — a locked 10-second beat remains 10 seconds while unlocked beats are proportionally adjusted to bring the total back to 60 seconds.

## Script-mapping test:

* PASS — Story beats create stable linked Script sections.
* PASS — editing Beat 3 marks only its linked section Source Changed while preserving the section's manually editable content.
* PASS — newly added beats can create new Script sections during sync.

## Khmer Story test:

* PASS — Khmer idea, Story title, beat content, Script linkage, SQLite persistence, and restart loading preserve Unicode exactly.

## Project-duplication test:

* PASS — duplicated Story projects receive new outline/beat IDs and Story mappings point only to duplicated ScriptSection/Scene IDs.
* PASS — no original project-owned Story section/scene target IDs remain in duplicated mappings.

## Restart persistence test:

* PASS — Story metadata, outline, beat data, source hashes/mappings, and Khmer content reload from schema v17 SQLite state.
* Undo/Redo command history is intentionally session-only, while creative project state persists.

## Known issues:

* PySide6 is unavailable in this Linux test container, so live Qt runtime smoke tests remain skipped; Story QML receives static structure/delimiter coverage and follows existing component patterns.
* Story Beat character assignment currently accepts a stable character ID in the advanced beat editor rather than a rich picker; Character management remains available in the Story Characters panel.
* Chapter grouping is represented through optional beat `chapter_title` metadata; a separate chapter editor was not required for Phase 20.
* Multi-character dialogue automation, waveform/audio mixing, cloud story writing, AI visual generation, automatic music, lip sync, and novel-length authoring are intentionally deferred.

## Architecture decisions:

* Existing Project/Script/Voice/Scene/Subtitle/Timeline/Director/Render/Export domains remain canonical; Story adds only planning/provenance records.
* Story planning is deterministic/offline by default and never requires a cloud provider.
* Original Story idea is stored separately and is never overwritten by outline refresh.
* Beat source hashes protect user-edited Script content from silent regeneration.
* Retained beat IDs are upserted during structure refresh so production mappings survive safely.
* Beat → Scene mapping is one-to-many capable even though initial creation is one scene per beat.
* Project duplication runs Story remapping after generic Script/Scene duplication so Story mappings can target duplicated production IDs.
* Story does not introduce another renderer, storyboard, timeline, TTS engine, subtitle engine, or translation engine.

## Recommended next phase:
Phase 21 — Translate & Dub

## Suggested Git commit:
`feat: add Story Studio planning and production workflow`

Do not automatically begin Phase 21.

# PHASE 9 STATUS

## Completed:

- Replaced the Voices placeholder with a full reusable Voice Studio.
- Added versioned built-in preset registry plus persistent Designed and Reference voices.
- Added search, category/language/engine filters, favorites, recent usage, recommendations, and selection state.
- Added project default voice and per-script-section voice overrides.
- Reused the Phase 8 TTS/narration pipeline for preview, section narration, and full narration.
- Added recent narration-take playback, Set Active, and delete actions.
- Added Script workspace voice summary and Change / Use Project Voice flow.
- Added global managed voice storage and reference-voice permission flow.
- Upgraded existing databases in place to schema version 6.

## Preset voices:

- Built-ins are immutable, versioned configuration data and use fictional names only.
- Categories include News Anchor, Storyteller, Documentary, Professional, Friendly, Educational, Energetic, Calm, Conversational, and Dramatic.
- Presets carry language, style tags, VoxCPM2 design description, default friendly settings, and engine identity.

## English voices:

- James — News Anchor — Warm / Confident.
- Maya — Storyteller — Friendly / Natural.
- Oliver — Documentary — Calm / Deep.
- Sophie — Professional — Clear / Polished.
- Leo — Creator/Energetic — Bright / Energetic.

## Khmer voices:

- Sokha — News Anchor — Clear / Confident.
- Dara — Documentary — Calm / Warm.
- Sreypov — Storyteller — Friendly / Natural.
- Ratha — Professional — Clear / Neutral.
- Khmer names/descriptions and reference metadata persist as Unicode.

## Designed Voices:

- Create, edit, rename, duplicate, delete, preview, favorite, and reuse.
- Name/language/category/voice description validation.
- App-level 800-character description sanity limit.
- Friendly Pace / Energy / Tone modifiers feed VoxCPM2 design descriptions instead of fake engine parameters.
- Saving without preview remains possible when the model/runtime is unavailable.

## Reference Voices:

- Explicit “I have permission…” confirmation is required.
- Validated source is copied into the global managed Voice Library.
- Source recordings are never modified or deleted.
- Rename/metadata edit and safe reference replacement with rollback.
- Reference recordings stay local in Phase 9.

## Favorites:

- Persist independently from immutable built-in definitions.
- Favorites filter updates immediately.
- Local last-used timestamp and usage count support Recently Used sorting.

## Project voice assignment:

- `projects.default_voice_id` persists the project narration voice.
- Assignment does not automatically regenerate audio.
- Project duplication preserves the same global voice ID.
- Project deletion never deletes global voices.

## Section voice overrides:

- `script_sections.voice_override_id` persists a per-section override.
- Resolution order: section override → project default → no implicit/random voice.
- Script workspace can clear an override back to Use Project Voice.
- Section narration uses the resolved section voice; full narration uses project default.

## Preview system:

- Editable English/Khmer default preview text.
- Session preview cache keyed by voice + text + settings + model identity.
- Shared Phase 5 playback stack; no second audio player.
- Model-missing state leaves browsing available and links to Models.

## TTS integration:

- Reuses existing Phase 8 `TTSController`, `TTSService`, and `NarrationService`.
- No duplicate inference worker or VoxCPM adapter was created.
- Capability-compatible VoxCPM2 Default/Designed/Reference voice configs are produced by `VoiceService`.
- Friendly controls remain primary; CFG/steps/seed/device are secondary Advanced controls.
- Recent generated takes can be played, set active, or deleted safely.

## New files:

- `domain/voice_profile.py`
- `engines/voice_registry.py`
- `resources/voices/builtin_voices.json`
- `resources/icons/heart.svg`
- `resources/icons/heart-filled.svg`
- `services/voice_service.py`
- `storage/migrations/m006_create_voice_studio.py`
- `storage/repositories/voice_repository.py`
- `ui/controllers/voice_controller.py`
- `ui/models/voice_list_model.py`
- `tests/test_voice_phase9.py`
- `tests/test_voice_qml_structure.py`
- `PHASE9_REPORT.md`

## Modified files:

- `app/bootstrap.py`
- `app/paths.py`
- `services/narration_service.py`
- `services/project_service.py`
- `storage/migrations/__init__.py`
- `storage/repositories/__init__.py`
- `ui/controllers/tts_controller.py`
- `ui/qml/components/InfoBanner.qml`
- `ui/qml/components/VoiceCard.qml`
- `ui/qml/editor/ScriptEditor.qml`
- `ui/qml/editor/TTSPanel.qml`
- `ui/qml/pages/ProjectWorkspacePage.qml`
- `ui/qml/pages/VoicesPage.qml`
- database-version regression tests
- `README.md`

## Tests run:

- Existing Phase 0–8 suite before changes: 170 passed, 3 expected skips.
- Phase 9 focused backend/migration tests: 21 passed before final UI integration.
- Final full suite: 191 passed, 3 expected skips.
- `python -m compileall` passed for application Python packages.

## Manual checks:

- Service-level create/edit/duplicate/delete/favorite/assignment flows exercised with temporary databases/files.
- Reference consent/copy/replacement rollback behavior covered.
- Project duplication/deletion assignment behavior covered.
- Voice Studio and Script integration statically checked.
- Live Qt visual smoke is unavailable in this packaging sandbox because PySide6 is not installed.

## Khmer UX check:

- Khmer built-in presets included and prioritized for Khmer projects by deterministic recommendation sorting.
- Khmer Designed Voice names/descriptions persist through SQLite.
- Khmer preview text is provided by the Voice Service.
- Unicode storage/restart tests pass; real synthesis quality remains dependent on the Phase 8 VoxCPM runtime and should be listened to on target hardware.

## Restart persistence test:

- Favorites, Designed/Reference voices, project default voice, and section override persistence are covered by reopened-database tests.
- Global voice files remain outside project deletion lifecycle.

## Known issues:

- Live PySide6/QML runtime smoke remains skipped in this sandbox.
- Actual VoxCPM2 preview generation still requires the Phase 7 model plus a working Phase 8 VoxCPM runtime.
- Preview cache is session-local by design; persistent cross-session preview caching is deferred.
- Full-script multi-voice mixing is not implemented; Phase 9 prepares section overrides and applies them to section narration without adding speaker/dialogue automation.

## Architecture decisions:

- Built-in presets are versioned config, not database rows and not identities of real people.
- User-created voices are global reusable profiles; projects store only voice IDs.
- Reference audio stays local and managed under the application Voice Library.
- Voice assignment SQL remains in `VoiceRepository`; QML talks only to `VoiceController`/services.
- Voice Studio configures the existing Phase 8 TTS stack instead of duplicating generation logic.
- Generated audio remains immutable historical output when a voice profile later changes or is deleted.

## Recommended next phase:
Phase 10 — faster-whisper Speech-to-Text Engine

## Suggested Git commit:
`feat: add polished voice studio and reusable voice profiles`

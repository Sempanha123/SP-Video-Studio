# Phase 39 — Release QA Architecture

## Purpose

Phase 39 is a QA/release-hardening phase. It does not replace the editor, renderer, workflow services, Phase 37 security controls, or Phase 38 migrations. The suite verifies those systems together and provides repeatable profiles for developer, CI and Windows release-candidate validation.

## Test profiles

Run profiles through:

```powershell
python scripts/run_release_qa.py FAST
python scripts/run_release_qa.py INTEGRATION
python scripts/run_release_qa.py E2E
python scripts/run_release_qa.py REAL_ENGINE_OPTIONAL
python scripts/run_release_qa.py PACKAGING_SMOKE
python scripts/run_release_qa.py RELEASE
```

- **FAST** — normal developer run. Excludes integration, FFmpeg-heavy E2E, performance/fault suites, optional real models and packaging smoke.
- **INTEGRATION** — database/services, generated FFmpeg fixtures, performance sanity, fault injection, Phase 37 security and Phase 38 migration regression.
- **E2E** — mandatory deterministic creator workflows using fake AI engines and tiny generated media.
- **REAL_ENGINE_OPTIONAL** — installed VoxCPM2/Whisper/translation capability and workstation smoke. Missing large models are skips, never standard-CI failures.
- **PACKAGING_SMOKE** — pyproject/entrypoint/resources/docs/large-fixture checks in preparation for Phase 40.
- **RELEASE** — all non-huge-model automated release gates plus JUnit and privacy-safe summaries.

## Deterministic engine strategy

`tests/qa_support/fake_engines.py` provides deterministic TTS, STT, translation and Director providers. They intentionally support the release matrix (`en`, `km`, `th`, `vi`) without claiming that every real engine supports the same languages. Real-engine optional tests query actual capabilities and are opt-in.

The fake TTS writes a small standard-library WAV so downstream audio/render tests receive a real file. STT, translation and Director outputs are stable for identical inputs. Failure injection is explicit and deterministic.

## Media fixtures

`tests/qa_support/media_fixtures.py` creates media inside pytest temporary roots using argv-based `shell=False` FFmpeg calls:

- 2-second color/test video
- longer source clip for Shorts
- green-screen presenter-like synthetic video
- stereo music/tone
- mono voice-like WAV
- generated image
- Unicode subtitle fixture

No large media is committed. The mandatory software encoder is `libx264`; hardware encoders remain optional and capability-dependent.

## Database and filesystem isolation

Phase 39 helpers never discover production `AppPaths` or write user LocalAppData. Each test receives a pytest temporary root for databases, projects, renders, templates and generated media. Unicode and spaces are exercised in temporary paths. Windows-specific junction/path/non-admin checks remain part of the Windows acceptance matrix.

## E2E workflow coverage

The deterministic workflow harness covers:

1. **Normal Video** — project, media/audio/image, timeline-like events, overlay, SpeechBlock-like speech, fake TTS, subtitles, music and MP4 render.
2. **Reporter News** — source/claim/provenance, reporter speaker/voice, green-screen presenter, B-roll/chroma composition, lower-third/subtitles/music and render.
3. **Interview** — Reporter + Guest, distinct voice records, split-screen/PIP-style composition, subtitles/audio and render.
4. **Story** — story plan/beats, Narrator + Character, scenes, ambience/music, subtitles and render.
5. **Translate & Dub** — source, fake STT, deterministic translation/review, target speech/voice/timing/subtitles/audio mix and render.
6. **Shorts** — long-enough source, manual In/Out metadata, portrait reframe, hook/captions/B-roll and render.
7. **Template** — Reporter-style template application, placeholder resolution and independence after apply.
8. **Asset Library** — reusable B-roll in two projects, detach-to-local, relink and delete guard semantics.
9. **Batch Factory** — CSV rows, template/language/platform variants, fake TTS, tiny outputs and pause/resume/failure/retry.
10. **Recovery** — dirty state, simulated unclean shutdown, recovered manifest/content and post-recovery render.
11. **Migration** — realistic Phase 38 legacy fixture, migrate, Unicode edit and post-migration libx264 render.

## Multilingual matrix

English, Khmer, Thai and Vietnamese are covered for project names, scripts, speech text, subtitles, overlays, filenames, template names, asset tags and rendered-output metadata/path handling. Phase 39 also fixes project-list language labels to resolve from the shared Language Registry rather than a two-language hardcoded map.

## UI and accessibility

QML smoke tests verify major source surfaces and structural contracts when the complete QML tree is available. `qmllint` is used when installed. Phase 34 accessibility contracts for theme mode, accessible names, reduced motion, interface text sizing and keyboard/shortcut wiring remain release regressions. Live Windows click-through, Narrator and DPI checks are intentionally in `docs/manual-qa-checklist.md`; the sandbox used to build this patch has no PySide6/QML runtime.

## Performance and resource sanity

Phase 31-style checks use generous non-flaky gates for 1,000 assets, 1,000 Batch rows, 1,000 subtitle cues and 100 scenes. Resource tests cover repeated fake-engine load/unload and FFmpeg termination; the full repository profile also exercises the bounded WorkerPool/thumbnail cancellation paths where available. The purpose is regression detection, not unrealistic micro-benchmark thresholds.

## Security, migrations and fault injection

The INTEGRATION/RELEASE profiles include Phase 37 security regression and all supported Phase 38 migration fixtures. Fault injection covers disk-full-like writes, missing media/models, TTS/STT/FFmpeg failures, transaction rollback, output collision, hostile/corrupted templates, corrupted recovery payloads and malformed settings. Failures are expected to preserve original data and fail closed.

## Reports and privacy

When `SPVS_QA_REPORT_DIR` is set (the runner sets it automatically), pytest writes:

- `test-results/summary.md`
- `test-results/summary.json`
- `test-results/junit.xml` for RELEASE

The custom summary stores aggregate counts and pytest node IDs only. It does not store scripts, media paths, credentials, user project text or other private data.

## Release gate

Phase 39 automated release gate requires:

- FAST pass
- INTEGRATION pass
- mandatory E2E pass
- Phase 38 migration regression pass
- Phase 37 security regression pass
- no known P0 issue
- core `libx264` render smoke pass

Optional large-model absence does not fail standard CI. Known issues and manual Windows acceptance are tracked separately rather than hidden or endlessly rerun.

## Flaky-test policy

A flaky failure must be fixed at its root or documented with reason/owner. Profiles do not automatically rerun failures forever. Time-based assertions use broad sanity limits and deterministic inputs.

## Environment limitations of this patch build

The patch-build sandbox did not contain a complete Git checkout, PySide6/qmllint or a Windows desktop. GitHub `main` at the Phase 38 commit was used as the authoritative source baseline. Windows UI/DPI/Narrator, non-admin execution, native Unicode user-profile paths, CUDA hardware and installed huge-model inference remain explicit manual/optional acceptance items, not falsely reported as executed.

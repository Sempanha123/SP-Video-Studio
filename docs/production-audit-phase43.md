# Phase 43 — Final Production Audit

## Release decision

**NOT READY — BLOCKERS REMAIN**

Phase 43 is a feature-freeze/readiness audit, not a feature phase. No major new feature scope was added. The audited source/configuration gates have no known open P0 issue, but a release candidate is blocked by two P1 gates: the real Windows 11 x64 clean-machine/native acceptance matrix has not been executed against the final packaged artifact, and owner-approved public application/distribution terms have not been supplied. Phase 44 must not begin while either P1 remains open.

## Environment

- Authoritative baseline: GitHub `main` commit `a8ed42d207ad42b61a85e4fa0117e796820df15b` (`feat: add secure Windows update architecture`).
- Audit execution environment: Linux patch/reconstruction sandbox, Python 3.x, no Windows shell/UI, no Inno Setup, no Windows Authenticode tooling and no hardware-encoder acceptance workstation.
- A literal `git status` was not available because the sandbox has no `.git` checkout. A direct clone was attempted but the local execution environment could not resolve GitHub; authoritative repository content was therefore inspected through the GitHub connector and the Phase 42 regression reconstruction.
- Reconstructed unchanged baseline modules used only to execute regression tests are not Phase 43 deliverables and are excluded from the Phase 43 delta archive.
- Native Windows-only observations are marked **MANUAL PENDING**, never inferred from Linux/source tests.

## Feature freeze

- No new `app/phase43_runtime.py` or application feature layer.
- No new creator workflow, AI engine, renderer, updater, storage system or installer system.
- The only production-facing changes are release-readiness documentation/notices and QA/audit tooling/tests.
- One stale Phase 37 QA assertion was corrected to follow the already-shipped Phase 40 packaged entrypoint through Phase 38 to Phase 37 rather than forcing the obsolete Phase 37 direct entrypoint.

## Build

### Automated/source evidence

- Phase 40 remains the stable packaged entrypoint (`app.phase40_runtime:run`).
- Phase 40 delegates into Phase 38, which retains the Phase 37 security layer; Phase 43 does not bypass either migration or security architecture.
- Fresh reconstructed Phase 43 `PACKAGING_SMOKE`: source/configuration packaging, installer and update contracts pass.
- Fresh reconstructed Phase 43 `RELEASE`: Phase 37 security + Phase 38 migrations + Phase 39 packaging + Phase 40 packaging + Phase 41 installer + Phase 42 updates + Phase 43 audit tests pass, subject to the documented sparse-QML environment skip.
- Recorded Phase 40 full available release baseline was `247 passed, 7 skipped, 3 deselected, 0 failed`; that baseline included Phase 39 deterministic workflow E2E, multilingual, performance/resource sanity, security, migration, fault injection and software-render coverage. Phase 43 does not claim that old count is a fresh full-checkout run.

### Native release build

**MANUAL PENDING / P1 (`REL-43-001`).** This Linux environment cannot produce or validate the final Windows 11 x64 standalone build, native Qt/QML startup, actual Setup EXE lifecycle, Windows shell integration, audio playback, 200% DPI/Narrator behavior, SmartScreen/reputation, or updater-to-Inno handoff. Those must be run on the actual candidate.

## Workflows

The table separates deterministic/regression evidence from release-workstation acceptance. The Phase 39 workflow harness recorded deterministic E2E coverage for Normal Video, Reporter News, Interview, Story, Translate & Dub, Shorts, Templates, Asset Library, Batch Factory, Recovery and legacy migration-to-render. Phase 43 preserves that suite and expands the native/manual release checklist; it does not replace real-media validation with mocks.

| Audit item | Current evidence | Phase 43 result |
|---|---|---|
| 1. Clean install | Phase 40/41 source contracts + verifier scripts | **MANUAL PENDING — P1** |
| 2. First launch/onboarding | Phase 39 structural/QML contracts; Windows checklist | **MANUAL PENDING — P1 umbrella** |
| 3. Project creation | Recorded Phase 39 deterministic E2E | Automated baseline pass; native recheck pending |
| 4. Normal Video | Deterministic import/timeline/speech/subtitles/music/libx264 E2E | Automated baseline pass; real build pending |
| 5. News | Deterministic source/claim/provenance/script composition | Automated baseline pass; real build pending |
| 6. Reporter | Reporter speaker/voice/chroma/B-roll/lower-third/subtitles E2E | Automated baseline pass; visual/audio pending |
| 7. Interview | Two speakers/voices + split/PIP/subtitles/audio/render E2E | Automated baseline pass; audio pending |
| 8. Story | plan/beats/characters/scenes/audio/subtitles/render E2E | Automated baseline pass; native recheck pending |
| 9. Translate & Dub | deterministic STT/translation/review/voice/timing/mix/subtitles/render | Automated baseline pass; real engine optional/manual pending |
| 10. Shorts | range/9:16/reframe/hook/captions/B-roll/render E2E | Automated baseline pass; native recheck pending |
| 11. Speech/TTS editor | SpeechBlock path exercised; no mandatory huge model | Contract/baseline pass; real voice quality pending |
| 12. Voice Studio | Manual/optional engine path retained | Native/real-engine acceptance pending |
| 13. Subtitles | E2E + multilingual matrix | Automated baseline pass; visual clipping pending |
| 14. Timeline | E2E + Phase 31 scale sanity | Automated baseline pass; long native session pending |
| 15. Audio Mixer | E2E music/mix/ducking semantics | Manual listening pending |
| 16. Templates | apply/placeholder/independence + hostile package security | Automated baseline pass |
| 17. Assets | reuse/detach/relink/delete-guard semantics | Automated baseline pass; 1,000-item native interaction pending |
| 18. Batch Factory | CSV/template/variant/pause-resume/failure-retry E2E | Automated baseline pass; 1,000-item native interaction pending |
| 19. Recovery | dirty/unclean/recover/render + corruption safety | Automated baseline pass; process-crash native recheck pending |
| 20. Storage/cache | Phase 29 safety contracts + manual checklist | Source contract pass; native cleanup recheck pending |
| 21. Diagnostics | Phase 36/37 support-bundle/privacy contracts | Automated security/privacy pass; native UI pending |
| 22. Migration | Phase 38 regression suite and legacy migrate→render baseline | Automated pass; packaged legacy fixture pending |
| 23. Packaging | Phase 40 package contracts and release smoke | Automated pass; final binary scan pending |
| 24. Installer | Phase 41 installer contracts | Automated pass; native lifecycle pending — P1 umbrella |
| 25. Update check | Phase 42 manifest/download/checksum/cancel/active-work contracts | Automated pass; native handoff pending — P1 umbrella |
| 26. Uninstall/data preservation | Phase 41 exact managed-root boundaries | Automated contract pass; native lifecycle pending — P1 umbrella |

### Manual/offline and AI-missing behavior

The recorded Phase 39 QA design requires an offline path with manual project editing, Timeline, Speech text, imported audio, subtitles and rendering, and explicitly avoids mandatory model downloads. The Phase 43 checklist retains these gates. A clean packaged Windows offline run is still required under `REL-43-001`.

### Error handling

Phase 37/39 fault coverage is designed to fail closed for missing media/models, provider/network failures, FFmpeg failures, transaction failures, corrupt templates/recovery/settings and unsafe archive/path inputs. Phase 43 source hygiene found no new `shell=True` production path and no accidental debug `print()` beyond the intentional `--version` CLI output. Real UI error presentation must still be spot-checked on Windows so raw tracebacks never become the primary user-facing error.

## Multilingual / paths / typography

- Recorded deterministic matrix covers English, Khmer, Thai and Vietnamese project names, scripts, speech text, subtitles, overlays, filenames, template names, asset tags and rendered-output metadata/path handling.
- Phase 43 expands native acceptance for paths containing spaces, Khmer `ខ្មែរ`, Thai `ไทย`, Vietnamese `Việt`, long-path scenarios where Windows policy permits, external referenced assets, missing/relink cases and read-only targets.
- Khmer/Thai combining-mark clipping is a visual/native typography gate and is **not** claimed passed from source tests.

## Render / audio

- Software H.264 (`libx264`) remains mandatory in the QA architecture; optional hardware encoders are capability-dependent and must not replace the software fallback.
- The native candidate must verify 16:9, 9:16 and 1:1, AAC 48 kHz stereo, subtitles, chroma key, PIP, B-roll, multi-speaker composition and music ducking.
- Manual listening remains required for clear voice, ducking, clipping/fades, interview balance and dub mix. Linux/source tests cannot certify perceptual audio quality.

## Performance

- Phase 39 records Phase 31-style non-flaky scale checks for approximately 1,000 assets, 1,000 Batch rows, 1,000 subtitle cues and representative large scene/timeline workloads, plus resource lifecycle checks.
- Phase 43 introduces no runtime feature layer and found no source-level reason to reset the Phase 31 architecture.
- **MANUAL PENDING:** compare startup and interaction against the Phase 31 baseline on the same Windows workstation class; exercise 1,000 assets, 1,000 Batch items, 1,000 subtitles and 100 audio clips; run an extended edit/render/project-switch session while recording memory, threads, child processes and temp growth.
- No claim is made that long-session resource stability was measured in this sandbox.

## Recovery / storage / migrations

- Phase 27 remains the shared autosave/recovery implementation; Phase 42 uses it before update handoff instead of adding a duplicate save path.
- Phase 29 storage categories protect projects, models, recovery, assets and final exports from generic cache cleanup; update staging is separately classified and guarded.
- Phase 38 migration tests pass in the reconstructed release suite and Phase 42 post-update handling delegates to normal migration startup rather than creating a second migration engine.
- Native interruption/recovery and packaged legacy-fixture migration remain part of `REL-43-001`.

## Security

- Fresh Phase 37 security regression is included in the green Phase 43 RELEASE profile after correcting the stale entrypoint assertion.
- Source audit checks for hardcoded credential-like assignments, developer-home coupling, `shell=True`, accidental production `print()`, and unfinished release markers.
- GitHub searches for `TODO`, `FIXME` and `Lorem ipsum` returned no production blockers; local audit reviews known legitimate diagnostic/debug wording rather than deleting it blindly.
- Phase 42 update tests retain bad-checksum rejection, staging containment, cancellation, retry, HTTPS trust rules, active-work blocking and safe `shell=False` installer handoff.
- **No known open P0 security issue** was identified by the automated audit.
- Authenticode expected-publisher identity is still unconfigured and tracked as `REL-43-004` P2; if signing is required by release policy it must be completed before publication.

## Privacy

- Phase 37 support-bundle/privacy regression remains in the release suite.
- Support-bundle design excludes project/media/private reference-voice content and redacts sensitive paths/values; the Phase 43 checklist requires inspection of the generated bundle on the final candidate.
- No telemetry/online registration was added by Phase 40–43.
- Update checks are user-controlled and do not auto-download installers.
- Final native artifact/bundle inspection is required before publication; source tests do not prove that an externally staged release directory contains no private files.

## Accessibility

- Existing accessibility contracts cover theme mode, accessible names, reduced motion, interface text sizing and keyboard/shortcut wiring.
- Phase 43 checklist requires keyboard basics, visible focus, contrast/visual consistency, 1366x768, 200% DPI and Narrator spot checks on Windows.
- **MANUAL PENDING:** this environment has no Windows desktop, Narrator or native DPI scaling, so accessibility is not release-signed-off under `REL-43-001`.

## Installer

Automated Phase 41 contracts verify the stable AppId, per-user/non-elevated scope, downgrade protection, running-app protections, Start Menu/default Desktop behavior, exact managed-data removal boundary, default data preservation, SHA-256 generation and optional external signing integration.

**MANUAL PENDING / P1 umbrella:** fresh install, N→N+1 upgrade, downgrade attempt, uninstall, reinstall, default data preservation, optional managed-data removal, non-admin behavior, Unicode/spaces paths and actual running-app Restart Manager behavior must be executed using the real Setup EXE on clean Windows.

## Updates

Automated Phase 42 coverage verifies strict manifest parsing, semantic versioning, HTTPS-only production origins, redirect downgrade rejection, no command/argument fields, explicit user download/install flow, managed staging, size/SHA-256 validation, altered-installer deletion/rejection, cancellation/retry, optional signer validation, active render/Batch/migration protection, Phase 27 autosave/recovery flush and Phase 38 post-update marker behavior.

**MANUAL PENDING / P1 umbrella:** updater → actual Phase 41 Setup EXE handoff and post-upgrade restart/migration/data preservation must be executed on Windows. The official public manifest URL and expected signer are intentionally unconfigured in source; internal acceptance should use a controlled test origin.

## License / notices

`packaging/windows/notices/THIRD_PARTY_NOTICES.md` was expanded in Phase 43 into an explicit release-engineering inventory/checklist for base Python runtime packages, Qt/PySide6, the build/runtime toolchain, optional AI runtimes, FFmpeg and assets/fonts. It intentionally does not claim legal approval or invent license text.

`APPLICATION_LICENSE_NOTICE.txt` still says that owner-approved public application license terms have not been supplied. That is `REL-43-002` **P1**. The exact final binary/package inventory and corresponding license/NOTICE texts also require reconciliation on the real build (`REL-43-003`).

## Build artifact / secret audit

- Phase 43 adds `scripts/run_phase43_audit.py`, an offline source/artifact hygiene scanner.
- It rejects release-artifact entries such as `.env`, Git/test metadata, SQLite/test databases and suspicious private/test media names; it also scans textual artifact content for developer home paths and verifies ZIP CRC.
- The Phase 42 delta ZIP is not a native Release build and therefore is not substituted for the mandatory final binary/installer scan.
- **MANUAL PENDING / P1 umbrella:** run the audit (and Phase 40 verifier) against the actual standalone directory/installer staging output and inspect for credentials, test DBs, private media, source screenshots, developer paths, Git metadata and unnecessary tests before candidate sign-off.

## Known Issues

| ID | Severity | State | Release effect |
|---|---|---|---|
| `REL-43-001` | **P1** | Open | Blocks Phase 44: native clean-machine Windows production acceptance incomplete |
| `REL-43-002` | **P1** | Open | Blocks Phase 44: owner-approved public application/distribution terms missing |
| `REL-43-003` | P2 | Open | Final third-party notice inventory must match exact native artifact; promote if unresolved |
| `REL-43-004` | P2 | Open | Authenticode publisher identity/signing not configured |
| Existing QA-39/40/41/42 items | P2/P3 or superseded by above | Tracked | Remain in `docs/known-issues.md` for provenance |

**P0:** none known from automated/source audit.

## Tests / audits executed in Phase 43

- Pre-change `PACKAGING_SMOKE`: `119 passed, 18 deselected`.
- Reconstructed official RELEASE before stale-test correction: `202 passed, 1 skipped, 1 failed`; sole failure was the obsolete Phase 37 direct-entrypoint assertion.
- After correcting that QA assertion: `203 passed, 1 skipped` before adding Phase 43 tests.
- Phase 43 focused audit tests: `14 passed`.
- Phase 37 security: `63 passed`; Phase 38 migrations: `36 passed`; Phase 41 installer: `34 passed`; Phase 42 updates: `34 passed`.
- Final reconstructed `PACKAGING_SMOKE`: `118 passed, 1 skipped, 99 deselected`.
- Final reconstructed `RELEASE`: `217 passed, 1 skipped`.
- `FAST`: `99 passed, 119 deselected`. `INTEGRATION` and `E2E` select zero tests in this sparse reconstruction and return pytest no-tests-selected; they are **not** reported as passes. Recorded full Phase 40 baseline remains the evidence for those deterministic workflow suites until a complete checkout/native candidate reruns them.
- Phase 43 static/source audit: P0=0, P1=0, P2=0, P3=0 within its deterministic source scope.
- The expected skip is caused by the reconstructed sparse QML source environment, not by a runtime assertion failure.

## Release Recommendation

**NOT READY — BLOCKERS REMAIN**

Phase 43 itself may be completed as an honest audit, but the product is **not** approved to enter Phase 44 yet. Required before changing this recommendation:

1. Clear `REL-43-001` by running the expanded clean Windows 11 x64 non-admin acceptance matrix on the actual Release build/Setup EXE/update test origin, including final artifact scan and recorded logs/hashes.
2. Clear `REL-43-002` by supplying owner-approved application/public distribution terms.
3. Reconcile final third-party notices with the exact artifact (`REL-43-003`) and decide/complete the release signing policy (`REL-43-004`).
4. Rerun Phase 43 release gates and record zero open P0/P1 before beginning Phase 44.

Do **not** begin **Phase 44 — Release Candidate** until the Phase 43 release-readiness result is explicitly changed to **READY FOR RELEASE CANDIDATE**.

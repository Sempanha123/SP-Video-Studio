# Known Issues — Release QA (Phases 39–42)

Severity: **P0** data loss/security/launch failure; **P1** core workflow broken; **P2** significant with workaround; **P3** minor/polish/environmental.

There are no known open P0 or P1 issues in the automated Phase 39–42 source/configuration gates completed in the patch-build environment.

## QA-39-001 — Native Windows UI acceptance pending on release workstation

- **Severity:** P2
- **Workflow:** Desktop UI / QML / Accessibility / DPI
- **Status:** Open validation item
- **Reproduction:** Run `docs/manual-qa-checklist.md` on Windows 11 using a non-admin user, 100% and 200% scaling, Light/Dark themes, keyboard-only basics and Narrator spot checks.
- **Workaround:** Static QML/accessibility regression tests run in CI; perform the documented Windows checklist before publishing a release candidate.
- **Target fix:** Phase 39 Windows release-candidate sign-off / before Phase 40 installer release.

## QA-39-002 — Optional hardware/model smoke depends on workstation capabilities

- **Severity:** P3
- **Workflow:** VoxCPM2 / Whisper / translation / NVENC-QSV-AMF / CUDA
- **Status:** Open environment-dependent validation item
- **Reproduction:** Install/configure the relevant local model or hardware and run `python scripts/run_release_qa.py REAL_ENGINE_OPTIONAL` plus the hardware-encoder checklist.
- **Workaround:** Standard QA uses deterministic fake engines and mandatory `libx264`; no huge model is downloaded by CI.
- **Target fix:** Capability-specific release workstation validation; continue in Phase 40 packaging matrix.

## QA-39-003 — Project-list Thai/Vietnamese display labels

- **Severity:** P2
- **Workflow:** Projects / multilingual
- **Status:** Fixed in Phase 39
- **Reproduction:** Before the fix, create/open a Thai or Vietnamese project and inspect `languageName` in the project list; the controller hardcoded only English/Khmer.
- **Workaround:** None required after this patch.
- **Target fix:** Completed — project display labels now resolve through the shared Language Registry.

## QA-40-001 — Native standalone Windows artifact verification pending

- **Severity:** P2
- **Workflow:** Windows packaging / QML / clean-profile launch / no-Python runtime
- **Status:** Open validation item
- **Reproduction:** On Windows 11 x64, stage the reviewed FFmpeg package, run `scripts/build_windows.ps1 -Mode Release`, then run `scripts/verify_windows_build.ps1 -RequireInteractiveAcceptance` against `dist\MMO Video Studio`.
- **Workaround:** Phase 40 source/configuration, resource, FFmpeg-path, manifest, LocalAppData, secret-scan and package-contract tests run in the patch environment; the Windows verifier performs the native compiled checks on the target platform.
- **Target fix:** Required before treating a Phase 40 Windows binary as a public release artifact or beginning installer release sign-off.

## QA-40-002 — Unsigned Nuitka build may trigger Windows reputation warnings

- **Severity:** P3
- **Workflow:** Windows distribution / SmartScreen / antivirus reputation
- **Status:** Expected release-preparation limitation
- **Reproduction:** Build the Release folder without a configured code-signing certificate and download/copy it onto a clean Windows workstation.
- **Workaround:** Verify hashes and build manifest internally. `build_windows.ps1` supports an optional certificate-thumbprint signing step when release signing is configured outside the repository.
- **Target fix:** Phase 41 installer/signing/release preparation. Do not add obfuscation or packer tricks to suppress reputation warnings.


## QA-41-001 — Native Inno installer acceptance pending

- **Severity:** P2
- **Workflow:** Windows installer / upgrade / uninstall / non-admin
- **Status:** Open validation item
- **Reproduction:** On a disposable clean Windows 11 x64 non-admin profile, build the real Setup EXE and run `scripts/verify_windows_installer.ps1 -RequireCleanProfile -RequireNonAdmin -RequireInteractiveAcceptance`; add `-PreviousInstaller` plus `-RequireUpgradeFixture` when the previous release installer is available.
- **Workaround:** Source/configuration tests validate stable AppId, non-admin scope, downgrade guard, data-deletion boundaries, shortcuts, signing/hash wiring and verifier safety.
- **Target fix:** Required before treating the Phase 41 Setup EXE as public-release verified.

## QA-41-002 — Owner-approved application license terms not yet supplied

- **Severity:** P2 release-content/legal gate
- **Workflow:** Installer notices / public redistribution
- **Status:** Open owner decision
- **Reproduction:** Inspect `packaging/windows/notices/APPLICATION_LICENSE_NOTICE.txt`; it intentionally states that the repository does not yet contain final owner-approved public application license terms.
- **Workaround:** Internal/test builds can include the notice without implying a permissive license.
- **Target fix:** Replace the notice with, or explicitly link it to, the project owner's final license before public/commercial distribution. Third-party and FFmpeg notices remain separate.


## QA-42-001 — Official update endpoint and Authenticode publisher are not configured

- **Severity:** P2 release-security/configuration gate
- **Workflow:** Updates / signing / public release
- **Status:** Open owner/release-infrastructure item
- **Reproduction:** Inspect `app/update_config.py` or `packaging/windows/build_config.json`; the official manifest URL and expected Authenticode signer are intentionally blank.
- **Workaround:** The updater remains disabled in an unconfigured build. Internal tests use a localhost-only mock server. Do not publish an update-enabled build until the official HTTPS endpoint is controlled and, preferably, the Phase 41 installer is Authenticode-signed with the configured expected publisher.
- **Target fix:** Release-owner infrastructure/signing setup before public update rollout.

## QA-42-002 — Native Windows update round-trip acceptance pending

- **Severity:** P2
- **Workflow:** Windows update / active jobs / autosave / installer handoff / upgrade
- **Status:** Open validation item
- **Reproduction:** On a disposable Windows 11 x64 non-admin profile, install the previous signed/verified release, use a controlled HTTPS test update origin, download the next Setup EXE, confirm render/Batch blocking, autosave/recovery flush, installer launch, preserved LocalAppData, Phase 38 migration startup and final `last-update.json` marker.
- **Workaround:** Deterministic source tests cover manifest security, altered-installer rejection, cancellation, retry, staging containment, active-work blocking, autosave failure, safe argv handoff and post-update markers without touching production servers.
- **Target fix:** Required release-workstation acceptance before enabling the public manifest URL.

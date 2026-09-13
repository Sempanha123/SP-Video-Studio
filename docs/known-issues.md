# Known Issues — Phase 39 Release QA

Severity: **P0** data loss/security/launch failure; **P1** core workflow broken; **P2** significant with workaround; **P3** minor/polish/environmental.

There are no known open P0 or P1 issues in the automated Phase 39 gates completed in the patch-build environment.

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

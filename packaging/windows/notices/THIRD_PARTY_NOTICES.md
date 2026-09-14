# MMO Video Studio — third-party distribution notes

This file is a **release engineering notice index**, not legal advice and not a substitute for the exact license/copyright texts shipped by dependencies. Phase 43 does not claim legal approval. The final Windows artifact must be inventoried because the exact transitive package set can differ by build environment and enabled optional AI groups.

## Base Python/runtime packages

The application declares these direct base runtime dependencies in `pyproject.toml`:

- `PySide6` / Qt for Python
- `psutil`
- `Pillow`

The final release build must retain the license/copyright notices required by the exact versions and transitive binaries actually packaged. Do not rely on this index as the license text itself.

## Qt / PySide6

The Windows application is packaged with PySide6/Qt runtime components required by the application. Preserve the license and copyright notices supplied by the selected PySide6/Qt distribution and review the applicable Qt for Python terms for the project's distribution model. Phase 43 does not select a legal licensing model on the owner's behalf.

## Build/runtime toolchain

Phase 40 selects Python 3.11 and Nuitka for the standalone Windows build. Review the exact Python runtime, Nuitka, compiler/runtime and bundled native-library notices produced by the final build. Build tools that do not become part of the distributed artifact should not be represented as if they were bundled runtime components.

## Optional AI/runtime package groups

The project declares optional runtime groups that can include:

- `faster-whisper` and `ctranslate2`
- `voxcpm` and `soundfile`
- `transformers`, `torch` and `sentencepiece`

Model **weights are not bundled** by the Phase 40 packaging contract. If any optional runtime package is included in the release build, inventory its exact installed version and transitive native/Python dependencies and preserve all required license/copyright/NOTICE files. Do not copy a model license onto a different model/version merely because the family name is similar.

## FFmpeg / FFprobe

Phase 40 does not select or download an FFmpeg binary. The builder must stage the exact reviewed `ffmpeg.exe` and `ffprobe.exe` together with `LICENSE.txt` and `SOURCE.txt`; those files are copied into `licenses/ffmpeg/` in the standalone folder. FFmpeg licensing depends on the exact build configuration and enabled libraries. Review the staged binary/configuration and its supplied source/license information before public redistribution.

## Bundled assets and fonts

Phase 40 adds no font files and no redistributable font binaries. The application uses system font fallback/registry metadata for English, Khmer, Thai, Vietnamese and other configured languages. Any future font, icon, sample-media, template or other third-party asset added to a release must have its redistribution rights and attribution requirements independently recorded before packaging.

## Phase 43 release gate

Before a release candidate is approved:

1. Generate or otherwise record the exact file/package inventory from the actual Windows Release build.
2. Reconcile that inventory with the license/copyright/NOTICE texts shipped in the artifact.
3. Verify the exact staged FFmpeg license/source/configuration information.
4. Confirm no model weights or unreviewed third-party media/font assets were accidentally bundled.
5. Keep the owner-approved application license/distribution terms separate from third-party terms.

Uncertainty in the final binary inventory is tracked in `docs/known-issues.md` and must not be described as legal approval.

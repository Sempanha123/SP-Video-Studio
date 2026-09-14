# MMO Video Studio — third-party distribution notes

This file is a packaging checklist/notice index, not legal advice and not a substitute for the license text shipped by each dependency.

## Qt / PySide6

The Windows application is packaged with PySide6/Qt runtime components required by the application. Preserve the license notices supplied by the selected PySide6/Qt distribution and review the applicable Qt for Python licensing terms for your distribution model.

## Nuitka

Nuitka is used as the build tool. The resulting application should retain any notices required by the exact Nuitka/build-tool version and compiler/runtime components used for the build.

## FFmpeg / FFprobe

Phase 40 does not select or download an FFmpeg binary. The builder must stage the exact `ffmpeg.exe` and `ffprobe.exe` together with `LICENSE.txt` and `SOURCE.txt`. Those files are copied into `licenses/ffmpeg/` in the standalone folder. FFmpeg licensing depends on how the binary was configured and which libraries were enabled; review the staged build before public redistribution.

## AI runtimes

Model **weights are not bundled**. The application may package CPU-capable Python/native runtimes needed to use separately installed models (for example faster-whisper/CT2, VoxCPM-related runtime packages, and translation runtime packages). Keep the notices/licenses supplied with the exact packages included in a release build.

## Fonts

Phase 40 adds no font files. The application continues to use system font fallback/registry metadata for English, Khmer, Thai, Vietnamese, and other configured languages. Do not add redistributable font binaries unless their distribution rights have been independently confirmed.

# FFmpeg staging for the Windows build

Phase 40 uses a **bundled-at-build-time** strategy. MMO Video Studio never downloads FFmpeg or FFprobe silently at runtime.

Before a Release/Development/Debug build, prepare a directory containing:

- `ffmpeg.exe`
- `ffprobe.exe`
- `LICENSE.txt` — the license text/notice supplied for the exact FFmpeg build being redistributed
- `SOURCE.txt` — the exact build/source URL and build/version identification used for that binary

Pass that directory with `-FFmpegDir` or set `MMOVS_FFMPEG_DIR`.

The build script probes both executables with `-version`, copies only those two executables into `bin/`, and copies the notice/source files into `licenses/ffmpeg/`. It does not download a binary, choose a third-party distributor for you, or make a legal conclusion about a specific FFmpeg build. Review the exact FFmpeg build configuration and its applicable license obligations before public distribution.

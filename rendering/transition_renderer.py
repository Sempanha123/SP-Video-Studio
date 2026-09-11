from __future__ import annotations

from pathlib import Path

from media.ffmpeg import FFmpegRunner
from workers.cancellation import CancellationToken


class TransitionRenderer:
    """Combine normalized scene intermediates with the Phase 13 transition semantics."""

    def __init__(self, runner: FFmpegRunner) -> None:
        self.runner = runner

    def combine(
        self,
        files: list[Path],
        scenes: list[dict],
        destination: Path,
        *,
        expected_duration_ms: int,
        fps: int = 30,
        cancellation: CancellationToken | None = None,
        progress_callback=None,
    ) -> Path:
        if not files:
            raise ValueError("At least one scene file is required.")
        if len(files) == 1:
            self.runner.run(
                ["-i", str(files[0]), "-map", "0:v:0", "-map", "0:a:0", "-c", "copy", str(destination)],
                expected_duration_ms=expected_duration_ms,
                cancellation=cancellation,
                progress_callback=progress_callback,
            )
            return destination

        has_overlap = any(
            str((scene.get("transitionOut", {}) or {}).get("type", "cut")) in {"crossfade", "slide"}
            and int((scene.get("transitionOut", {}) or {}).get("durationMs", 0) or 0) > 0
            for scene in scenes[:-1]
        )
        if not has_overlap:
            manifest = destination.with_suffix(".concat.txt")
            manifest.write_text(
                "".join(f"file '{self._concat_escape(path)}'\n" for path in files),
                encoding="utf-8",
            )
            self.runner.run(
                ["-f", "concat", "-safe", "0", "-i", str(manifest), "-c", "copy", str(destination)],
                expected_duration_ms=expected_duration_ms,
                cancellation=cancellation,
                progress_callback=progress_callback,
            )
            return destination

        args: list[str] = []
        filters: list[str] = []
        for file_path in files:
            args += ["-i", str(file_path)]
        # Scene intermediates are already normalized to identical CFR/FPS, dimensions,
        # pixel format and 48 kHz stereo audio. Feeding them directly preserves the
        # frame-rate metadata required by FFmpeg's xfade filter (some FFmpeg 7 builds
        # report a 1/0 rate after an unnecessary fps/null normalization filter).
        vcur = "0:v"
        acur = "0:a"
        accumulated = int(scenes[0].get("durationMs", 0) or 0)
        for index in range(1, len(files)):
            kind, duration_ms, direction = structure(scenes[index - 1])
            overlap_ms = duration_ms if kind in {"crossfade", "slide"} else 0
            if overlap_ms > 0:
                duration = overlap_ms / 1000.0
                offset = max(0, (accumulated - overlap_ms) / 1000.0)
                transition = "fade" if kind == "crossfade" else self._slide(direction)
                vnext = f"vx{index}"
                anext = f"ax{index}"
                filters.append(
                    f"[{vcur}][{index}:v]xfade=transition={transition}:duration={duration:.6f}:"
                    f"offset={offset:.6f}[{vnext}]"
                )
                filters.append(
                    f"[{acur}][{index}:a]acrossfade=d={duration:.6f}:c1=tri:c2=tri[{anext}]"
                )
                accumulated += int(scenes[index].get("durationMs", 0) or 0) - overlap_ms
            else:
                vnext = f"vc{index}"
                anext = f"ac{index}"
                filters.append(f"[{vcur}][{index}:v]concat=n=2:v=1:a=0[{vnext}]")
                filters.append(f"[{acur}][{index}:a]concat=n=2:v=0:a=1[{anext}]")
                accumulated += int(scenes[index].get("durationMs", 0) or 0)
            vcur = vnext
            acur = anext

        self.runner.run(
            [
                *args,
                "-filter_complex",
                ";".join(filters),
                "-map",
                f"[{vcur}]",
                "-map",
                f"[{acur}]",
                "-c:v",
                "ffv1",
                "-level",
                "3",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "pcm_s16le",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(destination),
            ],
            expected_duration_ms=expected_duration_ms,
            cancellation=cancellation,
            progress_callback=progress_callback,
        )
        return destination

    @staticmethod
    def _slide(direction: str) -> str:
        return {"right": "slideright", "up": "slideup", "down": "slidedown"}.get(direction, "slideleft")

    @staticmethod
    def _concat_escape(path: Path) -> str:
        return str(path.resolve()).replace("'", "'\\''")


def structure(scene: dict) -> tuple[str, int, str]:
    transition = dict(scene.get("transitionOut", {}) or {})
    return (
        str(transition.get("type", "cut")),
        max(0, int(transition.get("durationMs", 0) or 0)),
        str(transition.get("direction", "") or ""),
    )

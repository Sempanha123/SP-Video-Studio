from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(slots=True)
class ExecutableInfo:
    available: bool
    path: str | None = None
    version: str | None = None
    error: str | None = None


class FFmpegLocator:
    def __init__(
        self,
        timeout_seconds: float = 4.0,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self._which = which

    def discover(
        self,
        ffmpeg_custom: str | None = None,
        ffprobe_custom: str | None = None,
    ) -> tuple[ExecutableInfo, ExecutableInfo]:
        ffmpeg = self._discover_one("ffmpeg", ffmpeg_custom)
        probe_hint = ffprobe_custom
        if not probe_hint and ffmpeg.available and ffmpeg.path:
            ffmpeg_path = Path(ffmpeg.path)
            sibling = ffmpeg_path.with_name(
                "ffprobe.exe" if ffmpeg_path.suffix.lower() == ".exe" else "ffprobe"
            )
            if sibling.exists():
                probe_hint = str(sibling)
        ffprobe = self._discover_one("ffprobe", probe_hint)
        return ffmpeg, ffprobe

    def validate_path(self, path: str | Path, executable_name: str) -> ExecutableInfo:
        candidate = Path(path).expanduser()
        if not candidate.exists() or not candidate.is_file():
            return ExecutableInfo(False, str(candidate), error="Executable file was not found.")
        return self._probe(candidate, executable_name)

    def _discover_one(self, executable_name: str, custom: str | None) -> ExecutableInfo:
        if custom:
            return self.validate_path(custom, executable_name)
        located = self._which(executable_name)
        if not located:
            return ExecutableInfo(False, error=f"{executable_name} was not found on PATH.")
        return self._probe(Path(located), executable_name)

    def _probe(self, path: Path, executable_name: str) -> ExecutableInfo:
        try:
            completed = subprocess.run(
                [str(path), "-version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return ExecutableInfo(False, str(path), error=str(exc))
        output = (completed.stdout or completed.stderr or "").strip()
        first_line = output.splitlines()[0] if output else ""
        if completed.returncode != 0 or executable_name.lower() not in first_line.lower():
            return ExecutableInfo(
                False,
                str(path),
                error=f"Selected file is not a working {executable_name} executable.",
            )
        version = self._extract_version(first_line, executable_name)
        return ExecutableInfo(True, str(path.resolve()), version=version)

    @staticmethod
    def _extract_version(first_line: str, executable_name: str) -> str:
        words = first_line.split()
        for index, word in enumerate(words):
            if word.lower() == "version" and index + 1 < len(words):
                return words[index + 1]
        prefix = executable_name.lower() + " version "
        lower = first_line.lower()
        if lower.startswith(prefix):
            return first_line[len(prefix):].split()[0]
        return first_line[:80] or "Unknown"

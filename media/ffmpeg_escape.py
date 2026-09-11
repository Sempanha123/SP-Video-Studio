from __future__ import annotations

from pathlib import Path


def escape_filter_path(path: str | Path) -> str:
    """Escape a filesystem path for use inside an FFmpeg filter option.

    FFmpeg's filter parser treats ':' and '\\' specially even when subprocess
    receives an argv list. Keep shell quoting out of this helper entirely.
    """
    value = str(Path(path)).replace("\\", "/")
    value = value.replace("'", r"\'")
    value = value.replace(":", r"\:")
    value = value.replace("[", r"\[").replace("]", r"\]")
    value = value.replace(",", r"\,").replace(";", r"\;")
    return value


def subtitles_filter(path: str | Path, *, fonts_dir: str | Path | None = None) -> str:
    expr = f"subtitles=filename='{escape_filter_path(path)}'"
    if fonts_dir:
        expr += f":fontsdir='{escape_filter_path(fonts_dir)}'"
    return expr

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable


class SubtitleRenderError(RuntimeError): pass


def escape_ffmpeg_subtitle_path(path: str | Path) -> str:
    value=str(Path(path)).replace('\\','/')
    value=value.replace("'", r"\'").replace(':', r'\:').replace('[',r'\[').replace(']',r'\]')
    return value


def build_subtitle_filter(subtitle_path: str | Path, fonts_dir: str | Path | None = None) -> str:
    value=f"ass='{escape_ffmpeg_subtitle_path(subtitle_path)}'"
    if fonts_dir: value+=f":fontsdir='{escape_ffmpeg_subtitle_path(fonts_dir)}'"
    return value


class SubtitlePreviewService:
    def __init__(self, ffmpeg_provider: Callable[[], str | None]) -> None: self.ffmpeg_provider=ffmpeg_provider

    def render(self, source:Path, subtitle_file:Path, destination:Path, *, start_ms:int=0, duration_ms:int=7000, fonts_dir:Path|None=None)->Path:
        ffmpeg=self.ffmpeg_provider()
        if not ffmpeg: raise SubtitleRenderError("FFmpeg is not available.")
        destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
        cmd=[ffmpeg,'-y','-ss',f'{max(0,start_ms)/1000:.3f}','-i',str(source),'-t',f'{max(500,duration_ms)/1000:.3f}','-vf',build_subtitle_filter(subtitle_file,fonts_dir),'-c:v','libx264','-preset','veryfast','-c:a','aac',str(destination)]
        try: result=subprocess.run(cmd,capture_output=True,text=True,timeout=120,shell=False)
        except (OSError,subprocess.SubprocessError) as exc: raise SubtitleRenderError("Subtitle preview render could not start.") from exc
        if result.returncode!=0 or not destination.is_file(): raise SubtitleRenderError("FFmpeg could not render the subtitle preview.")
        return destination

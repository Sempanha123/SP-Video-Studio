from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Iterable

from domain.shorts_errors import ShortSourceMissing


class ShortAudioService:
    """Assembles selected source-audio ranges without touching the original file."""
    def __init__(self, ffmpeg_path_provider: Callable[[], str | None]) -> None:
        self.ffmpeg_path_provider=ffmpeg_path_provider

    def build_command(self, source_audio: str | Path, segments: Iterable, destination: str | Path) -> list[str]:
        ffmpeg=self.ffmpeg_path_provider()
        if not ffmpeg: raise ShortSourceMissing("FFmpeg is required to assemble Short audio.")
        source=Path(source_audio)
        if not source.is_file(): raise ShortSourceMissing("The dubbed audio used by this Short is unavailable.")
        items=sorted(list(segments),key=lambda x:x.order)
        if not items: raise ShortSourceMissing("This Short has no selected audio ranges.")
        filters=[]; labels=[]
        for index,item in enumerate(items):
            start=max(0,int(item.source_start_ms))/1000.0; end=max(0,int(item.source_end_ms))/1000.0
            if end<=start: continue
            label=f"a{index}"; filters.append(f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[{label}]"); labels.append(label)
        if not labels: raise ShortSourceMissing("This Short has no valid audio ranges.")
        if len(labels)==1: filters.append(f"[{labels[0]}]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[out]")
        else:
            joined="".join(f"[{x}]" for x in labels)
            filters.append(f"{joined}concat=n={len(labels)}:v=0:a=1,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[out]")
        return [str(ffmpeg),"-hide_banner","-y","-i",str(source),"-filter_complex",";".join(filters),"-map","[out]","-ar","48000","-ac","2","-c:a","pcm_s16le",str(destination)]

    def assemble(self, source_audio: str | Path, segments: Iterable, destination: str | Path) -> Path:
        target=Path(destination); target.parent.mkdir(parents=True,exist_ok=True)
        command=self.build_command(source_audio,segments,target)
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False,shell=False)
        if result.returncode!=0 or not target.is_file() or target.stat().st_size<=0:
            detail=(result.stderr or "").strip()[-1000:]
            raise ShortSourceMissing(f"Could not assemble the dubbed Short audio. {detail}".strip())
        return target

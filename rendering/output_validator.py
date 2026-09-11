from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from media.probe import FFprobeService, MediaProbeResult
from rendering.errors import RenderOutputInvalid


@dataclass(frozen=True, slots=True)
class OutputValidation:
    probe: MediaProbeResult
    file_size: int
    duration_delta_ms: int


class OutputValidator:
    def __init__(self, probe:FFprobeService) -> None: self.probe=probe

    def validate(self,path:str|Path,*,width:int,height:int,fps:float,expected_duration_ms:int,audio_expected:bool=True)->OutputValidation:
        p=Path(path)
        if not p.is_file() or p.stat().st_size<=0: raise RenderOutputInvalid("Rendered video file is missing or empty.")
        try: result=self.probe.probe(p,expected_type="video")
        except Exception as exc: raise RenderOutputInvalid("Rendered video could not be validated with FFprobe.") from exc
        if result.width!=int(width) or result.height!=int(height): raise RenderOutputInvalid("Rendered video resolution does not match the render plan.")
        if result.fps is None or abs(float(result.fps)-float(fps))>0.6: raise RenderOutputInvalid("Rendered video frame rate does not match the render plan.")
        actual=int(result.duration_ms or 0); tolerance=max(250,round(expected_duration_ms*.01)); delta=abs(actual-expected_duration_ms)
        if expected_duration_ms>0 and delta>tolerance: raise RenderOutputInvalid("Rendered video duration differs significantly from the render plan.")
        if audio_expected and not result.audio_codec: raise RenderOutputInvalid("Rendered video is missing its expected audio stream.")
        return OutputValidation(result,p.stat().st_size,delta)

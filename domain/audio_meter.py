from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True,slots=True)
class AudioMeter:
    peak_db:float=-60.0
    rms_db:float=-60.0
    integrated_lufs:float|None=None
    clipping:bool=False

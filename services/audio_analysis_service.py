from __future__ import annotations
import json
import math
import re
import subprocess
from pathlib import Path
from domain.audio_errors import AudioAnalysisFailed
from domain.audio_meter import AudioMeter


class AudioAnalysisService:
    def __init__(self, ffmpeg_path_provider, cache_service=None, logger=None):
        self.ffmpeg_path_provider = ffmpeg_path_provider
        self.cache_service = cache_service
        self.logger = logger

    def analyze(self, path: str | Path) -> AudioMeter:
        source = Path(path)
        if not source.is_file():
            raise AudioAnalysisFailed("An audio file used by this project could not be found.")
        ffmpeg = self.ffmpeg_path_provider()
        if not ffmpeg:
            raise AudioAnalysisFailed("FFmpeg is required for audio analysis.")
        peak = self._peak(ffmpeg, source)
        lufs = self._loudness(ffmpeg, source)
        return AudioMeter(peak_db=peak, rms_db=-60.0, integrated_lufs=lufs, clipping=peak >= -0.1)

    def normalization_gain_db(self, meter: AudioMeter, target_lufs: float = -16.0, max_gain_db: float = 12.0) -> float:
        if meter.integrated_lufs is None:
            return min(max_gain_db, max(-60.0, -1.0 - meter.peak_db))
        return max(-60.0, min(max_gain_db, float(target_lufs) - float(meter.integrated_lufs)))

    def peak_normalization_gain_db(self, meter: AudioMeter, target_peak_db: float = -1.0) -> float:
        return max(-60.0, min(12.0, float(target_peak_db) - float(meter.peak_db)))

    def _peak(self, ffmpeg: str, source: Path) -> float:
        done = subprocess.run([str(ffmpeg), "-hide_banner", "-nostats", "-i", str(source), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True, shell=False, check=False, timeout=120)
        text = (done.stderr or "") + "\n" + (done.stdout or "")
        m = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", text)
        if not m:
            if done.returncode != 0:
                raise AudioAnalysisFailed("Could not analyze audio peak.")
            return -60.0
        return float(m.group(1))

    def _loudness(self, ffmpeg: str, source: Path) -> float | None:
        done = subprocess.run([str(ffmpeg), "-hide_banner", "-nostats", "-i", str(source), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True, shell=False, check=False, timeout=120)
        text = done.stderr or ""
        blocks = re.findall(r"\{[^{}]*\}", text, flags=re.S)
        for raw in reversed(blocks):
            try:
                data = json.loads(raw)
                value = data.get("input_i")
                if value not in (None, "-inf", "inf"):
                    return float(value)
            except Exception:
                continue
        return None

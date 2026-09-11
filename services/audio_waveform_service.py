from __future__ import annotations
import array
import hashlib
import json
import subprocess
import wave
from pathlib import Path
from domain.storage_category import StorageCategory


class AudioWaveformService:
    VERSION = "30.1"
    def __init__(self, cache_service, ffmpeg_path_provider=None, logger=None):
        self.cache = cache_service
        self.ffmpeg_path_provider = ffmpeg_path_provider or (lambda: None)
        self.logger = logger

    def fingerprint(self, path: str | Path) -> str:
        source = Path(path)
        stat = source.stat()
        payload = f"{source.resolve(strict=False)}|{stat.st_size}|{stat.st_mtime_ns}|{self.VERSION}"
        return hashlib.sha256(payload.encode("utf-8", "surrogatepass")).hexdigest()

    def cache_path(self, path: str | Path, buckets: int = 1200) -> Path:
        key = self.cache.stable_key("audio-waveform", self.fingerprint(path), int(buckets), version=self.VERSION)
        return self.cache.category_root(StorageCategory.AUDIO_WAVEFORM_CACHE) / f"{key}.json"

    def generate(self, path: str | Path, *, buckets: int = 1200, force: bool = False, cancellation=None) -> dict:
        source = Path(path)
        target = self.cache_path(source, buckets)
        if target.is_file() and not force:
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                if data.get("version") == self.VERSION:
                    data["cacheHit"] = True
                    return data
            except Exception:
                pass
        samples, sample_rate = self._samples(source)
        if cancellation is not None and getattr(cancellation, "is_cancelled", False):
            raise RuntimeError("Waveform generation cancelled.")
        peaks = self._bucket(samples, max(1, min(10000, int(buckets))))
        data = {"version": self.VERSION, "sourceFingerprint": self.fingerprint(source), "sampleRate": sample_rate, "buckets": peaks, "cacheHit": False}
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temp.replace(target)
        return data

    def invalidate(self, path: str | Path, *, buckets: int = 1200) -> None:
        try:self.cache_path(path, buckets).unlink(missing_ok=True)
        except OSError:pass

    def _samples(self, source: Path) -> tuple[list[int], int]:
        if source.suffix.casefold() == ".wav":
            try:
                with wave.open(str(source), "rb") as wav:
                    width = wav.getsampwidth(); channels = wav.getnchannels(); rate = wav.getframerate(); raw = wav.readframes(wav.getnframes())
                if width == 2:
                    vals = array.array("h"); vals.frombytes(raw)
                    if channels > 1: vals = array.array("h", vals[::channels])
                    return list(vals), rate
            except Exception:
                pass
        ffmpeg = self.ffmpeg_path_provider()
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required to build this waveform.")
        done = subprocess.run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(source), "-map", "0:a:0", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"], capture_output=True, shell=False, check=False, timeout=180)
        if done.returncode != 0:
            raise RuntimeError("Could not decode audio for waveform.")
        vals = array.array("h"); vals.frombytes(done.stdout)
        return list(vals), 8000

    @staticmethod
    def _bucket(samples: list[int], buckets: int) -> list[list[float]]:
        if not samples:
            return [[0.0, 0.0]]
        width = max(1, len(samples) // buckets)
        scale = 32768.0
        out = []
        for i in range(0, len(samples), width):
            chunk = samples[i:i+width]
            out.append([round(min(chunk) / scale, 5), round(max(chunk) / scale, 5)])
            if len(out) >= buckets:break
        return out

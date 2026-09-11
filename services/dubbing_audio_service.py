from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Callable, Iterable

from domain.dub_mix_settings import DubMixMode, DubMixSettings
from domain.dub_segment import DubSegment, DubTimingMode
from domain.dubbing_errors import DubAudioMixError
from services.dubbing_alignment_service import DubbingAlignmentService


class DubbingAudioService:
    """Builds reusable PCM dubbing artifacts; final video encoding remains Phase 15/16."""

    def __init__(self, ffmpeg_path_provider: Callable[[], str | None], alignment: DubbingAlignmentService | None = None) -> None:
        self.ffmpeg_path_provider = ffmpeg_path_provider
        self.alignment = alignment or DubbingAlignmentService()

    @staticmethod
    def final_mix_fingerprint(source_fingerprint: str, segments: Iterable[DubSegment], settings: DubMixSettings) -> str:
        payload = {
            "source": source_fingerprint,
            "segments": [{"id": s.id, "audio": s.generated_audio_id, "hash": s.generation_hash,
                          "start": s.effective_start_ms, "mode": s.timing_mode_code, "stretch": round(s.stretch_factor, 8)}
                         for s in sorted(segments, key=lambda x: x.order)],
            "mix": settings.to_dict(),
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def build_narration_command(self, segments: list[DubSegment], duration_ms: int, output_path: str | Path) -> list[str]:
        ffmpeg = self._ffmpeg()
        usable = [s for s in sorted(segments, key=lambda x: x.order) if s.generated_audio_path and s.generated_duration_ms > 0]
        if not usable:
            raise DubAudioMixError("No generated dub segments are available.")
        args = [ffmpeg, "-y"]
        for segment in usable:
            args += ["-i", segment.generated_audio_path]
        filters: list[str] = []
        labels: list[str] = []
        for index, segment in enumerate(usable):
            chain = ["aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo"]
            if segment.timing_mode_code == DubTimingMode.FIT_SEGMENT.value and abs(segment.stretch_factor - 1.0) > 1e-6:
                chain.extend(f"atempo={value:.8f}" for value in self.alignment.atempo_chain(segment.stretch_factor))
            chain += [f"adelay={segment.effective_start_ms}|{segment.effective_start_ms}", "apad",
                      f"atrim=duration={duration_ms / 1000.0:.6f}"]
            label = f"d{index}"
            filters.append(f"[{index}:a]{','.join(chain)}[{label}]")
            labels.append(label)
        joined = "".join(f"[{label}]" for label in labels)
        filters.append(f"{joined}amix=inputs={len(labels)}:duration=longest:normalize=0,alimiter=limit=0.95,atrim=duration={duration_ms / 1000.0:.6f}[dub]")
        return [*args, "-filter_complex", ";".join(filters), "-map", "[dub]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output_path)]

    def build_mix_command(self, source_video: str | Path, dub_track: str | Path, duration_ms: int,
                          settings: DubMixSettings, segments: list[DubSegment], output_path: str | Path) -> list[str]:
        settings.validate()
        ffmpeg = self._ffmpeg(); duration = duration_ms / 1000.0
        args = [ffmpeg, "-y", "-i", str(source_video), "-i", str(dub_track)]
        filters: list[str] = []
        filters.append(f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={settings.dub_volume:.6f},apad,atrim=duration={duration:.6f}[dub]")
        if settings.mode_code == DubMixMode.REPLACE.value:
            filters.append(f"[dub]alimiter=limit=0.95,atrim=duration={duration:.6f}[out]")
        else:
            original_volume = settings.original_volume
            if settings.mode_code == DubMixMode.DUCK.value:
                windows = [(s.effective_start_ms / 1000.0, s.effective_end_ms / 1000.0) for s in segments if s.effective_duration_ms > 0]
                if windows:
                    active = "+".join(f"between(t,{a:.6f},{b:.6f})" for a, b in windows)
                    expr = f"if(gt({active},0),{settings.duck_under_volume:.6f},{settings.duck_normal_volume:.6f})"
                    filters.append(f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume='{expr}':eval=frame,apad,atrim=duration={duration:.6f}[src]")
                else:
                    filters.append(f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={settings.duck_normal_volume:.6f},apad,atrim=duration={duration:.6f}[src]")
            else:
                filters.append(f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={original_volume:.6f},apad,atrim=duration={duration:.6f}[src]")
            filters.append(f"[src][dub]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95,atrim=duration={duration:.6f}[out]")
        return [*args, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output_path)]

    def build_narration_track(self, segments: list[DubSegment], duration_ms: int, output_path: str | Path) -> Path:
        return self._run(self.build_narration_command(segments, duration_ms, output_path), output_path)

    def build_final_mix(self, source_video: str | Path, dub_track: str | Path, duration_ms: int,
                        settings: DubMixSettings, segments: list[DubSegment], output_path: str | Path) -> Path:
        return self._run(self.build_mix_command(source_video, dub_track, duration_ms, settings, segments, output_path), output_path)

    def _run(self, command: list[str], output_path: str | Path) -> Path:
        target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        except OSError as exc:
            raise DubAudioMixError("FFmpeg could not be started.") from exc
        if result.returncode != 0 or not target.is_file() or target.stat().st_size <= 0:
            detail = (result.stderr or "").strip()[-1200:]
            raise DubAudioMixError(f"Could not build dubbed audio mix. {detail}".strip())
        return target

    def _ffmpeg(self) -> str:
        value = self.ffmpeg_path_provider()
        if not value:
            raise DubAudioMixError("FFmpeg is required to build dubbed audio.")
        return str(value)

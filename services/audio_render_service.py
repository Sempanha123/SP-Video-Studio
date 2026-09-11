from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from domain.audio_errors import AudioEffectUnavailable, AudioMixFailed
from services.audio_ducking_service import AudioDuckingService, db_to_linear


class AudioRenderService:
    """Builds the Phase 30 FFmpeg audio graph; final video encoding remains FFmpegRenderer."""

    REQUIRED_FILTERS = {
        "high_pass": "highpass",
        "low_pass": "lowpass",
        "eq": "equalizer",
        "compressor": "acompressor",
        "limiter": "alimiter",
    }

    def __init__(self, runner=None, *, cache_service=None, logger=None) -> None:
        self.runner = runner
        self.cache_service = cache_service
        self.logger = logger
        self.ducking = AudioDuckingService()

    @staticmethod
    def db_linear(db: float) -> float:
        return db_to_linear(db)

    def build_command(self, spec: dict[str, Any], output_path: str | Path, *, available_filters: set[str] | frozenset[str] | None = None) -> list[str]:
        duration_ms = max(1, int(spec.get("durationMs", 0) or 0))
        tracks = {str(x.get("id")): dict(x) for x in spec.get("tracks", [])}
        buses = {str(x.get("id")): dict(x) for x in spec.get("buses", [])}
        clips = [dict(x) for x in spec.get("clips", [])]
        effects = [dict(x) for x in spec.get("effects", [])]
        rules = [dict(x) for x in spec.get("duckingRules", []) if x.get("enabled", True)]
        master = dict(spec.get("master", {}))
        solo_ids = {tid for tid, track in tracks.items() if bool(track.get("solo")) and bool(track.get("enabled", True))}

        args: list[str] = []
        filters: list[str] = []
        track_labels: dict[str, str] = {}
        input_index = 0

        for track_id, track in tracks.items():
            if not track.get("enabled", True) or track.get("muted", False):
                continue
            if solo_ids and track_id not in solo_ids:
                continue
            bus = buses.get(str(track.get("busId") or ""))
            if bus and bus.get("muted", False):
                continue
            clip_labels = []
            for clip in clips:
                if str(clip.get("trackId") or "") != track_id or clip.get("muted", False):
                    continue
                source = str(clip.get("sourcePath") or "")
                if not source:
                    continue
                args += ["-i", source]
                label = f"c{input_index}"
                chain = self._clip_chain(clip, effects, available_filters)
                filters.append(f"[{input_index}:a]{chain}[{label}]")
                clip_labels.append(label)
                input_index += 1
            if not clip_labels:
                continue
            mixed = f"t_{self._safe_label(track_id)}"
            if len(clip_labels) == 1:
                filters.append(f"[{clip_labels[0]}]anull[{mixed}_pre]")
            else:
                joined = "".join(f"[{x}]" for x in clip_labels)
                filters.append(f"{joined}amix=inputs={len(clip_labels)}:duration=longest:normalize=0[{mixed}_pre]")
            chain = self._gain_pan_chain(float(track.get("gainDb", 0) or 0), float(track.get("pan", 0) or 0))
            chain += self._effects_chain(self._owner_effects(effects, "track", track_id), available_filters)
            filters.append(f"[{mixed}_pre]{chain}[{mixed}]")
            current = mixed
            track_rules = [r for r in rules if str(r.get("targetKind")) == "track" and str(r.get("targetId")) == track_id]
            if track_rules:
                ducked = f"d_{self._safe_label(track_id)}"
                duck_chain = "anull"
                for rule in track_rules:
                    regions = self.ducking.trigger_regions(clips, trigger_kind=str(rule.get("triggerKind") or "bus"), trigger_id=str(rule.get("triggerId") or ""), tracks=tracks)
                    if regions:
                        duck_chain += f",volume='{self.ducking.volume_expression(rule, regions)}':eval=frame"
                filters.append(f"[{current}]{duck_chain}[{ducked}]")
                current = ducked
            track_labels[track_id] = current

        # No audible clips: produce a valid silent stereo mix rather than failing final render.
        if not track_labels:
            args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            filters.append(f"[{input_index}:a]atrim=duration={duration_ms/1000.0:.6f}[master_pre]")
            master_input = "master_pre"
        else:
            # Group routed tracks through buses. Tracks without a valid bus are mixed as direct master inputs.
            bus_labels: dict[str, str] = {}
            direct: list[str] = []
            for bus_id, bus in buses.items():
                labels = [label for tid, label in track_labels.items() if str(tracks[tid].get("busId") or "") == bus_id]
                if not labels or bus.get("muted", False):
                    continue
                pre = f"b_{self._safe_label(bus_id)}_pre"
                out = f"b_{self._safe_label(bus_id)}"
                joined = "".join(f"[{x}]" for x in labels)
                if len(labels) == 1:
                    filters.append(f"[{labels[0]}]anull[{pre}]")
                else:
                    filters.append(f"{joined}amix=inputs={len(labels)}:duration=longest:normalize=0[{pre}]")
                chain = f"volume={self.db_linear(float(bus.get('gainDb',0) or 0)):.8f}"
                chain += self._effects_chain(self._owner_effects(effects, "bus", bus_id), available_filters)
                duck_exprs = []
                for rule in rules:
                    if str(rule.get("targetKind")) == "bus" and str(rule.get("targetId")) == bus_id:
                        regions = self.ducking.trigger_regions(clips, trigger_kind=str(rule.get("triggerKind") or "bus"), trigger_id=str(rule.get("triggerId") or ""), tracks=tracks)
                        if regions:
                            duck_exprs.append(self.ducking.volume_expression(rule, regions))
                for expr in duck_exprs:
                    chain += f",volume='{expr}':eval=frame"
                filters.append(f"[{pre}]{chain}[{out}]")
                bus_labels[bus_id] = out
            for track_id, label in track_labels.items():
                bus_id = str(tracks[track_id].get("busId") or "")
                if not bus_id or bus_id not in buses:
                    direct.append(label)
                # A valid muted bus intentionally consumes its tracks; never leak
                # them directly to Master when the bus is muted.
            master_sources = list(bus_labels.values()) + direct
            if not master_sources:
                args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
                filters.append(f"[{input_index}:a]atrim=duration={duration_ms/1000.0:.6f}[master_pre]")
            elif len(master_sources) == 1:
                filters.append(f"[{master_sources[0]}]anull[master_pre]")
            else:
                joined = "".join(f"[{x}]" for x in master_sources)
                filters.append(f"{joined}amix=inputs={len(master_sources)}:duration=longest:normalize=0[master_pre]")
            master_input = "master_pre"

        master_gain = float(master.get("masterGainDb", master.get("gainDb", 0)) or 0)
        master_chain = f"volume={self.db_linear(master_gain):.8f}"
        master_effects = sorted([e for e in effects if str(e.get("ownerType")) == "master" and e.get("enabled", True)], key=lambda e: (int(e.get("order", 0) or 0), str(e.get("id") or "")))
        master_chain += self._effects_chain(master_effects, available_filters)
        if bool(master.get("normalizationEnabled", False)):
            if available_filters is not None and "loudnorm" not in available_filters:
                raise AudioEffectUnavailable("This FFmpeg installation does not support loudness normalization.")
            target = float(master.get("normalizationTargetLufs", -16.0) or -16.0)
            master_chain += f",loudnorm=I={target:.2f}:TP=-1.5:LRA=11"
        if bool(master.get("limiterEnabled", True)):
            if available_filters is not None and "alimiter" not in available_filters:
                raise AudioEffectUnavailable("This FFmpeg installation does not support the master limiter.")
            limit = max(0.1, min(1.0, float(master.get("limiterLimit", 0.95) or 0.95)))
            master_chain += f",alimiter=limit={limit:.4f}:attack=5:release=50"
        master_chain += f",apad,atrim=duration={duration_ms/1000.0:.6f}"
        filters.append(f"[{master_input}]{master_chain}[mixout]")
        return [*args, "-filter_complex", ";".join(filters), "-map", "[mixout]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output_path)]

    def render_mix(self, spec: dict[str, Any], output_path: str | Path, *, cancellation=None, progress_callback=None, available_filters=None) -> Path:
        if self.runner is None:
            raise AudioMixFailed("The existing FFmpeg runner is unavailable.")
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.stem + ".partial" + target.suffix)
        temp.unlink(missing_ok=True)
        args = self.build_command(spec, temp, available_filters=available_filters)
        try:
            self.runner.run(args, expected_duration_ms=int(spec.get("durationMs", 0) or 0), cancellation=cancellation, progress_callback=progress_callback)
            if not temp.is_file() or temp.stat().st_size <= 0:
                raise AudioMixFailed("FFmpeg did not produce the audio mix.")
            temp.replace(target)
            return target
        except Exception as exc:
            temp.unlink(missing_ok=True)
            if isinstance(exc, AudioMixFailed):
                raise
            raise AudioMixFailed(f"Could not render project audio mix: {exc}") from exc

    def preview_path(self, spec: dict[str, Any], project_id: str) -> Path | None:
        if self.cache_service is None:
            return None
        from domain.storage_category import StorageCategory
        key = self.cache_service.stable_key("audio-mix-preview", self.mix_fingerprint_payload(spec), version="30.1")
        root = self.cache_service.project_category_root(StorageCategory.PREVIEW_CACHE, project_id) / "audio-mix"
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{key}.wav"

    @staticmethod
    def mix_fingerprint_payload(spec: dict[str, Any]) -> dict[str, Any]:
        return {
            "durationMs": spec.get("durationMs"),
            "tracks": spec.get("tracks", []),
            "buses": spec.get("buses", []),
            "clips": spec.get("clips", []),
            "effects": spec.get("effects", []),
            "duckingRules": spec.get("duckingRules", []),
            "master": spec.get("master", {}),
        }

    def _clip_chain(self, clip: dict[str, Any], effects: list[dict], available_filters) -> str:
        duration = max(0.001, int(clip.get("durationMs", 0) or 0) / 1000.0)
        source_in = max(0.0, int(clip.get("sourceInMs", 0) or 0) / 1000.0)
        chain = f"atrim=start={source_in:.6f}:duration={duration:.6f},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
        chain += "," + self._gain_pan_chain(float(clip.get("gainDb", 0) or 0), float(clip.get("pan", 0) or 0))
        fade_in = max(0, int(clip.get("fadeInMs", 0) or 0)) / 1000.0
        fade_out = max(0, int(clip.get("fadeOutMs", 0) or 0)) / 1000.0
        crossfade = str((clip.get("metadata") or {}).get("crossfade") or "linear")
        curve = ":curve=qsin" if crossfade == "equal_power" else ""
        if fade_in > 0:
            chain += f",afade=t=in:st=0:d={min(fade_in,duration):.6f}{curve}"
        if fade_out > 0:
            d = min(fade_out, duration)
            chain += f",afade=t=out:st={max(0.0,duration-d):.6f}:d={d:.6f}{curve}"
        chain += self._effects_chain(self._owner_effects(effects, "clip", str(clip.get("id") or "")), available_filters)
        delay = max(0, int(clip.get("timelineStartMs", 0) or 0))
        if delay:
            chain += f",adelay={delay}:all=1"
        return chain

    def _gain_pan_chain(self, gain_db: float, pan: float) -> str:
        pan = max(-1.0, min(1.0, pan))
        left = 1.0 if pan <= 0 else 1.0 - pan
        right = 1.0 if pan >= 0 else 1.0 + pan
        return f"volume={self.db_linear(gain_db):.8f},pan=stereo|c0={left:.6f}*c0|c1={right:.6f}*c1"

    @staticmethod
    def _owner_effects(effects: list[dict], owner_type: str, owner_id: str) -> list[dict]:
        return sorted(
            [e for e in effects if str(e.get("ownerType")) == owner_type and str(e.get("ownerId")) == owner_id and e.get("enabled", True)],
            key=lambda e: (int(e.get("order", 0) or 0), str(e.get("id") or "")),
        )

    def _effects_chain(self, effects: list[dict], available_filters) -> str:
        chunks = []
        for effect in effects:
            kind = str(effect.get("type") or "")
            settings = dict(effect.get("settings") or {})
            required = self.REQUIRED_FILTERS.get(kind)
            if required and available_filters is not None and required not in available_filters:
                raise AudioEffectUnavailable("This FFmpeg installation does not support this audio effect.")
            if kind == "gain":
                chunks.append(f"volume={self.db_linear(float(settings.get('gainDb',0) or 0)):.8f}")
            elif kind == "high_pass":
                chunks.append(f"highpass=f={max(20,min(1000,float(settings.get('frequency',80) or 80))):.2f}")
            elif kind == "low_pass":
                chunks.append(f"lowpass=f={max(1000,min(22000,float(settings.get('frequency',18000) or 18000))):.2f}")
            elif kind == "eq":
                low = max(-12,min(12,float(settings.get('lowDb',0) or 0)))
                mid = max(-12,min(12,float(settings.get('midDb',0) or 0)))
                high = max(-12,min(12,float(settings.get('highDb',0) or 0)))
                chunks.extend([f"equalizer=f=120:t=q:w=0.8:g={low:.2f}",f"equalizer=f=1200:t=q:w=1.0:g={mid:.2f}",f"equalizer=f=8000:t=q:w=0.8:g={high:.2f}"])
            elif kind == "compressor":
                threshold = max(0.001,min(1.0,float(settings.get('threshold',0.125) or 0.125)))
                ratio = max(1.0,min(20.0,float(settings.get('ratio',3.0) or 3.0)))
                attack = max(0.01,min(2000.0,float(settings.get('attackMs',20) or 20)))
                release = max(10.0,min(9000.0,float(settings.get('releaseMs',250) or 250)))
                makeup = self.db_linear(float(settings.get('makeupDb',0) or 0))
                chunks.append(f"acompressor=threshold={threshold:.6f}:ratio={ratio:.3f}:attack={attack:.3f}:release={release:.3f}:makeup={makeup:.6f}")
            elif kind == "limiter":
                limit = max(0.1,min(1.0,float(settings.get('limit',0.95) or 0.95)))
                chunks.append(f"alimiter=limit={limit:.4f}")
        return ("," + ",".join(chunks)) if chunks else ""

    @staticmethod
    def _safe_label(value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in value)[:40] or "audio"

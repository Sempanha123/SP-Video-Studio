from __future__ import annotations
from pathlib import Path
from domain.audio_effect import AudioEffectType


class AudioValidationService:
    SUPPORTED_EFFECTS = {x.value for x in AudioEffectType}

    def validate_mix(self, spec: dict, *, project_duration_ms: int | None = None) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []
        tracks = {str(t.get("id")): t for t in spec.get("tracks", [])}
        buses = {str(b.get("id")): b for b in spec.get("buses", [])}
        for track in tracks.values():
            if track.get("busId") and str(track.get("busId")) not in buses:
                warnings.append({"code": "missing_bus", "message": f"Track {track.get('name','')} has an invalid bus route."})
            if float(track.get("gainDb", 0) or 0) > 9:
                warnings.append({"code": "extreme_gain", "message": f"Track {track.get('name','')} has high gain."})
        audible = 0
        for clip in spec.get("clips", []):
            if not clip.get("sourcePath") or not Path(str(clip.get("sourcePath"))).exists():
                warnings.append({"code": "missing_audio", "message": "An audio file used by this project could not be found."})
            start = int(clip.get("timelineStartMs", 0) or 0)
            duration = int(clip.get("durationMs", 0) or 0)
            source_in = int(clip.get("sourceInMs", 0) or 0)
            source_out = int(clip.get("sourceOutMs", 0) or 0)
            if duration <= 0 or source_in < 0 or (source_out and source_out <= source_in):
                warnings.append({"code": "invalid_range", "message": "An audio clip has an invalid source range."})
            if project_duration_ms and start + duration > project_duration_ms + 100:
                warnings.append({"code": "outside_project", "message": "An audio clip extends beyond the project duration."})
            if not clip.get("muted"):
                audible += 1
        for effect in spec.get("effects", []):
            if effect.get("enabled", True) and str(effect.get("type")) not in self.SUPPORTED_EFFECTS:
                warnings.append({"code": "invalid_effect", "message": "The mix contains an unsupported audio effect."})
        if spec.get("clips") and audible == 0:
            warnings.append({"code": "silent_master", "message": "The current mix is silent."})
        # Conservative static clipping hint; final limiter still protects output.
        summed = sum(max(0.0, 10 ** (float(t.get("gainDb", 0) or 0) / 20.0)) for t in tracks.values() if not t.get("muted"))
        if summed > max(2.5, len(tracks) * 1.25):
            warnings.append({"code": "potential_clipping", "message": "The current mix may clip."})
        return warnings

    def require_effects(self, effects: list[dict], available_filters: set[str] | frozenset[str]) -> list[str]:
        needs = {"high_pass": "highpass", "low_pass": "lowpass", "eq": "equalizer", "compressor": "acompressor", "limiter": "alimiter"}
        missing = []
        for effect in effects:
            if not effect.get("enabled", True):
                continue
            name = needs.get(str(effect.get("type")))
            if name and name not in available_filters:
                missing.append(name)
        return sorted(set(missing))

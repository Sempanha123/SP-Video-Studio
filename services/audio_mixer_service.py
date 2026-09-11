from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path
from typing import Any

from domain.audio_bus import AudioBus, AudioBusRole
from domain.audio_effect import AudioEffectSpec
from domain.audio_mix import AudioMixSettings
from domain.audio_track import AudioTrack, AudioTrackRole
from domain.ducking_rule import DuckingRule


def linear_to_db(value: float) -> float:
    value = float(value)
    return -60.0 if value <= 0.001 else max(-60.0, min(12.0, 20.0 * math.log10(value)))


class AudioMixerService:
    """Project/timeline mixer metadata layer; it does not own a second timeline."""

    PRESETS = {
        "voice_focus": {"voice": 0.0, "dialogue": 0.0, "narration": 0.0, "music": -18.0, "sfx": -8.0, "source_audio": -10.0, "duck": -12.0},
        "interview": {"voice": 0.0, "dialogue": 0.0, "narration": 0.0, "music": -22.0, "ambience": -14.0, "source_audio": -4.0, "duck": -10.0},
        "news": {"voice": 0.0, "dialogue": 0.0, "narration": 0.0, "broll_audio": -18.0, "music": -24.0, "sfx": -10.0, "source_audio": -12.0, "duck": -12.0},
        "story": {"narration": 0.0, "dialogue": -1.0, "music": -20.0, "ambience": -18.0, "sfx": -10.0, "duck": -10.0},
        "shorts": {"voice": 0.0, "source_audio": -6.0, "music": -16.0, "sfx": -8.0, "duck": -10.0},
        "dub": {"dub": 0.0, "source_audio": -14.0, "music": -20.0, "duck": -12.0},
    }

    DEFAULT_TRACKS = {
        "video": [("Source Audio", "source_audio"), ("Voice", "voice"), ("Music", "music"), ("SFX", "sfx")],
        "news": [("Reporter / Narration", "voice"), ("Interview", "dialogue"), ("Source Audio", "source_audio"), ("B-roll Audio", "broll_audio"), ("Music", "music"), ("SFX", "sfx")],
        "story": [("Narration", "narration"), ("Character Voices", "dialogue"), ("Music", "music"), ("SFX", "sfx"), ("Ambience", "ambience")],
        "shorts": [("Source Audio", "source_audio"), ("Voice", "voice"), ("Music", "music"), ("SFX", "sfx")],
        "dub": [("Dub Voice", "dub"), ("Original Audio", "source_audio"), ("Music / Ambience", "music")],
    }

    def __init__(self, repository, *, phase22_repository=None, dubbing_repository=None, cache_service=None, timeline_service=None, media_repository=None, generated_audio_repository=None, scene_repository=None, logger=None, command_sink=None):
        self.repository = repository
        self.phase22_repository = phase22_repository
        self.dubbing_repository = dubbing_repository
        self.cache_service = cache_service
        self.timeline_service = timeline_service
        self.media_repository = media_repository
        self.generated_audio_repository = generated_audio_repository
        self.scene_repository = scene_repository
        self.logger = logger
        self.command_sink = command_sink

    def ensure_project(self, project_id: str, workflow: str = "video") -> dict[str, Any]:
        buses = self.repository.buses(project_id)
        if not buses:
            buses = [
                self.repository.save_bus(AudioBus(project_id, "Voice Bus", AudioBusRole.VOICE, 0)),
                self.repository.save_bus(AudioBus(project_id, "Music Bus", AudioBusRole.MUSIC, 1)),
                self.repository.save_bus(AudioBus(project_id, "SFX Bus", AudioBusRole.SFX, 2)),
                self.repository.save_bus(AudioBus(project_id, "Source Bus", AudioBusRole.SOURCE, 3)),
            ]
        tracks = self.repository.tracks(project_id)
        if not tracks:
            bus_by_role = {b.role_code: b.id for b in buses}
            roles = self.DEFAULT_TRACKS.get(workflow, self.DEFAULT_TRACKS["video"])
            for order, (name, role) in enumerate(roles):
                bus_role = self._bus_role_for_track(role)
                gain = self.PRESETS.get(workflow, {}).get(role, 0.0)
                track = AudioTrack(project_id, name, role, order, gain_db=gain, bus_id=bus_by_role.get(bus_role, ""))
                if role == "broll_audio" and workflow in {"news", "story"}:
                    track.muted = True
                    track.metadata["defaultMutedReason"] = "Narration-driven B-roll"
                self.repository.save_track(track)
        # Persist the default master row as soon as the mixer is initialized.
        # This makes restart state explicit without changing any legacy clip timing.
        settings = self.repository.mix_settings(project_id)
        self.repository.save_mix_settings(settings)
        return self.state(project_id)

    def state(self, project_id: str) -> dict[str, Any]:
        return {
            "projectId": project_id,
            "tracks": [x.to_dict() for x in self.repository.tracks(project_id)],
            "buses": [x.to_dict() for x in self.repository.buses(project_id)],
            "effects": [x.to_dict() for x in self.repository.effects(project_id)],
            "duckingRules": [x.to_dict() for x in self.repository.ducking_rules(project_id)],
            "master": self.repository.mix_settings(project_id).to_dict(),
        }

    def track_for_role(self, project_id: str, role: str, *, create: bool = True) -> AudioTrack | None:
        for track in self.repository.tracks(project_id):
            if track.role_code == role:
                return track
        if not create:
            return None
        buses = self.repository.buses(project_id)
        bus_role = self._bus_role_for_track(role)
        bus = next((x for x in buses if x.role_code == bus_role), None)
        track = AudioTrack(project_id, self._label_for_role(role), role, len(self.repository.tracks(project_id)), bus_id=bus.id if bus else "")
        if role == "broll_audio":
            track.muted = True
        return self.repository.save_track(track)

    def add_track(self, project_id: str, name: str, role: str = "general") -> AudioTrack:
        track = AudioTrack(project_id, name, role, len(self.repository.tracks(project_id)))
        bus_role = self._bus_role_for_track(role)
        bus = next((b for b in self.repository.buses(project_id) if b.role_code == bus_role), None)
        track.bus_id = bus.id if bus else ""
        result = self.repository.save_track(track)
        self._command("track_add", {"projectId": project_id, "id": result.id, "exists": False}, result.to_dict())
        return result

    def update_track(self, project_id: str, track_id: str, **updates) -> AudioTrack:
        track = self.repository.track(project_id, track_id)
        if track is None:
            raise KeyError("Audio track not found.")
        before = track.to_dict()
        aliases = {"gainDb": "gain_db", "busId": "bus_id"}
        for key, value in updates.items():
            attr = aliases.get(key, key)
            if attr in {"name", "role", "order", "gain_db", "pan", "muted", "solo", "enabled", "bus_id"}:
                setattr(track, attr, value)
        result = self.repository.save_track(track)
        self._command("track", before, result.to_dict())
        return result

    def set_master_gain(self, project_id: str, gain_db: float) -> AudioMixSettings:
        item = self.repository.mix_settings(project_id)
        before = item.to_dict()
        item.master_gain_db = float(gain_db)
        self.repository.save_mix_settings(item)
        self._command("master_gain", before, item.to_dict())
        return item

    def update_master(self, project_id: str, **updates) -> AudioMixSettings:
        item = self.repository.mix_settings(project_id)
        before = item.to_dict()
        if "masterGainDb" in updates: item.master_gain_db = float(updates["masterGainDb"])
        if "limiterEnabled" in updates: item.limiter_enabled = bool(updates["limiterEnabled"])
        if "limiterLimit" in updates: item.limiter_limit = float(updates["limiterLimit"])
        if "normalizationEnabled" in updates: item.normalization_enabled = bool(updates["normalizationEnabled"])
        if "normalizationTargetLufs" in updates: item.normalization_target_lufs = float(updates["normalizationTargetLufs"])
        self.repository.save_mix_settings(item)
        self._command("master_state", before, item.to_dict())
        return item

    def set_clip_mix(self, project_id: str, clip_id: str, **updates) -> dict[str, object]:
        current = self.repository.clip_mix(project_id, clip_id)
        values = dict(current)
        values.update(updates)
        result = self.repository.save_clip_mix(
            project_id,
            clip_id,
            source_kind=str(values.get("sourceKind", "timeline")),
            track_id=str(values.get("trackId", "")),
            gain_db=float(values.get("gainDb", 0) or 0),
            pan=float(values.get("pan", 0) or 0),
            fade_in_ms=int(values.get("fadeInMs", 0) or 0),
            fade_out_ms=int(values.get("fadeOutMs", 0) or 0),
            muted=bool(values.get("muted", False)),
            effects=list(values.get("effects", []) or []),
            metadata=dict(values.get("metadata", {}) or {}),
        )
        self._command("clip_mix", current, result)
        return result

    def add_effect(self, project_id: str, owner_type: str, owner_id: str, effect_type: str, settings: dict | None = None) -> AudioEffectSpec:
        order = len(self.repository.effects(project_id, owner_type, owner_id))
        item = self.repository.save_effect(project_id, AudioEffectSpec(owner_type, owner_id, effect_type, order=order, settings=dict(settings or {})))
        return item

    def update_effect(self, project_id: str, effect_id: str, *, enabled: bool | None = None, settings: dict | None = None) -> AudioEffectSpec:
        item = next((x for x in self.repository.effects(project_id) if x.id == effect_id), None)
        if item is None:
            raise KeyError("Audio effect not found.")
        if enabled is not None:
            item.enabled = bool(enabled)
        if settings is not None:
            item.settings = dict(settings)
        return self.repository.save_effect(project_id, item)

    def update_bus(self, project_id: str, bus_id: str, **updates) -> AudioBus:
        bus = self.repository.bus(project_id, bus_id)
        if bus is None:
            raise KeyError("Audio bus not found.")
        if "name" in updates: bus.name = str(updates["name"] or bus.name)
        if "gainDb" in updates: bus.gain_db = float(updates["gainDb"])
        if "muted" in updates: bus.muted = bool(updates["muted"])
        return self.repository.save_bus(bus)

    def add_voice_effect_preset(self, project_id: str, track_id: str, preset: str) -> list[AudioEffectSpec]:
        """Small conservative built-ins; never rewrites the source audio."""
        key = str(preset or "").casefold().replace(" ", "_")
        created: list[AudioEffectSpec] = []
        if key == "clear_voice":
            created.append(self.add_effect(project_id, "track", track_id, "high_pass", {"frequency": 80}))
            created.append(self.add_effect(project_id, "track", track_id, "eq", {"lowDb": -1.0, "midDb": 1.5, "highDb": 1.0}))
        elif key == "warm_voice":
            created.append(self.add_effect(project_id, "track", track_id, "high_pass", {"frequency": 65}))
            created.append(self.add_effect(project_id, "track", track_id, "eq", {"lowDb": 1.5, "midDb": 0.5, "highDb": -0.5}))
        elif key == "gentle_compressor":
            created.append(self.add_effect(project_id, "track", track_id, "compressor", {"threshold": 0.18, "ratio": 2.5, "attackMs": 20, "releaseMs": 250, "makeupDb": 1.0}))
        elif key not in {"", "off"}:
            raise ValueError("Unknown audio effect preset.")
        return created

    def set_music_ducking(self, project_id: str, enabled: bool = True, amount_db: float = -12.0, attack_ms: int = 120, release_ms: int = 220, *, record_command: bool = True) -> DuckingRule | None:
        self.ensure_project(project_id)
        before_state = self.state(project_id) if record_command else None
        voice_bus = next((b for b in self.repository.buses(project_id) if b.role_code == "voice"), None)
        music_bus = next((b for b in self.repository.buses(project_id) if b.role_code == "music"), None)
        if not voice_bus or not music_bus:
            return None
        existing = next((r for r in self.repository.ducking_rules(project_id) if r.trigger_id == voice_bus.id and r.target_id == music_bus.id), None)
        if existing is None:
            existing = DuckingRule(project_id, voice_bus.id, music_bus.id, "bus", "bus", amount_db, attack_ms, release_ms, enabled=enabled, metadata={"purpose": "voice_ducks_music"})
        else:
            existing.enabled = enabled
            existing.duck_amount_db = float(amount_db)
            existing.attack_ms = int(attack_ms)
            existing.release_ms = int(release_ms)
        saved = self.repository.save_ducking(existing)
        if record_command and before_state is not None:
            self._command("ducking", before_state, self.state(project_id))
        return saved

    def apply_preset(self, project_id: str, preset: str) -> dict[str, Any]:
        key = str(preset).casefold().replace(" ", "_")
        values = self.PRESETS.get(key)
        if values is None:
            raise ValueError("Unknown audio mixer preset.")
        self.ensure_project(project_id, key if key in self.DEFAULT_TRACKS else "video")
        before = self.state(project_id)
        for track in self.repository.tracks(project_id):
            if track.role_code in values:
                track.gain_db = float(values[track.role_code])
                self.repository.save_track(track)
        if "duck" in values:
            self.set_music_ducking(project_id, True, float(values["duck"]), record_command=False)
        settings = self.repository.mix_settings(project_id)
        settings.preset = key
        self.repository.save_mix_settings(settings)
        after = self.state(project_id)
        self._command("preset", before, after)
        return after

    def apply_dub_preset(self, project_id: str, mode: str) -> dict[str, Any]:
        self.ensure_project(project_id, "dub")
        dub = self.track_for_role(project_id, "dub")
        original = self.track_for_role(project_id, "source_audio")
        if mode == "dub_only":
            dub.gain_db, dub.muted = 0.0, False
            original.muted = True
        elif mode == "dub_quiet_original":
            dub.gain_db, dub.muted = 0.0, False
            original.gain_db, original.muted = -14.0, False
            self._ensure_duck_between_tracks(project_id, dub.id, original.id, -8.0)
        elif mode == "dub_original":
            dub.gain_db, dub.muted = 0.0, False
            original.gain_db, original.muted = 0.0, False
        else:
            raise ValueError("Unknown dub mixer preset.")
        self.repository.save_track(dub)
        self.repository.save_track(original)
        return self.state(project_id)

    def migrate_legacy_dub(self, project_id: str, legacy) -> dict[str, Any]:
        self.ensure_project(project_id, "dub")
        original = self.track_for_role(project_id, "source_audio")
        dub = self.track_for_role(project_id, "dub")
        original.gain_db = linear_to_db(float(getattr(legacy, "original_volume", legacy.get("originalVolume", 0.25) if isinstance(legacy, dict) else 0.25)))
        dub.gain_db = linear_to_db(float(getattr(legacy, "dub_volume", legacy.get("dubVolume", 1.0) if isinstance(legacy, dict) else 1.0)))
        mode = str(getattr(legacy, "mode_code", legacy.get("mode", "duck") if isinstance(legacy, dict) else "duck"))
        original.muted = mode == "replace"
        self.repository.save_track(original)
        self.repository.save_track(dub)
        if mode == "duck":
            normal = float(getattr(legacy, "duck_normal_volume", legacy.get("duckNormalVolume", 0.25) if isinstance(legacy, dict) else 0.25))
            under = float(getattr(legacy, "duck_under_volume", legacy.get("duckUnderVolume", 0.12) if isinstance(legacy, dict) else 0.12))
            amount = linear_to_db(max(0.001, under / max(0.001, normal)))
            fade = int(getattr(legacy, "duck_fade_ms", legacy.get("duckFadeMs", 120) if isinstance(legacy, dict) else 120))
            self._ensure_duck_between_tracks(project_id, dub.id, original.id, amount, fade, max(220, fade))
        settings = self.repository.mix_settings(project_id)
        settings.metadata["legacyDubMigrated"] = True
        self.repository.save_mix_settings(settings)
        return self.state(project_id)

    def ensure_legacy_migrations(self, project_id: str) -> None:
        """Lazily preserve pre-Phase30 dub behavior exactly once."""
        settings = self.repository.mix_settings(project_id)
        if settings.metadata.get("legacyDubMigrated"):
            return
        if self.dubbing_repository is None:
            return
        try:
            project = self.dubbing_repository.get_project(project_id) if hasattr(self.dubbing_repository, "get_project") else None
            if project is None:
                return
            legacy = self.dubbing_repository.get_mix_settings(project_id)
            self.migrate_legacy_dub(project_id, legacy)
        except Exception:
            if self.logger:
                self.logger.warning("Legacy dub mixer migration was skipped", exc_info=True)

    def migrate_source_audio_volume(self, project_id: str, clip_id: str, volume: float, muted: bool = False) -> dict[str, object]:
        track = self.track_for_role(project_id, "source_audio")
        return self.set_clip_mix(project_id, clip_id, trackId=track.id, gainDb=linear_to_db(float(volume)), muted=bool(muted), sourceKind="legacy_source_audio")

    def route_speaker_role(self, project_id: str, role: str) -> AudioTrack:
        normalized = str(role or "").casefold()
        if normalized in {"narrator", "narration"}:
            return self.track_for_role(project_id, "narration")
        if normalized in {"reporter", "presenter", "host"}:
            return self.track_for_role(project_id, "voice")
        if normalized in {"guest", "character", "interview", "dialogue"}:
            return self.track_for_role(project_id, "dialogue")
        return self.track_for_role(project_id, "voice")

    def asset_track_role(self, asset_subtype: str) -> str:
        subtype = str(asset_subtype or "").casefold()
        if subtype == "music": return "music"
        if subtype == "sfx": return "sfx"
        if subtype == "ambience": return "ambience"
        return "general"

    def add_asset_clip_defaults(self, project_id: str, clip_id: str, asset_subtype: str) -> dict[str, object]:
        role = self.asset_track_role(asset_subtype)
        track = self.track_for_role(project_id, role)
        return self.set_clip_mix(project_id, clip_id, trackId=track.id, sourceKind="asset_library")

    def apply_crossfade(self, first: dict, second: dict, *, equal_power: bool = True) -> tuple[dict, dict]:
        overlap = max(0, int(first.get("timelineStartMs", 0)) + int(first.get("durationMs", 0)) - int(second.get("timelineStartMs", 0)))
        if overlap <= 0:
            return first, second
        first = dict(first); second = dict(second)
        first["fadeOutMs"] = max(int(first.get("fadeOutMs", 0) or 0), overlap)
        second["fadeInMs"] = max(int(second.get("fadeInMs", 0) or 0), overlap)
        first.setdefault("metadata", {})["crossfade"] = "equal_power" if equal_power else "linear"
        second.setdefault("metadata", {})["crossfade"] = "equal_power" if equal_power else "linear"
        return first, second

    def build_mix_spec(self, project_id: str, clips: list[dict[str, Any]], duration_ms: int) -> dict[str, Any]:
        self.ensure_project(project_id)
        state = self.state(project_id)
        track_ids = {str(t["id"]) for t in state["tracks"]}
        resolved = []
        for clip in clips:
            row = dict(clip)
            mix = self.repository.clip_mix(project_id, str(row.get("id") or row.get("clipId") or ""))
            if mix.get("trackId"):
                row["trackId"] = mix["trackId"]
            if str(row.get("trackId") or "") not in track_ids:
                role = str(row.get("role") or row.get("trackRole") or "general")
                row["trackId"] = self.track_for_role(project_id, role).id
            for key in ("gainDb", "pan", "fadeInMs", "fadeOutMs", "muted"):
                if key in mix and (key not in row or mix[key] not in (0, 0.0, False)):
                    row[key] = mix[key]
            resolved.append(row)
        return {
            "schemaVersion": 1,
            "projectId": project_id,
            "durationMs": int(duration_ms),
            "tracks": state["tracks"],
            "buses": state["buses"],
            "clips": resolved,
            "effects": state["effects"],
            "duckingRules": state["duckingRules"],
            "master": state["master"],
        }

    def collect_project_clips(self, project_id: str) -> list[dict[str, Any]]:
        """Resolve existing Timeline clip timing into mixer-ready audio DTOs.

        Timeline/Scene/SpeechBlock/manual-audio records remain authoritative; this
        method never creates a second audio timeline and never rewrites sources.
        """
        if self.timeline_service is None:
            return []
        try:
            loaded = self.timeline_service.load(project_id)
        except Exception:
            if self.logger:
                self.logger.warning("Could not derive Timeline audio clips for mixer", exc_info=True)
            return []
        by_type = dict(loaded.get("clips", {}) or {})
        result: list[dict[str, Any]] = []
        for timeline_role in ("voice", "source_audio", "music", "sfx"):
            for item in list(by_type.get(timeline_role, []) or []):
                raw = item.to_dict() if hasattr(item, "to_dict") else dict(item)
                source_kind = str(raw.get("sourceType") or raw.get("source_type") or "")
                source_ref = str(raw.get("sourceRefId") or raw.get("source_ref_id") or raw.get("sourceId") or "")
                metadata = dict(raw.get("metadata") or {})
                source_path = self._resolve_source_path(project_id, source_kind, source_ref, metadata)
                if not source_path:
                    continue
                role = self._role_for_timeline_clip(timeline_role, source_kind, metadata)
                track = self.track_for_role(project_id, role)
                base_volume = float(metadata.get("volume", 1.0) or 0.0)
                result.append({
                    "id": str(raw.get("id") or raw.get("clipId") or f"{source_kind}:{source_ref}"),
                    "trackId": track.id,
                    "role": role,
                    "sourcePath": source_path,
                    "timelineStartMs": int(raw.get("timelineStartMs", raw.get("startMs", 0)) or 0),
                    "durationMs": max(1, int(raw.get("durationMs", 1) or 1)),
                    "sourceInMs": max(0, int(raw.get("sourceInMs", 0) or 0)),
                    "sourceOutMs": max(0, int(raw.get("sourceOutMs") or 0)),
                    "gainDb": linear_to_db(base_volume),
                    "pan": 0.0,
                    "fadeInMs": max(0, int(metadata.get("fadeInMs", 0) or 0)),
                    "fadeOutMs": max(0, int(metadata.get("fadeOutMs", 0) or 0)),
                    "muted": bool(raw.get("muted", False) or not bool(raw.get("enabled", True))),
                    "speakerName": str(metadata.get("speakerName") or raw.get("label") or ""),
                    "language": str(metadata.get("language") or ""),
                    "metadata": {**metadata, "timelineSourceType": source_kind},
                })
        # Phase 22 multi-speaker blocks keep their existing Speaker/SpeechBlock IDs
        # and are only projected into track/routing DTOs here.
        result.extend(self._speech_block_clips(project_id, result))
        # Legacy/current Dub projects are projected into the generic Dub track.
        result.extend(self._legacy_dub_clips(project_id, result))
        return result

    def build_project_mix_spec(self, project_id: str, duration_ms: int) -> dict[str, Any]:
        self.ensure_legacy_migrations(project_id)
        return self.build_mix_spec(project_id, self.collect_project_clips(project_id), duration_ms)

    def apply_template_settings(self, project_id: str, settings: dict[str, Any] | None) -> dict[str, Any]:
        """Apply ID-free Phase 24/26 mixer settings using semantic roles."""
        data = dict(settings or {})
        self.ensure_project(project_id)
        buses_by_role = {b.role_code: b for b in self.repository.buses(project_id)}
        for row in list(data.get("buses", []) or []):
            role = str(row.get("role") or "general")
            bus = buses_by_role.get(role)
            if bus is None:
                bus = AudioBus(project_id, str(row.get("name") or role.replace("_", " ").title()), role, len(buses_by_role))
            bus.name = str(row.get("name") or bus.name)
            bus.gain_db = float(row.get("gainDb", bus.gain_db) or 0)
            bus.muted = bool(row.get("muted", bus.muted))
            self.repository.save_bus(bus); buses_by_role[role] = bus
        tracks_by_role = {t.role_code: t for t in self.repository.tracks(project_id)}
        for row in list(data.get("tracks", []) or []):
            role = str(row.get("role") or "general")
            track = tracks_by_role.get(role) or self.track_for_role(project_id, role)
            track.name = str(row.get("name") or track.name)
            track.gain_db = float(row.get("gainDb", track.gain_db) or 0)
            track.pan = float(row.get("pan", track.pan) or 0)
            track.muted = bool(row.get("muted", track.muted)); track.solo = bool(row.get("solo", track.solo)); track.enabled = bool(row.get("enabled", track.enabled))
            bus_role = str(row.get("busRole") or self._bus_role_for_track(role))
            if bus_role in buses_by_role: track.bus_id = buses_by_role[bus_role].id
            self.repository.save_track(track); tracks_by_role[role] = track

        # Template effects are ID-free and target semantic roles. Existing user
        # effects are preserved; only explicitly supplied template effects are added.
        for row in list(data.get("effects", []) or []):
            owner_type = str(row.get("ownerType") or "")
            owner_role = str(row.get("ownerRole") or "")
            owner_id = ""
            if owner_type == "master":
                owner_id = project_id
            elif owner_type == "track" and owner_role in tracks_by_role:
                owner_id = tracks_by_role[owner_role].id
            elif owner_type == "bus" and owner_role in buses_by_role:
                owner_id = buses_by_role[owner_role].id
            if not owner_id:
                continue
            effect = AudioEffectSpec(owner_type, owner_id, str(row.get("type") or "gain"), order=len(self.repository.effects(project_id, owner_type, owner_id)), enabled=bool(row.get("enabled", True)), settings=dict(row.get("settings") or {}))
            self.repository.save_effect(project_id, effect)

        # Ducking endpoints are also semantic so the same template works in every
        # project without leaking project-specific track/bus UUIDs.
        for row in list(data.get("duckingRules", []) or []):
            trigger_kind = str(row.get("triggerKind") or "bus")
            target_kind = str(row.get("targetKind") or "bus")
            trigger_role = str(row.get("triggerRole") or "")
            target_role = str(row.get("targetRole") or "")
            trigger_id = (buses_by_role.get(trigger_role).id if trigger_kind == "bus" and trigger_role in buses_by_role else tracks_by_role.get(trigger_role).id if trigger_kind == "track" and trigger_role in tracks_by_role else "")
            target_id = (buses_by_role.get(target_role).id if target_kind == "bus" and target_role in buses_by_role else tracks_by_role.get(target_role).id if target_kind == "track" and target_role in tracks_by_role else "")
            if trigger_id and target_id:
                self.repository.save_ducking(DuckingRule(project_id, trigger_id, target_id, trigger_kind, target_kind, float(row.get("duckAmountDb", -12.0)), int(row.get("attackMs", 120)), int(row.get("releaseMs", 220)), row.get("threshold"), bool(row.get("enabled", True)), dict(row.get("metadata") or {})))

        master_data = dict(data.get("master") or {})
        master = self.repository.mix_settings(project_id)
        master.master_gain_db = float(master_data.get("masterGainDb", master_data.get("gainDb", master.master_gain_db)) or 0)
        master.limiter_enabled = bool(master_data.get("limiterEnabled", master.limiter_enabled))
        master.limiter_limit = float(master_data.get("limiterLimit", master.limiter_limit) or master.limiter_limit)
        master.normalization_enabled = bool(master_data.get("normalizationEnabled", master.normalization_enabled))
        master.normalization_target_lufs = float(master_data.get("normalizationTargetLufs", master.normalization_target_lufs) or master.normalization_target_lufs)
        master.preset = str(master_data.get("preset") or data.get("preset") or master.preset)
        self.repository.save_mix_settings(master)
        if data.get("musicDucking") is not None:
            duck = dict(data.get("musicDucking") or {})
            self.set_music_ducking(project_id, bool(duck.get("enabled", True)), float(duck.get("amountDb", -12.0)), int(duck.get("attackMs", 120)), int(duck.get("releaseMs", 220)))
        return self.state(project_id)

    def _resolve_source_path(self, project_id: str, source_kind: str, source_ref: str, metadata: dict[str, Any]) -> str:
        try:
            if source_kind == "narration" and self.scene_repository is not None and self.generated_audio_repository is not None:
                scene = self.scene_repository.get(source_ref)
                audio_id = str(getattr(scene, "narration_audio_id", "") or "") if scene is not None else ""
                audio = self.generated_audio_repository.get(audio_id) if audio_id else None
                return str(getattr(audio, "file_path", "") or "") if audio is not None else ""
            if source_kind == "source_audio" and self.scene_repository is not None and self.media_repository is not None:
                scene = self.scene_repository.get(source_ref)
                media_id = str(getattr(scene, "primary_media_id", "") or "") if scene is not None else ""
                media = self.media_repository.get_by_id(media_id) if media_id else None
                return str(getattr(media, "project_path", "") or getattr(media, "path", "") or "") if media is not None else ""
            if source_kind == "manual_audio" and self.phase22_repository is not None and self.media_repository is not None:
                clips = list(self.phase22_repository.audio_clips(project_id) or [])
                manual = next((c for c in clips if str(getattr(c, "id", "")) == source_ref), None)
                if manual is None and hasattr(self.phase22_repository, "audio_clip"):
                    manual = self.phase22_repository.audio_clip(source_ref)
                media_id = str(getattr(manual, "media_id", "") or metadata.get("mediaId") or "") if manual is not None else str(metadata.get("mediaId") or "")
                media = self.media_repository.get_by_id(media_id) if media_id else None
                return str(getattr(media, "project_path", "") or getattr(media, "path", "") or "") if media is not None else ""
            if metadata.get("sourcePath"):
                return str(metadata.get("sourcePath"))
        except Exception:
            if self.logger:
                self.logger.warning("Could not resolve mixer source path", exc_info=True)
        return ""

    @staticmethod
    def _role_for_timeline_clip(timeline_role: str, source_kind: str, metadata: dict[str, Any]) -> str:
        if source_kind == "narration": return "narration"
        if source_kind == "source_audio": return "source_audio"
        subtype = str(metadata.get("assetSubtype") or metadata.get("subtype") or "").casefold()
        if subtype in {"music", "sfx", "ambience"}: return subtype
        if timeline_role in {"music", "sfx"}: return timeline_role
        return "voice"

    def _speech_block_clips(self, project_id: str, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.phase22_repository is None or self.generated_audio_repository is None:
            return []
        try:
            blocks = list(self.phase22_repository.blocks_for_project(project_id) or [])
        except Exception:
            return []
        already_audio = {str((x.get("metadata") or {}).get("audioId") or "") for x in existing}
        result = []
        fallback_cursor = 0
        for block in blocks:
            audio_id = str(getattr(block, "audio_id", "") or "")
            if not audio_id or audio_id in already_audio:
                continue
            audio = self.generated_audio_repository.get(audio_id)
            source = str(getattr(audio, "file_path", "") or "") if audio is not None else ""
            if not source:
                continue
            speaker = None
            try:
                speaker_id = str(getattr(block, "speaker_id", "") or "")
                speaker = self.phase22_repository.speaker(project_id, speaker_id) if speaker_id else None
            except Exception:
                speaker = None
            role_name = str(getattr(speaker, "role_code", "") or getattr(speaker, "role", "") or "speaker")
            # SpeakerProfile uses interview_guest/interviewer/expert in addition to
            # the simple public routing vocabulary; map those deterministically.
            if role_name in {"interview_guest", "interviewer", "expert", "character", "speaker"}:
                route_role = "dialogue"
            elif role_name in {"narrator"}:
                route_role = "narration"
            else:
                route_role = "voice"
            track = self.track_for_role(project_id, route_role)
            duration = max(1, int(getattr(audio, "duration_ms", 0) or 1))
            offset = getattr(block, "start_offset_ms", None)
            scene_id = str(getattr(block, "scene_id", "") or "")
            if scene_id and self.timeline_service is not None:
                try:
                    start = self.timeline_service.scene_to_project_time(project_id, scene_id, int(offset or 0))
                except Exception:
                    start = int(offset or fallback_cursor)
            else:
                start = int(offset if offset is not None else fallback_cursor)
            fallback_cursor = max(fallback_cursor, start + duration + max(0, int(getattr(block, "pause_after_ms", 0) or 0)))
            speaker_name = str(getattr(speaker, "name", "") or "")
            language = str(getattr(block, "language", "") or getattr(speaker, "language", "") or "")
            result.append({
                "id": f"speech-block:{getattr(block, 'id', audio_id)}",
                "trackId": track.id, "role": route_role, "sourcePath": source,
                "timelineStartMs": max(0, start), "durationMs": duration, "sourceInMs": 0,
                "gainDb": 0.0, "pan": 0.0, "fadeInMs": 0, "fadeOutMs": 0, "muted": False,
                "speakerId": str(getattr(block, "speaker_id", "") or ""),
                "speakerName": speaker_name, "language": language,
                "metadata": {"audioId": audio_id, "speechBlockId": str(getattr(block, "id", "")), "speakerRole": role_name, "text": str(getattr(block, "text", "") or "")},
            })
        return result

    def _legacy_dub_clips(self, project_id: str, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.dubbing_repository is None:
            return []
        track = self.track_for_role(project_id, "dub")
        try:
            segments_fn = getattr(self.dubbing_repository, "segments", None)
            if callable(segments_fn):
                clips = []
                for segment in list(segments_fn(project_id) or []):
                    path = str(getattr(segment, "generated_audio_path", "") or "")
                    if not path:
                        continue
                    start = int(getattr(segment, "source_start_ms", 0) or 0) + int(getattr(segment, "start_offset_ms", 0) or 0)
                    duration = int(getattr(segment, "generated_duration_ms", 0) or 0)
                    if duration <= 0:
                        duration = max(1, int(getattr(segment, "source_end_ms", 0) or 0) - int(getattr(segment, "source_start_ms", 0) or 0))
                    clips.append({
                        "id": f"dub-segment:{getattr(segment, 'id', len(clips))}", "trackId": track.id, "role": "dub",
                        "sourcePath": path, "timelineStartMs": max(0, start), "durationMs": duration, "sourceInMs": 0,
                        "gainDb": 0.0, "pan": 0.0, "fadeInMs": 0, "fadeOutMs": 0, "muted": False,
                        "speakerName": str(getattr(segment, "speaker_label", "") or ""),
                        "language": str(getattr(getattr(self.dubbing_repository, "get_project", lambda *_: None)(project_id), "target_language", "") or ""),
                        "metadata": {"dubSegmentId": str(getattr(segment, "id", "")), "generatedAudioId": str(getattr(segment, "generated_audio_id", "") or "")},
                    })
                if clips:
                    return clips
            for name in ("latest_output", "latest_audio_output", "active_audio_output", "get_latest_audio_output"):
                fn = getattr(self.dubbing_repository, name, None)
                if not callable(fn):
                    continue
                item = fn(project_id)
                if item is None:
                    continue
                path = str(getattr(item, "file_path", "") or (item.get("filePath", "") if isinstance(item, dict) else ""))
                if not path:
                    continue
                duration = int(getattr(item, "duration_ms", 0) or 0) or max([int(x.get("durationMs", 0) or 0) + int(x.get("timelineStartMs", 0) or 0) for x in existing] or [1])
                return [{"id": f"legacy-dub:{getattr(item, 'id', 'mix')}", "trackId": track.id, "role": "dub", "sourcePath": path, "timelineStartMs": 0, "durationMs": duration, "sourceInMs": 0, "gainDb": 0.0, "pan": 0.0, "fadeInMs": 0, "fadeOutMs": 0, "muted": False, "metadata": {"legacyDubOutput": True}}]
        except Exception:
            if self.logger:
                self.logger.warning("Could not resolve legacy dub audio", exc_info=True)
        return []

    def template_settings(self, project_id: str) -> dict[str, Any]:
        """Export semantic mixer settings for Phase 24 templates / Phase 26 Batch."""
        state = self.state(project_id)
        bus_roles = {str(b["id"]): str(b.get("role") or "general") for b in state["buses"]}
        track_roles = {str(t["id"]): str(t.get("role") or "general") for t in state["tracks"]}
        tracks = []
        for raw in state["tracks"]:
            row = {k: v for k, v in raw.items() if k not in {"id", "projectId", "busId"}}
            row["busRole"] = bus_roles.get(str(raw.get("busId") or ""), self._bus_role_for_track(str(raw.get("role") or "general")))
            tracks.append(row)
        effects = []
        for raw in state["effects"]:
            owner_type = str(raw.get("ownerType") or "")
            if owner_type == "clip":
                # Project-specific clip UUIDs do not belong in reusable templates.
                continue
            row = {k: v for k, v in raw.items() if k not in {"id", "ownerId"}}
            row["ownerRole"] = "master" if owner_type == "master" else track_roles.get(str(raw.get("ownerId") or ""), "") if owner_type == "track" else bus_roles.get(str(raw.get("ownerId") or ""), "")
            if row["ownerRole"]:
                effects.append(row)
        ducking = []
        for raw in state["duckingRules"]:
            trigger_kind = str(raw.get("triggerKind") or "bus"); target_kind = str(raw.get("targetKind") or "bus")
            trigger_role = bus_roles.get(str(raw.get("triggerId") or ""), "") if trigger_kind == "bus" else track_roles.get(str(raw.get("triggerId") or ""), "")
            target_role = bus_roles.get(str(raw.get("targetId") or ""), "") if target_kind == "bus" else track_roles.get(str(raw.get("targetId") or ""), "")
            if not trigger_role or not target_role:
                continue
            row = {k: v for k, v in raw.items() if k not in {"id", "projectId", "triggerId", "targetId"}}
            row["triggerRole"] = trigger_role; row["targetRole"] = target_role
            ducking.append(row)
        return {
            "tracks": tracks,
            "buses": [{k: v for k, v in b.items() if k not in {"id", "projectId"}} for b in state["buses"]],
            "effects": effects,
            "duckingRules": ducking,
            "master": {k: v for k, v in state["master"].items() if k not in {"projectId", "updatedAt"}},
        }

    def duplicate_project(self, source_project_id: str, target_project_id: str, *, clip_id_map: dict[str, str] | None = None):
        return self.repository.duplicate_project(source_project_id, target_project_id, clip_id_map=clip_id_map)

    def restore_command_state(self, name: str, payload: dict[str, Any]) -> None:
        """Restore an audio edit without pushing a second command.

        Phase 30 plugs this into Phase 17's existing CommandStack at runtime.
        """
        if name in {"track", "track_add"}:
            project_id = str(payload.get("projectId") or "")
            track_id = str(payload.get("id") or "")
            if not project_id or not track_id:
                return
            if payload.get("exists") is False:
                try: self.repository.delete_track(project_id, track_id)
                except Exception: pass
                return
            item = self.repository.track(project_id, track_id)
            if item is None:
                item = AudioTrack(project_id, str(payload.get("name") or "Audio"), str(payload.get("role") or "general"), int(payload.get("order", 0) or 0), track_id=track_id)
            item.name = str(payload.get("name") or item.name); item.role = str(payload.get("role") or item.role_code); item.order = int(payload.get("order", item.order) or 0)
            item.gain_db = float(payload.get("gainDb", item.gain_db) or 0); item.pan = float(payload.get("pan", item.pan) or 0)
            item.muted = bool(payload.get("muted", item.muted)); item.solo = bool(payload.get("solo", item.solo)); item.enabled = bool(payload.get("enabled", item.enabled)); item.bus_id = str(payload.get("busId", item.bus_id) or "")
            self.repository.save_track(item); return
        if name in {"master_gain", "master_state"}:
            project_id = str(payload.get("projectId") or ""); item = self.repository.mix_settings(project_id)
            item.master_gain_db = float(payload.get("masterGainDb", item.master_gain_db) or 0)
            item.limiter_enabled = bool(payload.get("limiterEnabled", item.limiter_enabled)); item.limiter_limit = float(payload.get("limiterLimit", item.limiter_limit) or item.limiter_limit)
            item.normalization_enabled = bool(payload.get("normalizationEnabled", item.normalization_enabled)); item.normalization_target_lufs = float(payload.get("normalizationTargetLufs", item.normalization_target_lufs) or item.normalization_target_lufs)
            self.repository.save_mix_settings(item); return
        if name == "clip_mix":
            project_id = str(payload.get("projectId") or ""); clip_id = str(payload.get("clipId") or "")
            self.repository.save_clip_mix(project_id, clip_id, source_kind=str(payload.get("sourceKind") or "timeline"), track_id=str(payload.get("trackId") or ""), gain_db=float(payload.get("gainDb", 0) or 0), pan=float(payload.get("pan", 0) or 0), fade_in_ms=int(payload.get("fadeInMs", 0) or 0), fade_out_ms=int(payload.get("fadeOutMs", 0) or 0), muted=bool(payload.get("muted", False)), effects=list(payload.get("effects") or []), metadata=dict(payload.get("metadata") or {})); return
        if name in {"preset", "ducking"}:
            self._restore_full_state(payload)

    def _restore_full_state(self, snapshot: dict[str, Any]) -> None:
        project_id = str(snapshot.get("projectId") or (snapshot.get("master") or {}).get("projectId") or "")
        if not project_id:
            return
        current_tracks = {t.id: t for t in self.repository.tracks(project_id)}
        wanted_track_ids = set()
        for raw in list(snapshot.get("tracks") or []):
            track_id = str(raw.get("id") or ""); wanted_track_ids.add(track_id)
            item = current_tracks.get(track_id) or AudioTrack(project_id, str(raw.get("name") or "Audio"), str(raw.get("role") or "general"), int(raw.get("order", 0) or 0), track_id=track_id)
            item.name=str(raw.get("name") or item.name); item.role=str(raw.get("role") or item.role_code); item.order=int(raw.get("order",item.order) or 0); item.gain_db=float(raw.get("gainDb",item.gain_db) or 0); item.pan=float(raw.get("pan",item.pan) or 0); item.muted=bool(raw.get("muted",item.muted)); item.solo=bool(raw.get("solo",item.solo)); item.enabled=bool(raw.get("enabled",item.enabled)); item.bus_id=str(raw.get("busId",item.bus_id) or ""); self.repository.save_track(item)
        master_raw=dict(snapshot.get("master") or {})
        if master_raw:
            master=self.repository.mix_settings(project_id); master.master_gain_db=float(master_raw.get("masterGainDb",master.master_gain_db) or 0); master.limiter_enabled=bool(master_raw.get("limiterEnabled",master.limiter_enabled)); master.limiter_limit=float(master_raw.get("limiterLimit",master.limiter_limit) or master.limiter_limit); master.normalization_enabled=bool(master_raw.get("normalizationEnabled",master.normalization_enabled)); master.normalization_target_lufs=float(master_raw.get("normalizationTargetLufs",master.normalization_target_lufs) or master.normalization_target_lufs); master.preset=str(master_raw.get("preset") or master.preset); master.metadata=dict(master_raw.get("metadata") or master.metadata); self.repository.save_mix_settings(master)
        current_rules={r.id:r for r in self.repository.ducking_rules(project_id)}; wanted=set()
        for raw in list(snapshot.get("duckingRules") or []):
            rid=str(raw.get("id") or ""); wanted.add(rid); rule=current_rules.get(rid) or DuckingRule(project_id,str(raw.get("triggerId") or ""),str(raw.get("targetId") or ""),rule_id=rid)
            rule.trigger_kind=str(raw.get("triggerKind") or rule.trigger_kind); rule.trigger_id=str(raw.get("triggerId") or rule.trigger_id); rule.target_kind=str(raw.get("targetKind") or rule.target_kind); rule.target_id=str(raw.get("targetId") or rule.target_id); rule.duck_amount_db=float(raw.get("duckAmountDb",rule.duck_amount_db) or 0); rule.attack_ms=int(raw.get("attackMs",rule.attack_ms) or 0); rule.release_ms=int(raw.get("releaseMs",rule.release_ms) or 0); rule.threshold=raw.get("threshold"); rule.enabled=bool(raw.get("enabled",rule.enabled)); rule.metadata=dict(raw.get("metadata") or rule.metadata); self.repository.save_ducking(rule)
        for rid in set(current_rules)-wanted:
            self.repository.delete_ducking(project_id,rid)

    def _ensure_duck_between_tracks(self, project_id: str, trigger_id: str, target_id: str, amount: float, attack: int = 120, release: int = 220):
        existing = next((r for r in self.repository.ducking_rules(project_id) if r.trigger_kind == "track" and r.trigger_id == trigger_id and r.target_kind == "track" and r.target_id == target_id), None)
        rule = existing or DuckingRule(project_id, trigger_id, target_id, "track", "track")
        rule.duck_amount_db = max(-36.0, min(0.0, float(amount)))
        rule.attack_ms, rule.release_ms, rule.enabled = int(attack), int(release), True
        return self.repository.save_ducking(rule)

    @staticmethod
    def _bus_role_for_track(role: str) -> str:
        if role in {"voice", "dialogue", "narration", "dub"}: return "voice"
        if role in {"music"}: return "music"
        if role in {"sfx", "ambience"}: return "sfx"
        return "source"

    @staticmethod
    def _label_for_role(role: str) -> str:
        return str(role).replace("_", " ").title()

    def _command(self, name: str, before: dict, after: dict) -> None:
        if self.command_sink:
            try:self.command_sink(name, before, after)
            except Exception:pass

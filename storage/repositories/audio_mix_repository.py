from __future__ import annotations

import json
from copy import deepcopy
from uuid import uuid4

from domain.audio_bus import AudioBus
from domain.audio_effect import AudioEffectSpec
from domain.audio_mix import AudioMixSettings
from domain.audio_track import AudioTrack
from domain.ducking_rule import DuckingRule
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase


def _j(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


class AudioMixRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def tracks(self, project_id: str) -> list[AudioTrack]:
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT * FROM audio_tracks WHERE project_id=? ORDER BY track_order,id",
                (project_id,),
            ).fetchall()
        return [AudioTrack.from_record(row) for row in rows]

    def track(self, project_id: str, track_id: str) -> AudioTrack | None:
        with self.database.connect() as c:
            row = c.execute(
                "SELECT * FROM audio_tracks WHERE project_id=? AND id=?",
                (project_id, track_id),
            ).fetchone()
        return AudioTrack.from_record(row) if row else None

    def save_track(self, item: AudioTrack) -> AudioTrack:
        item.validate()
        item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute(
                '''INSERT INTO audio_tracks(id,project_id,name,role,track_order,gain_db,pan,muted,solo,enabled,bus_id,metadata_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,role=excluded.role,track_order=excluded.track_order,
                   gain_db=excluded.gain_db,pan=excluded.pan,muted=excluded.muted,solo=excluded.solo,enabled=excluded.enabled,
                   bus_id=excluded.bus_id,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
                (
                    item.id,
                    item.project_id,
                    item.name,
                    item.role_code,
                    item.order,
                    item.gain_db,
                    item.pan,
                    int(item.muted),
                    int(item.solo),
                    int(item.enabled),
                    item.bus_id or None,
                    _j(item.metadata),
                    item.created_at,
                    item.updated_at,
                ),
            )
        return item

    def delete_track(self, project_id: str, track_id: str) -> None:
        with self.database.connect() as c, c:
            c.execute("DELETE FROM audio_tracks WHERE project_id=? AND id=?", (project_id, track_id))

    def buses(self, project_id: str) -> list[AudioBus]:
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT * FROM audio_buses WHERE project_id=? ORDER BY bus_order,id",
                (project_id,),
            ).fetchall()
        return [AudioBus.from_record(row) for row in rows]

    def bus(self, project_id: str, bus_id: str) -> AudioBus | None:
        with self.database.connect() as c:
            row = c.execute(
                "SELECT * FROM audio_buses WHERE project_id=? AND id=?",
                (project_id, bus_id),
            ).fetchone()
        return AudioBus.from_record(row) if row else None

    def save_bus(self, item: AudioBus) -> AudioBus:
        item.validate()
        item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute(
                '''INSERT INTO audio_buses(id,project_id,name,role,bus_order,gain_db,muted,metadata_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,role=excluded.role,bus_order=excluded.bus_order,
                   gain_db=excluded.gain_db,muted=excluded.muted,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
                (
                    item.id,
                    item.project_id,
                    item.name,
                    item.role_code,
                    item.order,
                    item.gain_db,
                    int(item.muted),
                    _j(item.metadata),
                    item.created_at,
                    item.updated_at,
                ),
            )
        return item

    def effects(self, project_id: str, owner_type: str | None = None, owner_id: str | None = None) -> list[AudioEffectSpec]:
        sql = "SELECT * FROM audio_effects WHERE project_id=?"
        args: list[object] = [project_id]
        if owner_type is not None:
            sql += " AND owner_type=?"
            args.append(owner_type)
        if owner_id is not None:
            sql += " AND owner_id=?"
            args.append(owner_id)
        sql += " ORDER BY effect_order,id"
        with self.database.connect() as c:
            rows = c.execute(sql, tuple(args)).fetchall()
        return [AudioEffectSpec.from_record(row) for row in rows]

    def save_effect(self, project_id: str, item: AudioEffectSpec) -> AudioEffectSpec:
        item.validate()
        item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute(
                '''INSERT INTO audio_effects(id,project_id,owner_type,owner_id,effect_type,effect_order,enabled,settings_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET owner_type=excluded.owner_type,owner_id=excluded.owner_id,
                   effect_type=excluded.effect_type,effect_order=excluded.effect_order,enabled=excluded.enabled,
                   settings_json=excluded.settings_json,updated_at=excluded.updated_at''',
                (
                    item.id,
                    project_id,
                    item.owner_type,
                    item.owner_id,
                    item.type_code,
                    item.order,
                    int(item.enabled),
                    _j(item.settings),
                    item.created_at,
                    item.updated_at,
                ),
            )
        return item

    def delete_effect(self, project_id: str, effect_id: str) -> None:
        with self.database.connect() as c, c:
            c.execute("DELETE FROM audio_effects WHERE project_id=? AND id=?", (project_id, effect_id))

    def ducking_rules(self, project_id: str) -> list[DuckingRule]:
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT * FROM audio_ducking_rules WHERE project_id=? ORDER BY created_at,id",
                (project_id,),
            ).fetchall()
        return [DuckingRule.from_record(row) for row in rows]

    def save_ducking(self, item: DuckingRule) -> DuckingRule:
        item.validate()
        item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute(
                '''INSERT INTO audio_ducking_rules(id,project_id,trigger_kind,trigger_id,target_kind,target_id,duck_amount_db,attack_ms,release_ms,threshold,enabled,metadata_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET trigger_kind=excluded.trigger_kind,trigger_id=excluded.trigger_id,
                   target_kind=excluded.target_kind,target_id=excluded.target_id,duck_amount_db=excluded.duck_amount_db,
                   attack_ms=excluded.attack_ms,release_ms=excluded.release_ms,threshold=excluded.threshold,
                   enabled=excluded.enabled,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
                (
                    item.id,
                    item.project_id,
                    item.trigger_kind,
                    item.trigger_id,
                    item.target_kind,
                    item.target_id,
                    item.duck_amount_db,
                    item.attack_ms,
                    item.release_ms,
                    item.threshold,
                    int(item.enabled),
                    _j(item.metadata),
                    item.created_at,
                    item.updated_at,
                ),
            )
        return item

    def delete_ducking(self, project_id: str, rule_id: str) -> None:
        with self.database.connect() as c, c:
            c.execute("DELETE FROM audio_ducking_rules WHERE project_id=? AND id=?", (project_id, rule_id))

    def mix_settings(self, project_id: str) -> AudioMixSettings:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM audio_mix_settings WHERE project_id=?", (project_id,)).fetchone()
        return AudioMixSettings.from_record(row) if row else AudioMixSettings(project_id)

    def save_mix_settings(self, item: AudioMixSettings) -> AudioMixSettings:
        item.validate()
        item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute(
                '''INSERT INTO audio_mix_settings(project_id,master_gain_db,limiter_enabled,limiter_limit,normalization_enabled,normalization_target_lufs,preset,metadata_json,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project_id) DO UPDATE SET master_gain_db=excluded.master_gain_db,
                   limiter_enabled=excluded.limiter_enabled,limiter_limit=excluded.limiter_limit,
                   normalization_enabled=excluded.normalization_enabled,normalization_target_lufs=excluded.normalization_target_lufs,
                   preset=excluded.preset,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
                (
                    item.project_id,
                    item.master_gain_db,
                    int(item.limiter_enabled),
                    item.limiter_limit,
                    int(item.normalization_enabled),
                    item.normalization_target_lufs,
                    item.preset,
                    _j(item.metadata),
                    item.updated_at,
                ),
            )
        return item

    def clip_mix(self, project_id: str, clip_id: str) -> dict[str, object]:
        with self.database.connect() as c:
            row = c.execute(
                "SELECT * FROM audio_clip_mix WHERE project_id=? AND clip_id=?",
                (project_id, clip_id),
            ).fetchone()
        if row is None:
            return {
                "clipId": clip_id,
                "projectId": project_id,
                "sourceKind": "timeline",
                "trackId": "",
                "gainDb": 0.0,
                "pan": 0.0,
                "fadeInMs": 0,
                "fadeOutMs": 0,
                "muted": False,
                "effects": [],
                "metadata": {},
            }
        try:
            effects = json.loads(str(row["effects_json"] or "[]"))
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except Exception:
            effects, metadata = [], {}
        return {
            "clipId": clip_id,
            "projectId": project_id,
            "sourceKind": str(row["source_kind"]),
            "trackId": str(row["track_id"] or ""),
            "gainDb": float(row["gain_db"]),
            "pan": float(row["pan"]),
            "fadeInMs": int(row["fade_in_ms"]),
            "fadeOutMs": int(row["fade_out_ms"]),
            "muted": bool(row["muted"]),
            "effects": effects if isinstance(effects, list) else [],
            "metadata": metadata if isinstance(metadata, dict) else {},
        }

    def save_clip_mix(
        self,
        project_id: str,
        clip_id: str,
        *,
        source_kind: str = "timeline",
        track_id: str = "",
        gain_db: float = 0.0,
        pan: float = 0.0,
        fade_in_ms: int = 0,
        fade_out_ms: int = 0,
        muted: bool = False,
        effects: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> dict[str, object]:
        if not -60 <= float(gain_db) <= 12 or not -1 <= float(pan) <= 1:
            raise ValueError("Clip mix values are out of range.")
        if int(fade_in_ms) < 0 or int(fade_out_ms) < 0:
            raise ValueError("Clip fades cannot be negative.")
        with self.database.connect() as c, c:
            c.execute(
                '''INSERT INTO audio_clip_mix(project_id,clip_id,source_kind,track_id,gain_db,pan,fade_in_ms,fade_out_ms,muted,effects_json,metadata_json,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project_id,clip_id) DO UPDATE SET source_kind=excluded.source_kind,track_id=excluded.track_id,
                   gain_db=excluded.gain_db,pan=excluded.pan,fade_in_ms=excluded.fade_in_ms,fade_out_ms=excluded.fade_out_ms,
                   muted=excluded.muted,effects_json=excluded.effects_json,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
                (
                    project_id,
                    clip_id,
                    source_kind,
                    track_id or None,
                    float(gain_db),
                    float(pan),
                    int(fade_in_ms),
                    int(fade_out_ms),
                    int(bool(muted)),
                    _j(effects or []),
                    _j(metadata or {}),
                    utc_now_iso(),
                ),
            )
        return self.clip_mix(project_id, clip_id)

    def duplicate_project(self, source_project_id: str, target_project_id: str, *, clip_id_map: dict[str, str] | None = None) -> dict[str, dict[str, str]]:
        clip_id_map = dict(clip_id_map or {})
        maps: dict[str, dict[str, str]] = {"bus": {}, "track": {}, "effect": {}, "ducking": {}, "clip": clip_id_map}
        for bus in self.buses(source_project_id):
            old = bus.id
            clone = deepcopy(bus)
            clone.bus_id = str(uuid4())
            clone.project_id = target_project_id
            clone.created_at = clone.updated_at = utc_now_iso()
            self.save_bus(clone)
            maps["bus"][old] = clone.id
        for track in self.tracks(source_project_id):
            old = track.id
            clone = deepcopy(track)
            clone.track_id = str(uuid4())
            clone.project_id = target_project_id
            clone.bus_id = maps["bus"].get(track.bus_id, "")
            clone.created_at = clone.updated_at = utc_now_iso()
            self.save_track(clone)
            maps["track"][old] = clone.id
        settings = deepcopy(self.mix_settings(source_project_id))
        settings.project_id = target_project_id
        settings.updated_at = utc_now_iso()
        self.save_mix_settings(settings)
        for effect in self.effects(source_project_id):
            old = effect.id
            clone = deepcopy(effect)
            clone.effect_id = str(uuid4())
            if effect.owner_type == "master":
                clone.owner_id = target_project_id
            elif effect.owner_type == "clip":
                clone.owner_id = clip_id_map.get(effect.owner_id, effect.owner_id)
            else:
                clone.owner_id = maps["track"].get(effect.owner_id, maps["bus"].get(effect.owner_id, effect.owner_id))
            clone.created_at = clone.updated_at = utc_now_iso()
            self.save_effect(target_project_id, clone)
            maps["effect"][old] = clone.id
        for rule in self.ducking_rules(source_project_id):
            old = rule.id
            clone = deepcopy(rule)
            clone.rule_id = str(uuid4())
            clone.project_id = target_project_id
            clone.trigger_id = maps["track"].get(rule.trigger_id, maps["bus"].get(rule.trigger_id, rule.trigger_id))
            clone.target_id = maps["track"].get(rule.target_id, maps["bus"].get(rule.target_id, rule.target_id))
            clone.created_at = clone.updated_at = utc_now_iso()
            self.save_ducking(clone)
            maps["ducking"][old] = clone.id
        with self.database.connect() as c, c:
            rows = c.execute("SELECT * FROM audio_clip_mix WHERE project_id=?", (source_project_id,)).fetchall()
            for row in rows:
                c.execute(
                    '''INSERT OR REPLACE INTO audio_clip_mix(project_id,clip_id,source_kind,track_id,gain_db,pan,fade_in_ms,fade_out_ms,muted,effects_json,metadata_json,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (
                        target_project_id,
                        clip_id_map.get(str(row["clip_id"]), str(row["clip_id"])),
                        str(row["source_kind"]),
                        maps["track"].get(str(row["track_id"] or ""), None),
                        float(row["gain_db"]),
                        float(row["pan"]),
                        int(row["fade_in_ms"]),
                        int(row["fade_out_ms"]),
                        int(row["muted"]),
                        str(row["effects_json"]),
                        str(row["metadata_json"]),
                        utc_now_iso(),
                    ),
                )
        return maps

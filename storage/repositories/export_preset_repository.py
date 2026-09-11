from __future__ import annotations

import json

from domain.export_preset import ExportPreset
from domain.export_profile import ExportProfile
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase


class ExportPresetRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, preset: ExportPreset) -> ExportPreset:
        preset.validate()
        now = utc_now_iso()
        payload = preset.to_dict()
        with self.database.connect() as c, c:
            c.execute(
                "INSERT INTO export_presets(id,name,description,settings_json,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (preset.id, preset.name, preset.description, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), now, now),
            )
        return preset

    def update(self, preset: ExportPreset) -> ExportPreset:
        preset.validate()
        payload = preset.to_dict()
        with self.database.connect() as c, c:
            cur = c.execute(
                "UPDATE export_presets SET name=?,description=?,settings_json=?,updated_at=? WHERE id=?",
                (preset.name, preset.description, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), utc_now_iso(), preset.id),
            )
            if cur.rowcount == 0:
                raise KeyError("Export preset not found.")
        return preset

    def get(self, preset_id: str) -> ExportPreset | None:
        with self.database.connect() as c:
            row = c.execute("SELECT * FROM export_presets WHERE id=?", (preset_id,)).fetchone()
        if not row:
            return None
        data = json.loads(row["settings_json"] or "{}")
        data.setdefault("id", row["id"])
        data.setdefault("name", row["name"])
        data.setdefault("description", row["description"])
        data["builtin"] = False
        return ExportPreset.from_dict(data, builtin=False)

    def list_all(self) -> list[ExportPreset]:
        with self.database.connect() as c:
            rows = c.execute("SELECT * FROM export_presets ORDER BY name COLLATE NOCASE, updated_at DESC").fetchall()
        result=[]
        for row in rows:
            data=json.loads(row["settings_json"] or "{}")
            data.setdefault("id", row["id"]); data.setdefault("name", row["name"]); data.setdefault("description", row["description"]); data["builtin"]=False
            result.append(ExportPreset.from_dict(data,builtin=False))
        return result

    def delete(self, preset_id: str) -> None:
        with self.database.connect() as c, c:
            cur=c.execute("DELETE FROM export_presets WHERE id=?",(preset_id,))
            if cur.rowcount == 0:
                raise KeyError("Export preset not found.")

    def save_profile(self, profile: ExportProfile) -> None:
        with self.database.connect() as c, c:
            c.execute(
                """INSERT INTO project_export_profiles(project_id,last_preset_id,settings_json,updated_at)
                   VALUES (?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET
                   last_preset_id=excluded.last_preset_id, settings_json=excluded.settings_json, updated_at=excluded.updated_at""",
                (profile.project_id, profile.last_preset_id, json.dumps(profile.settings, ensure_ascii=False, separators=(",", ":")), profile.updated_at),
            )

    def get_profile(self, project_id: str) -> ExportProfile | None:
        with self.database.connect() as c:
            row=c.execute("SELECT * FROM project_export_profiles WHERE project_id=?",(project_id,)).fetchone()
        if not row:
            return None
        try: settings=json.loads(row["settings_json"] or "{}")
        except Exception: settings={}
        return ExportProfile(project_id=str(row["project_id"]),last_preset_id=str(row["last_preset_id"] or ""),settings=settings if isinstance(settings,dict) else {},updated_at=str(row["updated_at"]))

from __future__ import annotations

import json
from collections.abc import Iterable

from domain.director_plan import DirectorPlan
from domain.director_scene_plan import DirectorScenePlan
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase


class DirectorPlanRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, plan: DirectorPlan, scenes: Iterable[DirectorScenePlan]) -> DirectorPlan:
        plan.validate(); items=list(scenes)
        for item in items:
            item.plan_id=plan.id; item.validate()
        with self.database.connect() as c, c:
            self._insert_plan(c,plan)
            for item in items: self._insert_scene(c,item)
        return plan

    def update(self, plan: DirectorPlan) -> DirectorPlan:
        plan.validate(); plan.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE director_plans SET workflow=?,platform=?,language=?,target_duration_ms=?,aspect_ratio=?,source_type=?,source_id=?,status=?,plan_version=?,schema_version=?,rule_engine_version=?,source_fingerprint=?,recommendations_json=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?""",
                (plan.workflow,plan.platform,plan.language,plan.target_duration_ms,plan.aspect_ratio,plan.source_type,plan.source_id,plan.status_code,plan.version,plan.schema_version,plan.rule_engine_version,plan.source_fingerprint,json.dumps([r.to_dict() for r in plan.recommendations],ensure_ascii=False,separators=(",",":")),json.dumps(plan.metadata,ensure_ascii=False,separators=(",",":")),plan.updated_at,plan.id,plan.project_id))
            if cur.rowcount==0: raise KeyError("Director plan does not belong to this project.")
        return plan

    def replace_scenes(self, project_id: str, plan_id: str, scenes: Iterable[DirectorScenePlan]) -> None:
        items=list(scenes)
        with self.database.connect() as c,c:
            owner=c.execute("SELECT 1 FROM director_plans WHERE id=? AND project_id=?",(plan_id,project_id)).fetchone()
            if owner is None: raise KeyError("Director plan does not belong to this project.")
            c.execute("DELETE FROM director_scene_plans WHERE plan_id=?",(plan_id,))
            for order,item in enumerate(items):
                item.plan_id=plan_id; item.order=order; item.validate(); self._insert_scene(c,item)

    def get(self, plan_id: str) -> DirectorPlan | None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM director_plans WHERE id=?",(plan_id,)).fetchone()
        return DirectorPlan.from_record(row) if row else None

    def get_owned(self, project_id: str, plan_id: str) -> DirectorPlan | None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM director_plans WHERE id=? AND project_id=?",(plan_id,project_id)).fetchone()
        return DirectorPlan.from_record(row) if row else None

    def list_for_project(self, project_id: str) -> list[DirectorPlan]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM director_plans WHERE project_id=? ORDER BY updated_at DESC,created_at DESC",(project_id,)).fetchall()
        return [DirectorPlan.from_record(r) for r in rows]

    def scenes(self, plan_id: str) -> list[DirectorScenePlan]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM director_scene_plans WHERE plan_id=? ORDER BY scene_order",(plan_id,)).fetchall()
        result=[]
        for r in rows:
            try: metadata=json.loads(r["metadata_json"] or "{}")
            except Exception: metadata={}
            result.append(DirectorScenePlan.from_record(r,metadata if isinstance(metadata,dict) else {}))
        return result

    def update_scene(self, project_id: str, scene: DirectorScenePlan) -> DirectorScenePlan:
        scene.validate()
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE director_scene_plans SET scene_order=?,title=?,purpose=?,target_duration_ms=?,script_section_id=?,visual_type=?,visual_description=?,overlay_recommendation=?,voice_style=?,subtitle_style=?,transition=?,notes=?,locked=?,user_modified=?,metadata_json=? WHERE id=? AND plan_id IN (SELECT id FROM director_plans WHERE project_id=?)""",
                (scene.order,scene.title,scene.purpose,scene.target_duration_ms,scene.script_section_id,scene.visual_type,scene.visual_description,scene.overlay_recommendation,scene.voice_style,scene.subtitle_style,scene.transition,scene.notes,int(scene.locked),int(scene.user_modified),json.dumps(scene.metadata,ensure_ascii=False,separators=(",",":")),scene.id,project_id))
            if cur.rowcount==0: raise KeyError("Director scene plan does not belong to this project.")
        return scene

    def delete(self, project_id: str, plan_id: str) -> None:
        with self.database.connect() as c,c:
            c.execute("UPDATE projects SET active_director_plan_id=NULL WHERE id=? AND active_director_plan_id=?",(project_id,plan_id))
            cur=c.execute("DELETE FROM director_plans WHERE id=? AND project_id=?",(plan_id,project_id))
            if cur.rowcount==0: raise KeyError("Director plan does not belong to this project.")

    def set_active(self, project_id: str, plan_id: str | None) -> None:
        with self.database.connect() as c,c:
            if plan_id:
                owner=c.execute("SELECT 1 FROM director_plans WHERE id=? AND project_id=?",(plan_id,project_id)).fetchone()
                if owner is None: raise KeyError("Director plan does not belong to this project.")
            cur=c.execute("UPDATE projects SET active_director_plan_id=? WHERE id=?",(plan_id or None,project_id))
            if cur.rowcount==0: raise KeyError("Project not found.")

    def active_id(self, project_id: str) -> str:
        with self.database.connect() as c: row=c.execute("SELECT active_director_plan_id FROM projects WHERE id=?",(project_id,)).fetchone()
        if row is None: raise KeyError("Project not found.")
        return str(row["active_director_plan_id"] or "")

    def set_default_subtitle_preset(self, project_id: str, preset_id: str) -> None:
        with self.database.connect() as c,c:
            cur=c.execute("UPDATE projects SET default_subtitle_preset_id=? WHERE id=?",(preset_id or None,project_id))
            if cur.rowcount==0: raise KeyError("Project not found.")

    def default_subtitle_preset(self, project_id: str) -> str:
        with self.database.connect() as c: row=c.execute("SELECT default_subtitle_preset_id FROM projects WHERE id=?",(project_id,)).fetchone()
        if row is None: raise KeyError("Project not found.")
        return str(row["default_subtitle_preset_id"] or "")

    @staticmethod
    def _insert_plan(c,plan:DirectorPlan)->None:
        c.execute("""INSERT INTO director_plans(id,project_id,request_id,workflow,platform,language,target_duration_ms,aspect_ratio,source_type,source_id,status,plan_version,schema_version,rule_engine_version,source_fingerprint,recommendations_json,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (plan.id,plan.project_id,plan.request_id,plan.workflow,plan.platform,plan.language,plan.target_duration_ms,plan.aspect_ratio,plan.source_type,plan.source_id,plan.status_code,plan.version,plan.schema_version,plan.rule_engine_version,plan.source_fingerprint,json.dumps([r.to_dict() for r in plan.recommendations],ensure_ascii=False,separators=(",",":")),json.dumps(plan.metadata,ensure_ascii=False,separators=(",",":")),plan.created_at,plan.updated_at))

    @staticmethod
    def _insert_scene(c,item:DirectorScenePlan)->None:
        c.execute("""INSERT INTO director_scene_plans(id,plan_id,scene_order,title,purpose,target_duration_ms,script_section_id,visual_type,visual_description,overlay_recommendation,voice_style,subtitle_style,transition,notes,locked,user_modified,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item.id,item.plan_id,item.order,item.title,item.purpose,item.target_duration_ms,item.script_section_id,item.visual_type,item.visual_description,item.overlay_recommendation,item.voice_style,item.subtitle_style,item.transition,item.notes,int(item.locked),int(item.user_modified),json.dumps(item.metadata,ensure_ascii=False,separators=(",",":"))))

from __future__ import annotations

import json
from typing import Iterable

from domain.project import utc_now_iso
from domain.scene import Scene
from domain.scene_layer import SceneLayer
from domain.scene_overlay import SceneOverlay
from storage.database import SQLiteDatabase


class SceneRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, scene: Scene, layers: Iterable[SceneLayer] = (), overlays: Iterable[SceneOverlay] = ()) -> Scene:
        scene.validate()
        with self.database.connect() as c, c:
            self._insert_scene(c, scene)
            for layer in layers:
                layer.validate(); self._insert_layer(c, layer)
            for overlay in overlays:
                overlay.validate(scene.duration_ms); self._insert_overlay(c, overlay)
        return scene

    def get(self, scene_id: str) -> Scene | None:
        with self.database.connect() as c:
            row=c.execute("SELECT * FROM scenes WHERE id=?",(scene_id,)).fetchone()
        return Scene.from_record(row) if row else None

    def list_for_project(self, project_id: str) -> list[Scene]:
        with self.database.connect() as c:
            rows=c.execute("SELECT * FROM scenes WHERE project_id=? ORDER BY scene_order,id",(project_id,)).fetchall()
        return [Scene.from_record(row) for row in rows]

    def list_enabled(self, project_id: str) -> list[Scene]:
        with self.database.connect() as c:
            rows=c.execute("SELECT * FROM scenes WHERE project_id=? AND enabled=1 ORDER BY scene_order,id",(project_id,)).fetchall()
        return [Scene.from_record(row) for row in rows]

    def layers(self, scene_id: str) -> list[SceneLayer]:
        with self.database.connect() as c:
            rows=c.execute("SELECT * FROM scene_layers WHERE scene_id=? ORDER BY layer_order,id",(scene_id,)).fetchall()
        return [SceneLayer.from_record(row) for row in rows]

    def overlays(self, scene_id: str) -> list[SceneOverlay]:
        with self.database.connect() as c:
            rows=c.execute("SELECT * FROM scene_overlays WHERE scene_id=? ORDER BY overlay_order,id",(scene_id,)).fetchall()
        return [SceneOverlay.from_record(row) for row in rows]

    def update(self, scene: Scene) -> Scene:
        scene.validate(); scene.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE scenes SET scene_order=?,name=?,duration_ms=?,enabled=?,primary_media_id=?,background_media_id=?,narration_audio_id=?,subtitle_track_id=?,script_section_id=?,transcript_segment_id=?,translation_segment_id=?,source_hash=?,source_status=?,fit_mode=?,source_start_ms=?,source_end_ms=?,background_color=?,transition_in_json=?,transition_out_json=?,audio_json=?,status=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?""", self._scene_values(scene, include_identity=False)+(scene.id,scene.project_id))
            if cur.rowcount==0: raise KeyError("Scene does not belong to this project.")
        return scene

    def save_order(self, project_id: str, scenes: list[Scene]) -> None:
        with self.database.connect() as c,c:
            # temporary negative values avoid unique-order collisions
            for i,scene in enumerate(scenes):
                c.execute("UPDATE scenes SET scene_order=? WHERE id=? AND project_id=?",(-100000-i,scene.id,project_id))
            for i,scene in enumerate(scenes):
                scene.order=i; scene.updated_at=utc_now_iso()
                c.execute("UPDATE scenes SET scene_order=?,updated_at=? WHERE id=? AND project_id=?",(i,scene.updated_at,scene.id,project_id))

    def delete(self, project_id: str, scene_id: str) -> None:
        with self.database.connect() as c,c:
            cur=c.execute("DELETE FROM scenes WHERE id=? AND project_id=?",(scene_id,project_id))
            if cur.rowcount==0: raise KeyError("Scene does not belong to this project.")

    def replace_layers(self, project_id: str, scene_id: str, layers: list[SceneLayer]) -> None:
        self._assert_owner(project_id,scene_id)
        with self.database.connect() as c,c:
            c.execute("DELETE FROM scene_layers WHERE scene_id=?",(scene_id,))
            for i,layer in enumerate(layers):
                layer.scene_id=scene_id; layer.order=i; layer.validate(); self._insert_layer(c,layer)

    def replace_overlays(self, project_id: str, scene_id: str, overlays: list[SceneOverlay], duration_ms: int | None=None) -> None:
        self._assert_owner(project_id,scene_id)
        with self.database.connect() as c,c:
            c.execute("DELETE FROM scene_overlays WHERE scene_id=?",(scene_id,))
            for i,overlay in enumerate(overlays):
                overlay.scene_id=scene_id; overlay.order=i; overlay.validate(duration_ms); self._insert_overlay(c,overlay)

    def update_overlay(self, project_id: str, overlay: SceneOverlay, duration_ms: int | None=None) -> SceneOverlay:
        overlay.validate(duration_ms)
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE scene_overlays SET overlay_order=?,overlay_type=?,text=?,secondary_text=?,asset_id=?,x=?,y=?,width=?,height=?,opacity=?,rotation=?,visible=?,start_offset_ms=?,end_offset_ms=?,style_json=?,metadata_json=? WHERE id=? AND scene_id IN (SELECT id FROM scenes WHERE project_id=?)""", self._overlay_values(overlay, include_identity=False)+(overlay.id,project_id))
            if cur.rowcount==0: raise KeyError("Overlay does not belong to this project.")
        return overlay

    def add_overlay(self, project_id: str, overlay: SceneOverlay, duration_ms: int | None=None) -> SceneOverlay:
        self._assert_owner(project_id,overlay.scene_id); overlay.validate(duration_ms)
        with self.database.connect() as c,c: self._insert_overlay(c,overlay)
        return overlay

    def delete_overlay(self, project_id: str, overlay_id: str) -> None:
        with self.database.connect() as c,c:
            cur=c.execute("DELETE FROM scene_overlays WHERE id=? AND scene_id IN (SELECT id FROM scenes WHERE project_id=?)",(overlay_id,project_id))
            if cur.rowcount==0: raise KeyError("Overlay does not belong to this project.")

    def count_for_project(self, project_id: str) -> int:
        with self.database.connect() as c: row=c.execute("SELECT COUNT(*) AS n FROM scenes WHERE project_id=?",(project_id,)).fetchone()
        return int(row['n'] if row else 0)

    def _assert_owner(self, project_id: str, scene_id: str) -> None:
        with self.database.connect() as c: row=c.execute("SELECT 1 FROM scenes WHERE id=? AND project_id=?",(scene_id,project_id)).fetchone()
        if row is None: raise KeyError("Scene does not belong to this project.")

    @staticmethod
    def _scene_values(scene: Scene, include_identity: bool=True) -> tuple[object,...]:
        persisted=(scene.project_id,scene.order,scene.name,scene.duration_ms,int(scene.enabled),scene.primary_media_id,scene.background_media_id,scene.narration_audio_id,scene.subtitle_track_id,scene.script_section_id,scene.transcript_segment_id,scene.translation_segment_id,scene.source_hash,scene.source_status_code,scene.fit_mode,scene.source_start_ms,scene.source_end_ms,scene.background_color,json.dumps(scene.transition_in.to_dict(),separators=(",",":")),json.dumps(scene.transition_out.to_dict(),separators=(",",":")),json.dumps(scene.audio.to_dict(),separators=(",",":")),scene.status_code,json.dumps(scene.metadata,ensure_ascii=False,separators=(",",":")),scene.created_at,scene.updated_at)
        if include_identity:
            return (scene.id,)+persisted
        # UPDATE excludes project_id and immutable created_at.
        return persisted[1:23]+(persisted[24],)

    @classmethod
    def _insert_scene(cls,c,scene:Scene):
        c.execute("""INSERT INTO scenes(id,project_id,scene_order,name,duration_ms,enabled,primary_media_id,background_media_id,narration_audio_id,subtitle_track_id,script_section_id,transcript_segment_id,translation_segment_id,source_hash,source_status,fit_mode,source_start_ms,source_end_ms,background_color,transition_in_json,transition_out_json,audio_json,status,metadata_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",cls._scene_values(scene))

    @staticmethod
    def _layer_values(layer:SceneLayer, include_identity:bool=True):
        values=(layer.scene_id,layer.order,layer.type_code,layer.asset_id,layer.x,layer.y,layer.width,layer.height,layer.opacity,layer.rotation,int(layer.visible),json.dumps(layer.metadata,ensure_ascii=False,separators=(",",":")))
        return ((layer.id,)+values) if include_identity else values

    @classmethod
    def _insert_layer(cls,c,layer):
        c.execute("INSERT INTO scene_layers(id,scene_id,layer_order,layer_type,asset_id,x,y,width,height,opacity,rotation,visible,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",cls._layer_values(layer))

    @staticmethod
    def _overlay_values(overlay:SceneOverlay, include_identity:bool=True):
        values=(overlay.scene_id,overlay.order,overlay.type_code,overlay.text,overlay.secondary_text,overlay.asset_id,overlay.x,overlay.y,overlay.width,overlay.height,overlay.opacity,overlay.rotation,int(overlay.visible),overlay.start_offset_ms,overlay.end_offset_ms,json.dumps(overlay.style,ensure_ascii=False,separators=(",",":")),json.dumps(overlay.metadata,ensure_ascii=False,separators=(",",":")))
        return ((overlay.id,)+values) if include_identity else values[1:]

    @classmethod
    def _insert_overlay(cls,c,overlay):
        c.execute("INSERT INTO scene_overlays(id,scene_id,overlay_order,overlay_type,text,secondary_text,asset_id,x,y,width,height,opacity,rotation,visible,start_offset_ms,end_offset_ms,style_json,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",cls._overlay_values(overlay))

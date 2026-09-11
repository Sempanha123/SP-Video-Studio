from __future__ import annotations

import json
from copy import deepcopy
from uuid import uuid4

from domain.project import utc_now_iso
from domain.timeline import Timeline
from domain.timeline_marker import TimelineMarker
from domain.timeline_track import DEFAULT_TRACKS, TimelineTrack
from storage.database import SQLiteDatabase


class TimelineRepository:
    def __init__(self, database: SQLiteDatabase) -> None: self.database=database

    def get_state(self, project_id: str) -> Timeline:
        with self.database.connect() as c,c:
            row=c.execute("SELECT * FROM timeline_state WHERE project_id=?",(project_id,)).fetchone()
            if row is None:
                c.execute("INSERT INTO timeline_state(project_id) VALUES(?)",(project_id,))
                row=c.execute("SELECT * FROM timeline_state WHERE project_id=?",(project_id,)).fetchone()
        return Timeline.from_record(row)

    def save_state(self, state: Timeline) -> Timeline:
        state.validate()
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO timeline_state(project_id,zoom_level,playhead_ms,scroll_position,snap_enabled,snap_threshold_px,active_track_id,selected_clip_id,metadata_json)
                         VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET zoom_level=excluded.zoom_level,playhead_ms=excluded.playhead_ms,scroll_position=excluded.scroll_position,snap_enabled=excluded.snap_enabled,snap_threshold_px=excluded.snap_threshold_px,active_track_id=excluded.active_track_id,selected_clip_id=excluded.selected_clip_id,metadata_json=excluded.metadata_json""",
                      (state.project_id,state.zoom_level,state.playhead_ms,state.scroll_position,int(state.snap_enabled),state.snap_threshold_px,state.active_track_id,state.selected_clip_id,json.dumps(state.metadata,ensure_ascii=False,separators=(",",":"))))
        return state

    def ensure_tracks(self, project_id: str) -> list[TimelineTrack]:
        with self.database.connect() as c,c:
            existing={str(r["track_type"]) for r in c.execute("SELECT track_type FROM timeline_tracks WHERE project_id=?",(project_id,)).fetchall()}
            for order,(kind,name) in enumerate(DEFAULT_TRACKS):
                if kind in existing: continue
                item=TimelineTrack(project_id=project_id,track_type=kind,name=name,order=order)
                c.execute("INSERT INTO timeline_tracks(id,project_id,track_type,name,track_order,visible,muted,locked,height,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (item.id,item.project_id,item.type_code,item.name,item.order,int(item.visible),int(item.muted),int(item.locked),item.height,"{}"))
        return self.list_tracks(project_id)

    def list_tracks(self, project_id: str) -> list[TimelineTrack]:
        with self.database.connect() as c:
            rows=c.execute("SELECT * FROM timeline_tracks WHERE project_id=? ORDER BY track_order,id",(project_id,)).fetchall()
        return [TimelineTrack.from_record(r) for r in rows]

    def track_by_type(self, project_id: str, track_type: str) -> TimelineTrack | None:
        with self.database.connect() as c:
            row=c.execute("SELECT * FROM timeline_tracks WHERE project_id=? AND track_type=?",(project_id,track_type)).fetchone()
        return TimelineTrack.from_record(row) if row else None

    def update_track(self, track: TimelineTrack) -> TimelineTrack:
        track.validate()
        with self.database.connect() as c,c:
            cur=c.execute("UPDATE timeline_tracks SET name=?,track_order=?,visible=?,muted=?,locked=?,height=?,metadata_json=? WHERE id=? AND project_id=?",
                          (track.name,track.order,int(track.visible),int(track.muted),int(track.locked),track.height,json.dumps(track.metadata,ensure_ascii=False,separators=(",",":")),track.id,track.project_id))
            if cur.rowcount==0: raise KeyError("Timeline track does not belong to this project.")
        return track

    def markers(self, project_id: str) -> list[TimelineMarker]:
        with self.database.connect() as c:
            rows=c.execute("SELECT * FROM timeline_markers WHERE project_id=? ORDER BY time_ms,id",(project_id,)).fetchall()
        return [TimelineMarker.from_record(r) for r in rows]

    def add_marker(self, marker: TimelineMarker) -> TimelineMarker:
        marker.validate()
        with self.database.connect() as c,c:
            c.execute("INSERT INTO timeline_markers(id,project_id,time_ms,label,color,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                      (marker.id,marker.project_id,marker.time_ms,marker.label,marker.color,json.dumps(marker.metadata,ensure_ascii=False,separators=(",",":")),marker.created_at,marker.updated_at))
        return marker

    def update_marker(self, marker: TimelineMarker) -> TimelineMarker:
        marker.validate(); marker.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            cur=c.execute("UPDATE timeline_markers SET time_ms=?,label=?,color=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?",
                          (marker.time_ms,marker.label,marker.color,json.dumps(marker.metadata,ensure_ascii=False,separators=(",",":")),marker.updated_at,marker.id,marker.project_id))
            if cur.rowcount==0: raise KeyError("Timeline marker does not belong to this project.")
        return marker

    def delete_marker(self, project_id: str, marker_id: str) -> None:
        with self.database.connect() as c,c:
            cur=c.execute("DELETE FROM timeline_markers WHERE id=? AND project_id=?",(marker_id,project_id))
            if cur.rowcount==0: raise KeyError("Timeline marker does not belong to this project.")

    def duplicate_project(self, source_project_id: str, target_project_id: str) -> dict[str,str]:
        result: dict[str,str]={}
        state=self.get_state(source_project_id)
        clone=deepcopy(state); clone.project_id=target_project_id; clone.active_track_id=""; clone.selected_clip_id=""; clone.playhead_ms=0; clone.scroll_position=0
        self.save_state(clone)
        source_tracks=self.ensure_tracks(source_project_id)
        target_tracks={t.type_code:t for t in self.ensure_tracks(target_project_id)}
        for source in source_tracks:
            target=target_tracks[source.type_code]; target.visible=source.visible; target.muted=source.muted; target.locked=source.locked; target.height=source.height; target.metadata=deepcopy(source.metadata); self.update_track(target); result[source.id]=target.id
        for marker in self.markers(source_project_id):
            item=deepcopy(marker); item.marker_id=str(uuid4()); item.project_id=target_project_id; item.created_at=item.updated_at=utc_now_iso(); self.add_marker(item); result[marker.id]=item.id
        return result

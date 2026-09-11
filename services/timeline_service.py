from __future__ import annotations

from copy import deepcopy

from domain.timeline_marker import TimelineMarker
from services.timeline_edit_service import TimelineEditService
from services.timeline_mapping_service import TimelineMappingService
from services.timeline_snap_service import TimelineSnapService
from services.timeline_validation_service import TimelineValidationService
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.timeline_repository import TimelineRepository


class TimelineService:
    def __init__(self,repository:TimelineRepository,projects:ProjectRepository,mapping:TimelineMappingService,edits:TimelineEditService,snapping:TimelineSnapService|None=None,validation:TimelineValidationService|None=None) -> None:
        self.repository=repository; self.projects=projects; self.mapping=mapping; self.edits=edits; self.snapping=snapping or TimelineSnapService(); self.validation=validation or TimelineValidationService()

    def load(self,project_id:str)->dict:
        self._project(project_id); tracks=self.repository.ensure_tracks(project_id); state=self.repository.get_state(project_id); state.duration_ms=self.mapping.duration_ms(project_id); state.validate(); clips=self.mapping.build_clips(project_id); flat=[clip for values in clips.values() for clip in values]; issues=self.validation.validate_clips(flat,state.duration_ms)
        return {"state":state,"tracks":tracks,"clips":clips,"markers":self.repository.markers(project_id),"issues":issues}

    def save_editor_state(self,project_id:str,*,playhead_ms:int|None=None,zoom_level:float|None=None,scroll_position:float|None=None,snap_enabled:bool|None=None,selected_clip_id:str|None=None,active_track_id:str|None=None):
        self._project(project_id); state=self.repository.get_state(project_id); state.duration_ms=self.mapping.duration_ms(project_id)
        if playhead_ms is not None: state.playhead_ms=max(0,min(int(playhead_ms),state.duration_ms))
        if zoom_level is not None: state.zoom_level=float(zoom_level)
        if scroll_position is not None: state.scroll_position=float(scroll_position)
        if snap_enabled is not None: state.snap_enabled=bool(snap_enabled)
        if selected_clip_id is not None: state.selected_clip_id=str(selected_clip_id)
        if active_track_id is not None: state.active_track_id=str(active_track_id)
        return self.repository.save_state(state)

    def snap_time(self,project_id:str,value_ms:int,pixels_per_second:float,*,include_playhead:int|None=None)->int:
        targets=[0,self.mapping.duration_ms(project_id)]
        for item in self.mapping.scene_ranges(project_id): targets.extend([int(item["startMs"]),int(item["endMs"])])
        targets.extend(m.time_ms for m in self.repository.markers(project_id))
        if include_playhead is not None: targets.append(int(include_playhead))
        return self.snapping.snap(value_ms,targets,pixels_per_second,self.repository.get_state(project_id).snap_threshold_px).time_ms

    def add_marker(self,project_id:str,time_ms:int,label:str="Marker")->TimelineMarker:
        self._project(project_id); duration=self.mapping.duration_ms(project_id); item=TimelineMarker(project_id,max(0,min(int(time_ms),duration)),label.strip() or "Marker"); return self.repository.add_marker(item)
    def update_marker(self,project_id:str,marker_id:str,time_ms:int,label:str)->TimelineMarker:
        item=next((x for x in self.repository.markers(project_id) if x.id==marker_id),None)
        if item is None: raise KeyError("Marker could not be found.")
        item.time_ms=max(0,min(int(time_ms),self.mapping.duration_ms(project_id))); item.label=label.strip() or "Marker"; return self.repository.update_marker(item)
    def delete_marker(self,project_id:str,marker_id:str)->None: self.repository.delete_marker(project_id,marker_id)

    def duplicate_project_timeline(self,source_project_id:str,target_project_id:str)->dict[str,str]: return self.repository.duplicate_project(source_project_id,target_project_id)
    def project_to_scene_time(self,project_id:str,project_ms:int): return self.mapping.project_to_scene_time(project_id,project_ms)
    def scene_to_project_time(self,project_id:str,scene_id:str,local_ms:int)->int: return self.mapping.scene_to_project_time(project_id,scene_id,local_ms)
    def get_scene_at_time(self,project_id:str,project_ms:int): return self.mapping.get_scene_at_time(project_id,project_ms)
    def active_overlays(self,project_id:str,project_ms:int): return self.mapping.get_active_overlays(project_id,project_ms)
    def active_subtitles(self,project_id:str,project_ms:int): return self.mapping.get_active_subtitle_cues(project_id,project_ms)
    def duration_ms(self,project_id:str)->int: return self.mapping.duration_ms(project_id)
    def frame_step_ms(self,project_id:str)->int:
        project=self._project(project_id); return max(1,int(round(1000.0/max(1.0,float(project.fps or 30.0)))))
    def quantize_to_frame(self,project_id:str,time_ms:int)->int:
        project=self._project(project_id); return self.mapping.quantize_to_frame(time_ms,float(project.fps or 30.0))

    def _project(self,project_id:str):
        project=self.projects.get_by_id(project_id)
        if project is None: raise KeyError("Project could not be found.")
        return project

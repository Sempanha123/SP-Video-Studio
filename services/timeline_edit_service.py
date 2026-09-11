from __future__ import annotations

from copy import deepcopy

from commands.command_stack import CommandStack
from commands.timeline.commands import TimelineCommand, ValueCommand
from domain.scene_transition import SceneTransition
from services.scene_service import SceneInvalidSourceRange, SceneService
from services.subtitle_service import SubtitleService
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.timeline_repository import TimelineRepository


class TimelineInvalidOperation(RuntimeError): pass
class TimelineClipLocked(TimelineInvalidOperation): pass
class TimelineInvalidTrim(TimelineInvalidOperation): pass
class TimelineInvalidSplit(TimelineInvalidOperation): pass
class TimelineSourceMissing(TimelineInvalidOperation): pass
class TimelineTransitionConflict(TimelineInvalidOperation): pass


class TimelineEditService:
    """Command-backed edits against the canonical scene/subtitle/overlay records."""
    def __init__(self, scenes:SceneService, scene_repository:SceneRepository, subtitles:SubtitleService, subtitle_repository:SubtitleRepository, timeline:TimelineRepository, stack:CommandStack|None=None) -> None:
        self.scenes=scenes; self.scene_repository=scene_repository; self.subtitles=subtitles; self.subtitle_repository=subtitle_repository; self.timeline=timeline; self.stack=stack or CommandStack(150)

    def clear_history(self)->None: self.stack.clear()
    def undo(self)->bool: return self.stack.undo()
    def redo(self)->bool: return self.stack.redo()

    def _track_locked(self,project_id:str,kind:str)->bool:
        track=self.timeline.track_by_type(project_id,kind); return bool(track and track.locked)
    def _guard(self,project_id:str,kind:str)->None:
        if self._track_locked(project_id,kind): raise TimelineClipLocked("This track is locked.")

    def reorder_scene(self,project_id:str,scene_id:str,new_index:int)->None:
        self._guard(project_id,"video"); scenes=self.scene_repository.list_for_project(project_id); old=next((i for i,s in enumerate(scenes) if s.id==scene_id),None)
        if old is None: raise TimelineSourceMissing("Scene could not be found.")
        target=max(0,min(int(new_index),len(scenes)-1))
        if target==old:return
        self.scenes.move_scene(project_id,scene_id,target)
        self.stack.push_executed(TimelineCommand("Reorder Scene",lambda:self.scenes.move_scene(project_id,scene_id,target),lambda:self.scenes.move_scene(project_id,scene_id,old)))

    def trim_scene_right(self,project_id:str,scene_id:str,new_duration_ms:int)->None:
        self._guard(project_id,"video"); scene=deepcopy(self.scenes.get(project_id,scene_id)[0]); new=max(100,int(new_duration_ms))
        if new==scene.duration_ms:return
        media=self.scenes.media_repository.get_by_id(scene.primary_media_id) if scene.primary_media_id else None
        old=deepcopy(scene)
        def apply(value:int):
            current=self.scenes.get(project_id,scene_id)[0]
            if media and media.type=="video":
                end=current.source_start_ms+value
                if media.duration_ms and end>media.duration_ms: raise TimelineInvalidTrim("The source video does not contain enough media to extend this clip.")
                self.scenes.set_video_range(project_id,scene_id,current.source_start_ms,end)
            self.scenes.update_general(project_id,scene_id,duration_ms=value)
        apply(new)
        def restore(): self.scene_repository.update(deepcopy(old))
        self.stack.push_executed(TimelineCommand("Trim Scene",lambda:apply(new),restore))

    def trim_scene_left(self,project_id:str,scene_id:str,trim_ms:int)->None:
        self._guard(project_id,"video"); scene=deepcopy(self.scenes.get(project_id,scene_id)[0]); amount=max(0,int(trim_ms))
        if amount<=0:return
        if amount>=scene.duration_ms-99: raise TimelineInvalidTrim("A clip must remain at least 100 ms long.")
        old=deepcopy(scene); media=self.scenes.media_repository.get_by_id(scene.primary_media_id) if scene.primary_media_id else None
        new_duration=scene.duration_ms-amount
        if media and media.type=="video":
            new_start=scene.source_start_ms+amount
            end=scene.source_end_ms if scene.source_end_ms is not None else scene.source_start_ms+scene.duration_ms
            if end<=new_start: raise TimelineInvalidTrim("The selected trim would remove the whole source range.")
            self.scenes.set_video_range(project_id,scene_id,new_start,end)
        self.scenes.update_general(project_id,scene_id,duration_ms=new_duration)
        def redo():
            if media and media.type=="video":
                end=old.source_end_ms if old.source_end_ms is not None else old.source_start_ms+old.duration_ms
                self.scenes.set_video_range(project_id,scene_id,old.source_start_ms+amount,end)
            self.scenes.update_general(project_id,scene_id,duration_ms=new_duration)
        self.stack.push_executed(TimelineCommand("Trim Scene Start",redo,lambda:self.scene_repository.update(deepcopy(old))))

    def split_scene(self,project_id:str,scene_id:str,local_ms:int)->str:
        self._guard(project_id,"video"); original,layers,overlays=self.scenes.get(project_id,scene_id); original=deepcopy(original); layers=deepcopy(layers); overlays=deepcopy(overlays)
        split=int(local_ms)
        if split<100 or split>original.duration_ms-100: raise TimelineInvalidSplit("The playhead must be inside the selected clip.")
        clone=self.scenes.duplicate_scene(project_id,scene_id); clone_id=clone.id
        # First half.
        if original.primary_media_id:
            media=self.scenes.media_repository.get_by_id(original.primary_media_id)
            if media and media.type=="video": self.scenes.set_video_range(project_id,scene_id,original.source_start_ms,original.source_start_ms+split)
        self.scenes.update_general(project_id,scene_id,duration_ms=split)
        self.scenes.set_transition(project_id,scene_id,"cut",0)
        # Second half.
        second=self.scenes.get(project_id,clone_id)[0]
        if original.primary_media_id:
            media=self.scenes.media_repository.get_by_id(original.primary_media_id)
            if media and media.type=="video":
                end=original.source_end_ms if original.source_end_ms is not None else original.source_start_ms+original.duration_ms
                self.scenes.set_video_range(project_id,clone_id,original.source_start_ms+split,end)
        self.scenes.update_general(project_id,clone_id,name=f"{original.name} - Part 2",duration_ms=original.duration_ms-split)
        self.scene_repository.update(self._with_transition_out(self.scenes.get(project_id,clone_id)[0],deepcopy(original.transition_out)))
        self.scenes.set_transition(project_id,clone_id,"cut",0,outgoing=False)
        # Do not play the same generated narration twice after splitting a scene.
        if original.narration_audio_id: self.scenes.assign_narration(project_id,clone_id,"")
        self._split_overlays(project_id,scene_id,clone_id,overlays,split,original.duration_ms)
        first_after=deepcopy(self.scenes.get(project_id,scene_id)[0]); first_layers=deepcopy(self.scene_repository.layers(scene_id)); first_overlays=deepcopy(self.scene_repository.overlays(scene_id))
        second_after=deepcopy(self.scenes.get(project_id,clone_id)[0]); second_layers=deepcopy(self.scene_repository.layers(clone_id)); second_overlays=deepcopy(self.scene_repository.overlays(clone_id))
        old_order=[s.id for s in self.scene_repository.list_for_project(project_id)]
        def undo():
            if self.scene_repository.get(clone_id): self.scene_repository.delete(project_id,clone_id)
            self.scene_repository.update(deepcopy(original)); self.scene_repository.replace_layers(project_id,scene_id,deepcopy(layers)); self.scene_repository.replace_overlays(project_id,scene_id,deepcopy(overlays),original.duration_ms); self._restore_order(project_id,[x for x in old_order if x!=clone_id])
        def redo():
            self.scene_repository.update(deepcopy(first_after)); self.scene_repository.replace_layers(project_id,scene_id,deepcopy(first_layers)); self.scene_repository.replace_overlays(project_id,scene_id,deepcopy(first_overlays),first_after.duration_ms)
            if self.scene_repository.get(clone_id) is None:
                item=deepcopy(second_after); item.order=len(self.scene_repository.list_for_project(project_id)); self.scene_repository.create(item,deepcopy(second_layers),deepcopy(second_overlays))
            self._restore_order(project_id,old_order)
        self.stack.push_executed(TimelineCommand("Split Scene",redo,undo)); return clone_id

    @staticmethod
    def _with_transition_out(scene,transition): scene.transition_out=transition; return scene

    def _split_overlays(self,project_id:str,first_id:str,second_id:str,original_overlays:list,split:int,total:int)->None:
        for item in list(self.scene_repository.overlays(first_id)):
            src=next((x for x in original_overlays if x.text==item.text and x.order==item.order and x.type_code==item.type_code),None)
            if src is None: continue
            if src.start_offset_ms>=split: self.scenes.delete_overlay(project_id,first_id,item.id)
            else: self.scenes.update_overlay(project_id,first_id,item.id,{"endOffsetMs":min(split,src.end_offset_ms)})
        for item in list(self.scene_repository.overlays(second_id)):
            src=next((x for x in original_overlays if x.text==item.text and x.order==item.order and x.type_code==item.type_code),None)
            if src is None: continue
            if src.end_offset_ms<=split: self.scenes.delete_overlay(project_id,second_id,item.id)
            else: self.scenes.update_overlay(project_id,second_id,item.id,{"startOffsetMs":max(0,src.start_offset_ms-split),"endOffsetMs":max(1,src.end_offset_ms-split)})

    def delete_scene(self,project_id:str,scene_id:str)->None:
        self._guard(project_id,"video"); scene,layers,overlays=self.scenes.get(project_id,scene_id); snapshot=(deepcopy(scene),deepcopy(layers),deepcopy(overlays)); old_order=[s.id for s in self.scene_repository.list_for_project(project_id)]
        self.scenes.delete_scene(project_id,scene_id)
        def undo():
            scene0,layers0,overlays0=deepcopy(snapshot); scene0.order=len(self.scene_repository.list_for_project(project_id)); self.scene_repository.create(scene0,layers0,overlays0); self._restore_order(project_id,old_order)
        self.stack.push_executed(TimelineCommand("Delete Scene",lambda:self.scenes.delete_scene(project_id,scene_id),undo))

    def duplicate_scene(self,project_id:str,scene_id:str)->str:
        self._guard(project_id,"video"); clone=self.scenes.duplicate_scene(project_id,scene_id); cid=clone.id; scene,layers,overlays=self.scenes.get(project_id,cid); snapshot=(deepcopy(scene),deepcopy(layers),deepcopy(overlays)); order=[s.id for s in self.scene_repository.list_for_project(project_id)]
        def redo():
            if self.scene_repository.get(cid) is None:
                s,l,o=deepcopy(snapshot); s.order=len(self.scene_repository.list_for_project(project_id)); self.scene_repository.create(s,l,o); self._restore_order(project_id,order)
        self.stack.push_executed(TimelineCommand("Duplicate Scene",redo,lambda:self.scenes.delete_scene(project_id,cid))); return cid

    def set_scene_audio(self,project_id:str,scene_id:str,*,narration_volume:float|None=None,source_volume:float|None=None,narration_enabled:bool|None=None,source_enabled:bool|None=None)->None:
        kind="voice" if narration_volume is not None or narration_enabled is not None else "source_audio"; self._guard(project_id,kind); before=deepcopy(self.scenes.get(project_id,scene_id)[0].audio)
        self.scenes.set_audio(project_id,scene_id,narration_volume=narration_volume,source_volume=source_volume,narration_enabled=narration_enabled,source_enabled=source_enabled)
        after=deepcopy(self.scenes.get(project_id,scene_id)[0].audio)
        def apply(audio): self.scenes.set_audio(project_id,scene_id,narration_volume=audio.narration_volume,source_volume=audio.source_audio_volume,narration_enabled=audio.narration_enabled,source_enabled=audio.source_audio_enabled)
        self.stack.push_executed(ValueCommand("Audio Settings",apply,before,after,f"audio:{scene_id}:{kind}"))

    def delete_overlay(self,project_id:str,scene_id:str,overlay_id:str)->None:
        self._guard(project_id,"overlay"); scene=self.scenes.get(project_id,scene_id)[0]
        overlays=self.scene_repository.overlays(scene_id); item=next((x for x in overlays if x.id==overlay_id),None)
        if item is None: raise TimelineSourceMissing("Overlay could not be found.")
        snapshot=deepcopy(item); old_order=[x.id for x in overlays]
        self.scenes.delete_overlay(project_id,scene_id,overlay_id)
        def undo():
            restored=deepcopy(snapshot); restored.order=len(self.scene_repository.overlays(scene_id)); self.scene_repository.add_overlay(project_id,restored,scene.duration_ms)
            current={x.id:x for x in self.scene_repository.overlays(scene_id)}; ordered=[current[i] for i in old_order if i in current]; ordered.extend(x for x in current.values() if x.id not in old_order)
            self.scene_repository.replace_overlays(project_id,scene_id,ordered,scene.duration_ms)
        self.stack.push_executed(TimelineCommand("Delete Overlay",lambda:self.scenes.delete_overlay(project_id,scene_id,overlay_id),undo))

    def set_overlay_timing(self,project_id:str,scene_id:str,overlay_id:str,start_ms:int,end_ms:int)->None:
        self._guard(project_id,"overlay"); scene=self.scenes.get(project_id,scene_id)[0]; item=next((x for x in self.scene_repository.overlays(scene_id) if x.id==overlay_id),None)
        if item is None: raise TimelineSourceMissing("Overlay could not be found.")
        before=(item.start_offset_ms,item.end_offset_ms); start=max(0,int(start_ms)); end=min(scene.duration_ms,int(end_ms))
        if end<=start: raise TimelineInvalidTrim("Overlay timing must remain inside the scene.")
        self.scenes.update_overlay(project_id,scene_id,overlay_id,{"startOffsetMs":start,"endOffsetMs":end}); after=(start,end)
        setter=lambda pair:self.scenes.update_overlay(project_id,scene_id,overlay_id,{"startOffsetMs":pair[0],"endOffsetMs":pair[1]})
        self.stack.push_executed(ValueCommand("Overlay Timing",setter,before,after,f"overlay:{overlay_id}:timing"))

    def set_subtitle_timing(self,project_id:str,cue_id:str,start_ms:int,end_ms:int)->None:
        self._guard(project_id,"subtitle"); cue=self.subtitle_repository.cue(cue_id)
        if cue is None: raise TimelineSourceMissing("Subtitle cue could not be found.")
        track=self.subtitle_repository.get_track(cue.track_id)
        if track is None or track.project_id!=project_id: raise TimelineSourceMissing("Subtitle cue does not belong to this project.")
        before=(cue.start_ms,cue.end_ms); start=max(0,int(start_ms)); end=int(end_ms)
        if end<=start: raise TimelineInvalidTrim("Subtitle end must be after start.")
        self.subtitles.update_cue(project_id,cue.track_id,cue.id,start_ms=start,end_ms=end); after=(start,end)
        setter=lambda pair:self.subtitles.update_cue(project_id,cue.track_id,cue.id,start_ms=pair[0],end_ms=pair[1])
        self.stack.push_executed(ValueCommand("Subtitle Timing",setter,before,after,f"subtitle:{cue_id}:timing"))

    def set_transition(self,project_id:str,scene_id:str,kind:str,duration_ms:int)->None:
        self._guard(project_id,"video"); before=deepcopy(self.scenes.get(project_id,scene_id)[0].transition_out)
        self.scenes.set_transition(project_id,scene_id,kind,duration_ms); after=deepcopy(self.scenes.get(project_id,scene_id)[0].transition_out)
        setter=lambda t:self.scenes.set_transition(project_id,scene_id,t.type_code,t.duration_ms,direction=t.direction)
        self.stack.push_executed(ValueCommand("Transition",setter,before,after,f"transition:{scene_id}"))

    def set_track_state(self,project_id:str,track_type:str,*,locked:bool|None=None,muted:bool|None=None,visible:bool|None=None,height:int|None=None)->None:
        track=self.timeline.track_by_type(project_id,track_type)
        if track is None: raise TimelineSourceMissing("Timeline track could not be found.")
        before=deepcopy(track)
        if locked is not None: track.locked=bool(locked)
        if muted is not None: track.muted=bool(muted)
        if visible is not None: track.visible=bool(visible)
        if height is not None: track.height=int(height)
        self.timeline.update_track(track); after=deepcopy(track)
        self.stack.push_executed(ValueCommand("Track Settings",self.timeline.update_track,before,after,f"track:{track.id}"))

    def _restore_order(self,project_id:str,ids:list[str])->None:
        by={s.id:s for s in self.scene_repository.list_for_project(project_id)}; ordered=[by[i] for i in ids if i in by]; ordered.extend(s for s in by.values() if s.id not in ids); self.scene_repository.save_order(project_id,ordered)

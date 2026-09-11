from __future__ import annotations
import logging
from copy import deepcopy
from commands.command_stack import CommandStack
from commands.timeline.commands import TimelineCommand, ValueCommand
from domain.project import utc_now_iso
from domain.story_beat import StoryBeat, BEAT_TYPES, BEAT_EMOTIONS
from domain.story_outline import StoryOutline
from services.story_errors import StoryBeatInvalid, StoryOutlineMissing
from services.story_planner import DeterministicStoryPlanner, STORY_STRUCTURE_TEMPLATES
from services.story_service import StoryService
from storage.repositories.story_repository import StoryRepository

class StoryOutlineService:
    def __init__(self,repository:StoryRepository,story_service:StoryService,planner:DeterministicStoryPlanner|None=None,logger=None)->None:
        self.repository=repository;self.story_service=story_service;self.planner=planner or DeterministicStoryPlanner();self.logger=logger or logging.getLogger("sp_video_studio.story_outline");self.commands=CommandStack(150)
    def latest(self,project_id:str)->tuple[StoryOutline|None,list[StoryBeat]]:
        self.story_service.load_or_create(project_id);outline=self.repository.latest_outline(project_id);return outline,self.repository.beats(outline.id) if outline else []
    def create_from_plan(self,project_id:str,*,replace:bool=False,template_id:str|None=None)->tuple[StoryOutline,list[StoryBeat]]:
        meta=self.story_service.load_or_create(project_id);old=self.repository.latest_outline(project_id)
        if old and not replace:return old,self.repository.beats(old.id)
        if old and replace:self.repository.delete_outline(project_id,old.id)
        outline=StoryOutline(project_id=project_id,title=meta.title.strip() or "Story Outline",summary=meta.idea,status="review",source_fingerprint=meta.planning_fingerprint(),metadata={"templateId":template_id or self.planner.template_for(meta.story_type)})
        plan=self.planner.plan(meta,outline_id=outline.id,template_id=template_id);self.repository.create_outline(outline,plan.beats);return outline,plan.beats
    def approve(self,project_id:str,outline_id:str)->StoryOutline:
        item=self._outline(project_id,outline_id);item.status="approved";item.source_fingerprint=self.story_service.load_or_create(project_id).planning_fingerprint();return self.repository.save_outline(item)
    def add_beat(self,project_id:str,outline_id:str,title:str="New Beat",beat_type:str="custom",duration_ms:int=5000)->StoryBeat:
        outline=self._outline(project_id,outline_id);beats=self.repository.beats(outline.id);beat=StoryBeat(outline.id,len(beats),beat_type if beat_type in BEAT_TYPES else "custom",title.strip() or "New Beat",target_duration_ms=max(1,int(duration_ms)),user_modified=True)
        self.repository.add_beat(project_id,beat)
        self.commands.push_executed(TimelineCommand("Add Story Beat",lambda:self.repository.add_beat(project_id,beat),lambda:self.repository.delete_beat(project_id,beat.id)))
        return beat
    def update_beat(self,project_id:str,beat_id:str,**changes)->StoryBeat:
        beat=self._beat(project_id,beat_id);before=deepcopy(beat)
        for key in ("title","description","beat_type","target_duration_ms","emotion","visual_direction","chapter_title","character_id","voice_override_id","notes","locked"):
            if key in changes and changes[key] is not None:setattr(beat,key,changes[key])
        beat.target_duration_ms=int(beat.target_duration_ms);beat.user_modified=True
        try:beat.validate()
        except ValueError as exc:raise StoryBeatInvalid(str(exc)) from exc
        self.repository.save_beat(project_id,beat);self._mark_links_changed(project_id,beat,before.source_hash())
        after=deepcopy(beat)
        self.commands.push_executed(TimelineCommand("Edit Story Beat",lambda:self.repository.save_beat(project_id,deepcopy(after)),lambda:self.repository.save_beat(project_id,deepcopy(before))))
        return beat
    def set_locked(self,project_id:str,beat_id:str,locked:bool)->StoryBeat:
        return self.update_beat(project_id,beat_id,locked=bool(locked))
    def move_beat(self,project_id:str,beat_id:str,new_index:int)->list[StoryBeat]:
        beat=self._beat(project_id,beat_id);beats=self.repository.beats(beat.outline_id);before=[b.id for b in beats];idx=next(i for i,b in enumerate(beats) if b.id==beat_id);item=beats.pop(idx);beats.insert(max(0,min(int(new_index),len(beats))),item);self.repository.save_order(project_id,beat.outline_id,beats);after=[b.id for b in beats]
        def apply(order):
            current={b.id:b for b in self.repository.beats(beat.outline_id)};self.repository.save_order(project_id,beat.outline_id,[current[i] for i in order if i in current])
        self.commands.push_executed(TimelineCommand("Reorder Story Beat",lambda:apply(after),lambda:apply(before)));return self.repository.beats(beat.outline_id)
    def duplicate_beat(self,project_id:str,beat_id:str)->StoryBeat:
        source=self._beat(project_id,beat_id);beats=self.repository.beats(source.outline_id);idx=next(i for i,b in enumerate(beats) if b.id==beat_id);clone=deepcopy(source);from uuid import uuid4
        clone.beat_id=str(uuid4());clone.title=f"{source.title} Copy";clone.script_section_id="";clone.locked=False;clone.user_modified=True;clone.created_at=clone.updated_at=utc_now_iso();beats.insert(idx+1,clone);self.repository.replace_beats(project_id,source.outline_id,beats)
        order_after=[b.id for b in self.repository.beats(source.outline_id)]
        snapshot=deepcopy(clone)
        def undo():
            self.repository.delete_beat(project_id,snapshot.id);self.repository.save_order(project_id,source.outline_id,self.repository.beats(source.outline_id))
        def redo():
            if self.repository.beat(project_id,snapshot.id) is None:self.repository.add_beat(project_id,deepcopy(snapshot))
            current={b.id:b for b in self.repository.beats(source.outline_id)};self.repository.save_order(project_id,source.outline_id,[current[i] for i in order_after if i in current])
        self.commands.push_executed(TimelineCommand("Duplicate Story Beat",redo,undo));return clone
    def delete_beat(self,project_id:str,beat_id:str)->dict[str,int]:
        beat=deepcopy(self._beat(project_id,beat_id));links=deepcopy(self.repository.mappings(project_id,beat_id=beat_id));order_before=[b.id for b in self.repository.beats(beat.outline_id)]
        self.repository.delete_beat(project_id,beat_id);self.repository.save_order(project_id,beat.outline_id,self.repository.beats(beat.outline_id))
        def undo():
            if self.repository.beat(project_id,beat.id) is None:self.repository.add_beat(project_id,deepcopy(beat))
            current={b.id:b for b in self.repository.beats(beat.outline_id)};self.repository.save_order(project_id,beat.outline_id,[current[i] for i in order_before if i in current])
            for m in links:self.repository.save_mapping(project_id,beat.id,str(m['mappingType']),str(m['targetId']),str(m['sourceHash']),str(m['status']),dict(m['metadata']),str(m['id']))
        def redo():
            if self.repository.beat(project_id,beat.id) is not None:self.repository.delete_beat(project_id,beat.id)
            self.repository.save_order(project_id,beat.outline_id,self.repository.beats(beat.outline_id))
        self.commands.push_executed(TimelineCommand("Delete Story Beat",redo,undo))
        return {"scriptLinks":sum(1 for x in links if x['mappingType']=='script_section'),"sceneLinks":sum(1 for x in links if x['mappingType']=='scene')}
    def fit_to_target(self,project_id:str,outline_id:str)->list[StoryBeat]:
        meta=self.story_service.load_or_create(project_id);beats=self.repository.beats(outline_id)
        locked_total=sum(b.target_duration_ms for b in beats if b.locked);unlocked=[b for b in beats if not b.locked];target=max(0,meta.target_duration_ms-locked_total)
        if not unlocked:
            if locked_total!=meta.target_duration_ms:raise StoryBeatInvalid("Locked beats already exceed or differ from the target duration.")
            return beats
        current=sum(b.target_duration_ms for b in unlocked) or len(unlocked);factor=target/current
        vals=[max(1000,round(b.target_duration_ms*factor)) for b in unlocked];diff=target-sum(vals);i=0
        while diff and vals:
            idx=i%len(vals);step=1 if diff>0 else -1
            if step>0 or vals[idx]>1000:vals[idx]+=step;diff-=step
            i+=1
            if i>abs(target)+len(vals)*4:break
        for beat,value in zip(unlocked,vals):beat.target_duration_ms=value;beat.user_modified=True;self.repository.save_beat(project_id,beat)
        return self.repository.beats(outline_id)
    def apply_template(self,project_id:str,outline_id:str,template_id:str,mode:str="replace")->list[StoryBeat]:
        if template_id not in STORY_STRUCTURE_TEMPLATES:raise StoryBeatInvalid("Unknown Story structure template.")
        meta=self.story_service.load_or_create(project_id);outline=self._outline(project_id,outline_id);planned=self.planner.plan(meta,outline_id=outline_id,template_id=template_id).beats
        if mode=="append":
            current=self.repository.beats(outline_id);offset=len(current)
            for i,b in enumerate(planned):b.order=offset+i
            self.repository.replace_beats(project_id,outline_id,current+planned)
        elif mode=="replace":self.repository.replace_beats(project_id,outline_id,planned)
        else:raise StoryBeatInvalid("Choose Replace Outline or Append Structure.")
        outline.version+=1;outline.status="review";outline.metadata["templateId"]=template_id;self.repository.save_outline(outline);return self.repository.beats(outline_id)
    def refresh_structure(self,project_id:str,outline_id:str)->list[StoryBeat]:
        meta=self.story_service.load_or_create(project_id);outline=self._outline(project_id,outline_id);old=self.repository.beats(outline_id);fresh=self.planner.plan(meta,outline_id=outline_id,template_id=str(outline.metadata.get("templateId") or self.planner.template_for(meta.story_type))).beats
        # Preserve locked/user-modified beats in their positions; only unlocked planner beats refresh.
        result=[]
        for i,item in enumerate(fresh):
            prior=old[i] if i<len(old) else None
            if prior and (prior.locked or prior.user_modified):result.append(prior)
            else:result.append(item)
        for prior in old[len(fresh):]:
            if prior.locked or prior.user_modified:result.append(prior)
        self.repository.replace_beats(project_id,outline_id,result);outline.version+=1;outline.status="review";outline.source_fingerprint=meta.planning_fingerprint();self.repository.save_outline(outline);return self.repository.beats(outline_id)
    def undo(self)->bool:return self.commands.undo()
    def redo(self)->bool:return self.commands.redo()
    def _mark_links_changed(self,project_id:str,beat:StoryBeat,old_hash:str)->None:
        if beat.source_hash()==old_hash:return
        for m in self.repository.mappings(project_id,beat_id=beat.id):self.repository.update_mapping_status(project_id,str(m['id']),"source_changed")
        if beat.script_section_id:
            # Script section itself remains untouched; StoryScriptService exposes the changed state.
            pass
    def _outline(self,project_id,outline_id):
        item=self.repository.outline(project_id,outline_id)
        if item is None:raise StoryOutlineMissing("Story outline could not be found.")
        return item
    def _beat(self,project_id,beat_id):
        item=self.repository.beat(project_id,beat_id)
        if item is None:raise StoryBeatInvalid("Story beat could not be found.")
        return item

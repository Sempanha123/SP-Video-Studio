from __future__ import annotations
from dataclasses import dataclass
from domain.story_beat import StoryBeat
from domain.story_project import StoryProjectMetadata

STORY_STRUCTURE_TEMPLATES={
    "5_beat_story": [("hook","Hook"),("setup","Setup"),("development","Development"),("climax","Climax"),("resolution","Resolution")],
    "explainer": [("hook","Hook"),("problem","Problem"),("context","Context"),("explanation","Explanation"),("example","Example"),("outro","Summary")],
    "documentary": [("hook","Hook"),("context","Background"),("development","Development"),("context","Context"),("current_state","Current State"),("outro","Closing")],
    "motivational": [("hook","Hook"),("problem","Problem"),("struggle","Struggle"),("turning_point","Turning Point"),("lesson","Lesson"),("outro","Closing")],
    "mystery_short": [("hook","Hook"),("setup","Setup"),("discovery","Discovery"),("turning_point","Reveal"),("resolution","Resolution")],
    "educational": [("hook","Hook"),("context","Context"),("explanation","Explanation"),("example","Example"),("lesson","Lesson"),("outro","Outro")],
}
TYPE_TEMPLATE={
    "short_story":"5_beat_story","documentary_story":"documentary","educational_story":"educational",
    "motivational_story":"motivational","mystery":"mystery_short","explainer_story":"explainer",
    "drama":"5_beat_story","adventure":"5_beat_story","biography_style":"documentary","custom":"5_beat_story",
}
VOICE_CATEGORY={"short_story":"Storyteller","documentary_story":"Documentary","educational_story":"Educational","motivational_story":"Warm","mystery":"Dramatic"}
SUBTITLE_PRESET={"documentary_story":"documentary","educational_story":"clean","short_story":"clean","motivational_story":"creator","mystery":"minimal"}
WEIGHTS={"hook":0.65,"setup":1.0,"context":1.15,"character":1.0,"development":1.35,"problem":1.0,"struggle":1.25,"conflict":1.2,"discovery":1.0,"turning_point":1.0,"climax":1.1,"explanation":1.25,"example":1.05,"lesson":0.85,"current_state":1.0,"resolution":0.85,"outro":0.65,"closing":0.65,"custom":1.0}

@dataclass(frozen=True,slots=True)
class StoryPlan:
    beats:list[StoryBeat]
    voice_category:str
    subtitle_preset:str
    visual_pacing:str

class DeterministicStoryPlanner:
    def template_for(self,story_type:str)->str:return TYPE_TEMPLATE.get(story_type,"5_beat_story")
    def recommended_count(self,duration_ms:int,pace:str)->int:
        sec=max(1,duration_ms/1000)
        if sec<=30:base=4
        elif sec<=90:base=6
        elif sec<=180:base=10
        elif sec<=300:base=14
        else:base=min(24,max(14,round(sec/22)))
        if pace=="fast":base+=1
        elif pace=="slow":base=max(3,base-1)
        return base
    def plan(self,meta:StoryProjectMetadata,*,outline_id:str="",template_id:str|None=None)->StoryPlan:
        template=template_id or self.template_for(meta.story_type); core=list(STORY_STRUCTURE_TEMPLATES.get(template,STORY_STRUCTURE_TEMPLATES["5_beat_story"]))
        count=max(len(core),self.recommended_count(meta.target_duration_ms,meta.pace)); structure=self._expand(core,count)
        durations=self._durations([kind for kind,_ in structure],meta.target_duration_ms)
        beats=[]
        for i,((kind,title),duration) in enumerate(zip(structure,durations)):
            desc=self._description(kind,meta.idea,meta.language)
            beats.append(StoryBeat(outline_id=outline_id,order=i,beat_type=kind,title=title,description=desc,target_duration_ms=duration,metadata={"planner":"deterministic","templateId":template}))
        return StoryPlan(beats,VOICE_CATEGORY.get(meta.story_type,"Storyteller"),SUBTITLE_PRESET.get(meta.story_type,"clean"),meta.pace)
    def _expand(self,core,count):
        if count<=len(core):return core[:count]
        result=list(core); insert=max(1,len(result)-2); n=2
        while len(result)<count:
            kind="development" if any(x[0]=="development" for x in result) else "context"
            result.insert(insert,(kind,f"Development {n}" if kind=="development" else f"Context {n}"));insert+=1;n+=1
        return result
    def _durations(self,kinds,total):
        weights=[WEIGHTS.get(k,1.0) for k in kinds];unit=total/sum(weights);vals=[max(1000,round(unit*w)) for w in weights];diff=total-sum(vals)
        order=sorted(range(len(vals)),key=lambda i:weights[i],reverse=True);step=1 if diff>0 else -1
        while diff:
            changed=False
            for i in order:
                if not diff:break
                if step<0 and vals[i]<=1000:continue
                vals[i]+=step;diff-=step;changed=True
            if not changed:break
        return vals
    @staticmethod
    def _description(kind,idea,language):
        idea=idea.strip()
        if not idea:return ""
        if language=="km":return idea if kind in {"hook","setup"} else ""
        prompts={"hook":"Open with the most engaging part of the idea.","setup":"Establish the situation and context.","development":"Develop the central idea.","climax":"Present the strongest turning point.","resolution":"Resolve the main development.","lesson":"State the useful takeaway.","outro":"Close the story clearly."}
        return prompts.get(kind,"")

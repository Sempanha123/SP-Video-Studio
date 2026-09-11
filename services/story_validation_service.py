from __future__ import annotations
from dataclasses import dataclass
from services.script_analysis_service import ScriptAnalysisService
from storage.repositories.story_repository import StoryRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.generated_audio_repository import GeneratedAudioRepository

@dataclass(frozen=True,slots=True)
class StoryValidationIssue:
    code:str;message:str;severity:str='warning'
    def to_dict(self):return {"code":self.code,"message":self.message,"severity":self.severity}

class StoryValidationService:
    def __init__(self,repository:StoryRepository,script_repository:ScriptRepository,scene_repository:SceneRepository,subtitle_repository:SubtitleRepository,audio_repository:GeneratedAudioRepository,analysis:ScriptAnalysisService)->None:
        self.repository=repository;self.script_repository=script_repository;self.scene_repository=scene_repository;self.subtitle_repository=subtitle_repository;self.audio_repository=audio_repository;self.analysis=analysis
    def validate(self,project_id:str)->dict[str,object]:
        issues=[];meta=self.repository.get_project(project_id);outline=self.repository.latest_outline(project_id)
        if meta is None:return {"level":"not_ready","issues":[StoryValidationIssue('story_missing','Story setup is incomplete.','error').to_dict()]}
        if not meta.title.strip() or not meta.idea.strip():issues.append(StoryValidationIssue('idea_missing','Add a Story title and idea.','error'))
        beats=self.repository.beats(outline.id) if outline else []
        if outline is None:issues.append(StoryValidationIssue('outline_missing','Create a Story outline.','error'))
        elif outline.status!='approved':issues.append(StoryValidationIssue('outline_review','Approve the Story outline before production.'))
        if outline and outline.source_fingerprint!=meta.planning_fingerprint():issues.append(StoryValidationIssue('outline_outdated','Story settings changed after this outline was created.'))
        script=self.script_repository.get_primary_by_project(project_id);sections=self.script_repository.list_sections(script.id) if script else []
        if not script or not any(s.content.strip() for s in sections):issues.append(StoryValidationIssue('script_missing','Create or write the Story script.','error'))
        estimate=0
        if script:estimate=self.analysis.analyze_sections(sections,script.language,str(script.pace)).estimated_duration_ms
        if estimate and abs(estimate-meta.target_duration_ms)>max(15000,meta.target_duration_ms*.3):issues.append(StoryValidationIssue('duration_mismatch','Estimated narration duration differs from the Story target.'))
        if not meta.narrator_voice_id:issues.append(StoryValidationIssue('voice_missing','Choose a narrator voice.'))
        audio_count=len(self.audio_repository.list_for_project(project_id));scene_count=self.scene_repository.count_for_project(project_id);subtitle_count=len(self.subtitle_repository.list_for_project(project_id))
        if not scene_count:issues.append(StoryValidationIssue('scenes_missing','Create Story scenes.'))
        level='not_ready' if any(i.severity=='error' for i in issues) else ('needs_review' if issues else 'ready')
        return {"level":level,"issues":[i.to_dict() for i in issues],"beatCount":len(beats),"outlineStatus":outline.status if outline else 'missing',"estimatedDurationMs":estimate,"narrationCount":audio_count,"sceneCount":scene_count,"subtitleCount":subtitle_count,"voiceSelected":bool(meta.narrator_voice_id)}

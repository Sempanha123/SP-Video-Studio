from __future__ import annotations
import logging
from domain.director_plan import DirectorRequest
from domain.project import utc_now_iso
from services.story_errors import StoryOutlineMissing
from storage.repositories.story_repository import StoryRepository
from services.scene_service import SceneService
from services.script_service import ScriptService
from services.ai_director_service import AIDirectorService

class StoryApplyService:
    def __init__(self,repository:StoryRepository,scene_service:SceneService,script_service:ScriptService,director_service:AIDirectorService|None=None,logger=None)->None:
        self.repository=repository;self.scene_service=scene_service;self.script_service=script_service;self.director_service=director_service;self.logger=logger or logging.getLogger("sp_video_studio.story_apply")
    def create_scenes_from_outline(self,project_id:str,outline_id:str,*,append:bool=True)->list[object]:
        outline=self.repository.outline(project_id,outline_id)
        if outline is None:raise StoryOutlineMissing("Story outline could not be found.")
        beats=self.repository.beats(outline_id);existing=self.scene_service.list_scenes(project_id)
        linked={str(m['beatId']) for m in self.repository.mappings(project_id,mapping_type='scene')}
        created=[]
        for beat in beats:
            if beat.id in linked:continue
            scene=self.scene_service.add_scene(project_id,beat.title,beat.target_duration_ms)
            scene.metadata.update({"storyRole":beat.beat_type,"storyBeatId":beat.id,"emotion":beat.emotion,"visualDirection":beat.visual_direction,"sourceType":"story_beat","storyBeatSourceHash":beat.source_hash()})
            if beat.script_section_id:scene.script_section_id=beat.script_section_id
            scene.source_hash=beat.source_hash();scene.updated_at=utc_now_iso();self.scene_service.repository.update(scene)
            self.repository.save_mapping(project_id,beat.id,"scene",scene.id,beat.source_hash(),metadata={"initialDurationMs":beat.target_duration_ms});created.append(scene)
        return created
    def director_plan(self,project_id:str,*,platform:str='generic'):
        if self.director_service is None:raise StoryOutlineMissing("AI Director is unavailable.")
        meta=self.repository.get_project(project_id);outline=self.repository.latest_outline(project_id)
        if meta is None or outline is None:raise StoryOutlineMissing("Approve a Story outline first.")
        script=self.script_service.repository.get_primary_by_project(project_id)
        if script:
            req=DirectorRequest(project_id=project_id,workflow='story',content_source_type='script',content_source_id=script.id,language=meta.language,platform=platform,target_duration_ms=meta.target_duration_ms,audience=meta.audience if meta.audience in {'general','young','professional','educational'} else 'general',style='storytelling',pace=meta.pace,tone=meta.tone if meta.tone in {'warm','calm','dramatic','inspirational','serious','friendly','suspenseful','educational','neutral'} else 'neutral')
        else:
            req=DirectorRequest(project_id=project_id,workflow='story',content_source_type='idea',content_text=meta.idea or meta.title,language=meta.language,platform=platform,target_duration_ms=meta.target_duration_ms,audience='general',style='storytelling',pace=meta.pace,tone=meta.tone if meta.tone in {'warm','calm','dramatic','inspirational','serious','friendly','suspenseful','educational','neutral'} else 'neutral')
        return self.director_service.create_plan(req)
    def translation_context(self,project_id:str)->dict[str,object]:
        script=self.script_service.repository.get_primary_by_project(project_id)
        mappings=self.repository.mappings(project_id,mapping_type='script_section')
        return {"scriptId":script.id if script else "","sectionToBeat":{str(m['targetId']):str(m['beatId']) for m in mappings}}

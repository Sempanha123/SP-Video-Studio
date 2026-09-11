from __future__ import annotations
import logging
from copy import deepcopy
from domain.project import ProjectWorkflow, utc_now_iso
from domain.story_project import StoryProjectMetadata, STORY_TYPES, STORY_TONES, STORY_AUDIENCES, STORY_PACES
from domain.story_character import StoryCharacter, CHARACTER_ROLES
from services.story_errors import StoryInvalidSetup, StoryMappingError
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.story_repository import StoryRepository

class StoryService:
    def __init__(self,repository:StoryRepository,project_repository:ProjectRepository,voice_service=None,logger=None)->None:
        self.repository=repository;self.project_repository=project_repository;self.voice_service=voice_service;self.logger=logger or logging.getLogger("sp_video_studio.story")
    def load_or_create(self,project_id:str)->StoryProjectMetadata:
        project=self.project_repository.get_by_id(project_id)
        if project is None:raise StoryInvalidSetup("Project could not be found.")
        if str(project.workflow)!=ProjectWorkflow.STORY.value:raise StoryInvalidSetup("Story Studio is available for Story projects.")
        item=self.repository.get_project(project_id)
        if item:
            if not item.narrator_voice_id and self.voice_service is not None:
                try:
                    assigned=self.voice_service.resolve_voice(project_id)
                    if assigned is not None:item.narrator_voice_id=assigned.voice_id;item.updated_at=utc_now_iso();self.repository.save_project(item)
                except Exception:pass
            return item
        item=StoryProjectMetadata(project_id=project_id,title=project.title,language=project.language)
        if self.voice_service is not None:
            try:
                assigned=self.voice_service.resolve_voice(project_id)
                if assigned is not None:item.narrator_voice_id=assigned.voice_id
            except Exception:pass
        item.source_fingerprint=item.planning_fingerprint();self.repository.save_project(item);return item
    def update_setup(self,project_id:str,**changes)->StoryProjectMetadata:
        item=self.load_or_create(project_id);before=item.planning_fingerprint()
        for key in ("title","idea","story_type","language","target_duration_ms","audience","tone","pace","notes"):
            if key in changes and changes[key] is not None:setattr(item,key,changes[key])
        try:item.target_duration_ms=int(item.target_duration_ms);item.validate()
        except Exception as exc:raise StoryInvalidSetup(str(exc)) from exc
        current=item.planning_fingerprint();item.source_fingerprint=current;item.updated_at=utc_now_iso();self.repository.save_project(item)
        if current!=before:
            outline=self.repository.latest_outline(project_id)
            if outline and outline.source_fingerprint!=current and outline.status!="outdated":outline.status="outdated";self.repository.save_outline(outline)
        return item
    def set_narrator_voice(self,project_id:str,voice_id:str)->StoryProjectMetadata:
        item=self.load_or_create(project_id)
        if voice_id and self.voice_service is not None:self.voice_service.assign_project(project_id,voice_id)
        item.narrator_voice_id=voice_id;item.updated_at=utc_now_iso();return self.repository.save_project(item)
    def add_character(self,project_id:str,name:str,role:str="other",description:str="",voice_id:str="",notes:str="")->StoryCharacter:
        self.load_or_create(project_id)
        if role not in CHARACTER_ROLES:raise StoryInvalidSetup("Choose a supported character role.")
        if voice_id and self.voice_service is not None:self.voice_service.get(voice_id)
        item=StoryCharacter(project_id=project_id,name=name.strip(),role=role,description=description,voice_id=voice_id,notes=notes)
        try:item.validate()
        except ValueError as exc:raise StoryInvalidSetup(str(exc)) from exc
        return self.repository.save_character(item)
    def update_character(self,project_id:str,character_id:str,**changes)->StoryCharacter:
        item=self.repository.character(project_id,character_id)
        if item is None:raise StoryMappingError("Character could not be found.")
        for key in ("name","role","description","voice_id","notes"):
            if key in changes:setattr(item,key,changes[key])
        item.validate();return self.repository.save_character(item)
    def delete_character(self,project_id:str,character_id:str)->None:self.repository.delete_character(project_id,character_id)
    def overview(self,project_id:str)->dict[str,object]:
        meta=self.load_or_create(project_id);outline=self.repository.latest_outline(project_id);beats=self.repository.beats(outline.id) if outline else [];mappings=self.repository.mappings(project_id)
        return {**meta.to_dict(),"outlineId":outline.id if outline else "","outlineStatus":outline.status if outline else "missing","beatCount":len(beats),"outlineDurationMs":sum(b.target_duration_ms for b in beats),"characterCount":len(self.repository.characters(project_id)),"scriptLinkCount":sum(1 for m in mappings if m['mappingType']=='script_section'),"sceneLinkCount":sum(1 for m in mappings if m['mappingType']=='scene')}
    def duplicate_project_story(self,source_project_id:str,target_project_id:str,*,section_map:dict[str,str]|None=None,scene_map:dict[str,str]|None=None):
        return self.repository.duplicate_project(source_project_id,target_project_id,section_map=section_map,scene_map=scene_map)

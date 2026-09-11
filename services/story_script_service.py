from __future__ import annotations
import logging
from domain.project import utc_now_iso
from domain.script_section import ScriptSection, ScriptSectionType
from services.story_errors import StoryApplyConflict, StoryOutlineMissing
from storage.repositories.story_repository import StoryRepository
from services.script_service import ScriptService
from services.voice_service import VoiceService

class StoryScriptService:
    def __init__(self,repository:StoryRepository,script_service:ScriptService,voice_service:VoiceService|None=None,logger=None)->None:
        self.repository=repository;self.script_service=script_service;self.voice_service=voice_service;self.logger=logger or logging.getLogger("sp_video_studio.story_script")
    def create_from_outline(self,project_id:str,outline_id:str,*,replace:bool=False)->tuple[object,list[ScriptSection]]:
        outline=self.repository.outline(project_id,outline_id)
        if outline is None:raise StoryOutlineMissing("Story outline could not be found.")
        beats=self.repository.beats(outline_id);script,existing=self.script_service.load_or_create(project_id)
        mapped=self.repository.mappings(project_id,mapping_type="script_section")
        has_story=bool(mapped)
        if not replace and not has_story and any(s.content.strip() for s in existing):raise StoryApplyConflict("A Story script already contains manual edits.")
        if replace or not has_story:
            sections=[]
            for order,beat in enumerate(beats):
                stype=ScriptSectionType.HOOK if beat.beat_type=="hook" else ScriptSectionType.OUTRO if beat.beat_type in {"outro","closing","resolution"} and order==len(beats)-1 else ScriptSectionType.BODY
                section=ScriptSection(script.id,order,stype,beat.title,content=beat.description,metadata={"storyBeatId":beat.id,"storyBeatSourceHash":beat.source_hash(),"storySourceStatus":"current","characterId":beat.character_id,"voiceOverrideId":beat.voice_override_id})
                sections.append(section)
            self.script_service.repository.replace_sections(project_id,script.id,sections)
            # Replace only Story mappings; old targets cascade/are harmless, but clear table rows explicitly.
            with self.repository.database.connect() as c,c:c.execute("DELETE FROM story_mappings WHERE project_id=? AND mapping_type='script_section'",(project_id,))
            for beat,section in zip(beats,sections):
                beat.script_section_id=section.id;self.repository.save_beat(project_id,beat);self.repository.save_mapping(project_id,beat.id,"script_section",section.id,beat.source_hash())
                if beat.voice_override_id and self.voice_service:self.voice_service.assign_section(project_id,section.id,beat.voice_override_id)
            script.metadata["storyOutlineId"]=outline.id;script.metadata["storyWorkflow"]=True;script.updated_at=utc_now_iso();self.script_service.save_script(script)
            return script,sections
        return self.sync(project_id,outline_id)
    def sync(self,project_id:str,outline_id:str)->tuple[object,list[ScriptSection]]:
        script,sections=self.script_service.load_or_create(project_id);by_id={s.id:s for s in sections};beats=self.repository.beats(outline_id)
        for beat in beats:
            mappings=self.repository.mappings(project_id,mapping_type="script_section",beat_id=beat.id)
            if not mappings:
                section=self.script_service.add_section(project_id,beat.title,"body");section.content=beat.description;section.metadata.update({"storyBeatId":beat.id,"storyBeatSourceHash":beat.source_hash(),"storySourceStatus":"current"});self.script_service.save_section(project_id,section);beat.script_section_id=section.id;self.repository.save_beat(project_id,beat);self.repository.save_mapping(project_id,beat.id,"script_section",section.id,beat.source_hash());by_id[section.id]=section;continue
            for m in mappings:
                section=by_id.get(str(m['targetId'])) or self.script_service.repository.get_section(str(m['targetId']))
                if section is None:continue
                if str(m['sourceHash'])!=beat.source_hash():
                    section.metadata["storySourceStatus"]="source_changed";section.metadata["storyBeatId"]=beat.id;section.metadata["storyBeatSourceHash"]=str(m['sourceHash']);self.script_service.save_section(project_id,section);self.repository.update_mapping_status(project_id,str(m['id']),"source_changed")
        return script,self.script_service.repository.list_sections(script.id)
    def section_status(self,project_id:str,section_id:str)->dict[str,object]:
        m=self.repository.mapping_for_target(project_id,"script_section",section_id)
        if not m:return {"status":"unlinked"}
        beat=self.repository.beat(project_id,str(m['beatId']))
        status="source_missing" if beat is None else ("source_changed" if beat.source_hash()!=str(m['sourceHash']) else str(m['status']))
        return {**m,"status":status,"beat":beat.to_dict() if beat else {}}

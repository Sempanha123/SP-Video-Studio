from __future__ import annotations

from domain.director_plan import DirectorPlan
from engines.llm.errors import DirectorApplyConflict, DirectorPlanValidationError
from services.ai_director_service import AIDirectorService
from services.director_validation_service import DirectorValidationService
from services.project_service import ProjectService
from services.scene_service import SceneService
from services.subtitle_preset_service import SubtitlePresetService
from services.voice_service import VoiceService
from storage.repositories.director_plan_repository import DirectorPlanRepository


class DirectorApplyService:
    def __init__(self, director:AIDirectorService, repository:DirectorPlanRepository, validation:DirectorValidationService,
                 project_service:ProjectService, scene_service:SceneService, voice_service:VoiceService,
                 subtitle_presets:SubtitlePresetService) -> None:
        self.director=director; self.repository=repository; self.validation=validation; self.project_service=project_service
        self.scene_service=scene_service; self.voice_service=voice_service; self.subtitle_presets=subtitle_presets

    def impact(self, project_id:str, plan_id:str)->dict[str,object]:
        plan,scenes=self.director.get(project_id,plan_id); existing=self.scene_service.list_scenes(project_id)
        return {"aspectRatio":plan.aspect_ratio,"plannedScenes":len(scenes),"existingScenes":len(existing),"hasSceneConflict":bool(existing),"subtitlePreset":str((plan.recommendation("subtitles").value if plan.recommendation("subtitles") else "")),"voiceCategory":str((plan.recommendation("voice").value if plan.recommendation("voice") else ""))}

    def apply(self, project_id:str, plan_id:str, *, mode:str="settings_only", voice_id:str="", apply_subtitle_preference:bool=True)->dict[str,object]:
        plan,scene_plans=self.director.get(project_id,plan_id); issues=self.validation.validate(plan,scene_plans)
        if any(i.severity=="error" for i in issues): raise DirectorPlanValidationError("This production plan cannot be applied until its structural errors are fixed.")
        if mode not in {"settings_only","add_scenes","replace_scenes"}: raise DirectorApplyConflict("Choose how the plan should affect scenes.")
        existing=self.scene_service.list_scenes(project_id)
        if existing and mode=="replace_scenes":
            for scene in list(existing): self.scene_service.delete_scene(project_id,scene.id)
        self.project_service.update_creative_settings(project_id,aspect_ratio=plan.aspect_ratio)
        if voice_id:self.voice_service.assign_project(project_id,voice_id)
        if apply_subtitle_preference:
            rec=plan.recommendation("subtitles")
            if rec:
                preset_id=str(rec.value); available={str(p["id"]) for p in self.subtitle_presets.list_presets()}
                if preset_id in available:self.repository.set_default_subtitle_preset(project_id,preset_id)
        created=[]
        if mode in {"add_scenes","replace_scenes"}:
            for item in scene_plans:
                scene=self.scene_service.add_scene(project_id,item.title,item.target_duration_ms)
                scene.metadata.update({"directorPlanId":plan.id,"directorScenePlanId":item.id,"purpose":item.purpose,"visualDescription":item.visual_description,"overlayRecommendation":item.overlay_recommendation})
                if item.script_section_id:
                    section=self.scene_service.script_service.repository.get_section(item.script_section_id)
                    if section:
                        from services.scene_generation_service import script_section_source_hash
                        scene.script_section_id=item.script_section_id; scene.source_hash=script_section_source_hash(section); scene.metadata["sourceType"]="script"; scene.metadata["sourceTitle"]=section.title
                self.scene_service.repository.update(scene)
                self.scene_service.set_transition(project_id,scene.id,item.transition, min(500,max(0,item.target_duration_ms//8)))
                created.append(scene.id)
        applied=self.director.mark_applied(project_id,plan_id)
        return {"planId":applied.id,"mode":mode,"createdSceneIds":created,"aspectRatio":plan.aspect_ratio,"voiceId":voice_id,"subtitlePreset":self.repository.default_subtitle_preset(project_id)}

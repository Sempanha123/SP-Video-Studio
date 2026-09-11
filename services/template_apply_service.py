from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from domain.chroma_key import ChromaKeySettings
from domain.short_project import ShortProject
from domain.template import Template
from domain.template_asset import is_safe_relative_template_path
from domain.template_component import TemplateComponentType
from domain.template_errors import TemplateApplyError, TemplateCompatibilityError, TemplatePlaceholderUnresolved
from domain.template_placeholder import resolve_placeholders
from services.template_validation_service import TemplateValidationService


@dataclass(slots=True)
class TemplateApplyResult:
    project_id: str
    mapping: dict[str,str] = field(default_factory=dict)
    created_scene_ids: list[str] = field(default_factory=list)
    created_speaker_ids: list[str] = field(default_factory=list)
    created_subtitle_track_ids: list[str] = field(default_factory=list)
    imported_media_ids: list[str] = field(default_factory=list)
    unresolved_required: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    applied_components: list[str] = field(default_factory=list)
    recommendations: dict[str,Any] = field(default_factory=dict)

    @property
    def ready(self)->bool:return not self.unresolved_required
    def to_dict(self)->dict[str,Any]:
        return {"projectId":self.project_id,"mapping":dict(self.mapping),"createdSceneIds":list(self.created_scene_ids),"createdSpeakerIds":list(self.created_speaker_ids),"createdSubtitleTrackIds":list(self.created_subtitle_track_ids),"importedMediaIds":list(self.imported_media_ids),"unresolvedRequired":list(self.unresolved_required),"warnings":list(self.warnings),"appliedComponents":list(self.applied_components),"recommendations":dict(self.recommendations),"ready":self.ready}


class TemplateApplyService:
    """Apply reusable structure to authoritative Project/Scene/Speaker/Subtitle systems.

    It intentionally owns no renderer/timeline/subtitle implementation. Every applied value is copied into
    project-owned entities, so deleting/updating the template never changes existing projects.
    """
    def __init__(self,project_service,project_repository,scene_service,scene_repository,visual_layers,speakers,subtitles,validation:TemplateValidationService,template_repository,*,media_service=None,short_repository=None,export_presets=None,timeline_service=None,story_outline_service=None,news_visual_service=None) -> None:
        self.project_service=project_service; self.projects=project_repository; self.scenes=scene_service; self.scene_repository=scene_repository
        self.visual=visual_layers; self.speakers=speakers; self.subtitles=subtitles; self.validation=validation; self.repository=template_repository
        self.media_service=media_service; self.short_repository=short_repository; self.export_presets=export_presets; self.timeline_service=timeline_service; self.story_outline=story_outline_service; self.news_visual=news_visual_service
        self.failure_injector=None

    def impact_summary(self,item:Template,selected_components:Iterable[str]|None=None)->dict[str,int]:
        selected=set(selected_components or [x.type_code for x in item.components if x.enabled]); counts={"scenes":0,"speakers":0,"overlays":0,"visualLayers":0,"subtitleStyles":0,"timelineTracks":0}
        for comp in item.components:
            if not comp.enabled or comp.type_code not in selected: continue
            data=comp.data
            if comp.type_code==TemplateComponentType.SCENE_STRUCTURE.value:
                scenes=list(data.get("scenes") or []); counts["scenes"]+=len(scenes)
                counts["overlays"]+=sum(len(x.get("overlays") or []) for x in scenes if isinstance(x,dict)); counts["visualLayers"]+=sum(len(x.get("layers") or []) for x in scenes if isinstance(x,dict))
            elif comp.type_code==TemplateComponentType.SPEAKER_STRUCTURE.value: counts["speakers"]+=len(data.get("speakers") or [])
            elif comp.type_code==TemplateComponentType.SUBTITLE_STYLE.value: counts["subtitleStyles"]+=1
            elif comp.type_code==TemplateComponentType.TIMELINE_TRACKS.value: counts["timelineTracks"]+=len(data.get("tracks") or [])
        return counts

    def create_project_from_template(self,item:Template,title:str,language:str,aspect_ratio:str,*,resolutions:Mapping[str,Any]|None=None,selected_components:Iterable[str]|None=None,allow_unresolved:bool=True):
        compatibility=self.validation.compatibility(item,language=language,aspect_ratio=aspect_ratio)
        if compatibility["state"] in {"unsupported_version","missing_features"} and any(x["severity"]=="error" for x in compatibility["issues"]): raise TemplateCompatibilityError(compatibility["issues"][0]["message"])
        settings=next((c.data for c in item.components if c.type_code==TemplateComponentType.PROJECT_SETTINGS.value),{})
        fps=int(settings.get("fps",30) or 30)
        project=self.project_service.create_project(title,item.workflow,language,aspect_ratio,fps)
        try:
            result=self.apply_to_project(item,project.project_id,resolutions=resolutions,selected_components=selected_components,mode="create_new",allow_unresolved=allow_unresolved)
            return project,result
        except Exception:
            try:self.project_service.delete_project(project.project_id)
            except Exception:pass
            raise

    def apply_to_project(self,item:Template,project_id:str,*,resolutions:Mapping[str,Any]|None=None,selected_components:Iterable[str]|None=None,mode:str="merge",selected_scene_id:str="",allow_unresolved:bool=True,use_closest_layout:bool=False)->TemplateApplyResult:
        self.validation.validate(item); project=self.projects.get_by_id(project_id)
        if project is None: raise TemplateApplyError("Project could not be found.")
        if item.supported_aspect_ratios and project.aspect_ratio not in item.supported_aspect_ratios and not use_closest_layout:
            raise TemplateCompatibilityError(f"This template does not include a layout for {project.aspect_ratio}.")
        if mode not in {"create_new","merge","replace_selected_component"}: raise TemplateApplyError("Unsupported template application mode.")
        selected=set(selected_components or [x.type_code for x in item.components if x.enabled])
        resolution_map={"project_language":project.language,**dict(resolutions or {})}
        unresolved=[]
        for placeholder in item.placeholders:
            value=resolution_map.get(placeholder.id,placeholder.default_value)
            if value not in (None,""): resolution_map.setdefault(placeholder.id,value)
            elif placeholder.required: unresolved.append(placeholder.id)
        if unresolved and not allow_unresolved: raise TemplatePlaceholderUnresolved("Required template setup is incomplete: "+", ".join(unresolved))
        result=TemplateApplyResult(project_id,unresolved_required=list(unresolved))
        created_scenes=[]; created_speakers=[]; created_tracks=[]; imported_media=[]; scene_backups={}; subtitle_style_backups={}
        try:
            resolution_map=self._materialize_asset_resolutions(item,project_id,resolution_map,imported_media,result)
            # Speakers first so visual layers can reference mapped roles.
            components=[c for c in item.components if c.enabled and c.type_code in selected]
            priority={TemplateComponentType.SPEAKER_STRUCTURE.value:0,TemplateComponentType.SCENE_STRUCTURE.value:1,TemplateComponentType.SCENE_LAYOUT.value:2,TemplateComponentType.STORY_STRUCTURE.value:9,TemplateComponentType.NEWS_VISUAL_THEME.value:9}
            components.sort(key=lambda c:priority.get(c.type_code,5))
            for component in components:
                data=resolve_placeholders(component.data,resolution_map,preserve_unresolved=True)
                if component.type_code==TemplateComponentType.SPEAKER_STRUCTURE.value:
                    self._apply_speakers(project_id,data,resolution_map,result,created_speakers)
                elif component.type_code==TemplateComponentType.SCENE_STRUCTURE.value:
                    self._apply_scenes(project_id,data,resolution_map,result,created_scenes)
                elif component.type_code==TemplateComponentType.SCENE_LAYOUT.value:
                    if selected_scene_id:
                        self._apply_scene_layout(project_id,selected_scene_id,data,resolution_map,result,scene_backups)
                elif component.type_code==TemplateComponentType.SUBTITLE_STYLE.value:
                    self._apply_subtitle(project_id,data,project.language,result,created_tracks,subtitle_style_backups)
                elif component.type_code==TemplateComponentType.TRANSITION_STYLE.value:
                    self._apply_transitions(project_id,data,result,created_scenes,selected_scene_id)
                elif component.type_code==TemplateComponentType.TIMELINE_TRACKS.value:
                    self._apply_timeline(project_id,data,result)
                elif component.type_code==TemplateComponentType.SHORT_STYLE.value:
                    self._apply_short_style(project_id,data,project,result)
                elif component.type_code==TemplateComponentType.EXPORT_RECOMMENDATION.value:
                    result.recommendations["exportPresetId"]=str(data.get("presetId") or "")
                elif component.type_code==TemplateComponentType.NEWS_VISUAL_THEME.value:
                    self._apply_news_theme(project_id,data,result)
                elif component.type_code==TemplateComponentType.STORY_STRUCTURE.value:
                    self._apply_story_structure(project_id,data,result,mode)
                elif component.type_code==TemplateComponentType.PROJECT_SETTINGS.value:
                    result.recommendations["projectSettings"]=deepcopy(data)
                elif component.type_code in {TemplateComponentType.VISUAL_THEME.value,TemplateComponentType.SPEECH_BLOCK_STRUCTURE.value}:
                    result.recommendations[component.type_code]=deepcopy(data)
                result.applied_components.append(component.type_code)
                if self.failure_injector:self.failure_injector(component.type_code,result)
            self.repository.record_usage(item.id,project_id=project_id,template_version=item.version,metadata={"mapping":result.mapping,"unresolved":result.unresolved_required,"recommendations":result.recommendations,"mode":mode})
            return result
        except Exception as exc:
            # Compensating rollback across existing service-owned transactions.
            for track_id in reversed(created_tracks):
                try:self.subtitles.delete_track(project_id,track_id)
                except Exception:pass
            for track_id,style_data in subtitle_style_backups.items():
                try:self.subtitles.update_style(project_id,track_id,style_data)
                except Exception:pass
            for scene_id in reversed(created_scenes):
                try:self.scenes.delete_scene(project_id,scene_id)
                except Exception:pass
            for speaker_id in reversed(created_speakers):
                try:self.speakers.delete(project_id,speaker_id)
                except Exception:pass
            for media_id in reversed(imported_media):
                if self.media_service:
                    try:self.media_service.remove_media(project_id,media_id)
                    except Exception:pass
            for scene_id,snapshot in scene_backups.items():
                try:
                    scene,layers,overlays=snapshot; self.scene_repository.update(scene); self.scene_repository.replace_layers(project_id,scene_id,layers); self.scene_repository.replace_overlays(project_id,scene_id,overlays,scene.duration_ms)
                except Exception:pass
            if isinstance(exc,(TemplateApplyError,TemplateCompatibilityError,TemplatePlaceholderUnresolved)): raise
            raise TemplateApplyError(str(exc) or TemplateApplyError.user_message) from exc


    def _materialize_asset_resolutions(self,item:Template,project_id:str,resolutions:dict[str,Any],imported:list[str],result:TemplateApplyResult)->dict[str,Any]:
        if not self.media_service or not item.manifest_path:
            return resolutions
        root=Path(item.manifest_path).parent
        known={asset.relative_path:asset for asset in item.assets}
        output=dict(resolutions)
        for key,value in list(output.items()):
            if not isinstance(value,str) or not value.startswith("asset:"):
                continue
            relative=value[6:].replace("\\","/").strip("/")
            if relative not in known or not is_safe_relative_template_path(relative):
                raise TemplateApplyError(f"Template packaged asset is unavailable: {relative}")
            path=(root/"assets"/relative).resolve()
            asset_root=(root/"assets").resolve()
            if path!=asset_root and asset_root not in path.parents:
                raise TemplateApplyError("Template asset path escaped its package directory.")
            if not path.is_file():
                raise TemplateApplyError(f"Template packaged asset is unavailable: {relative}")
            media=self.media_service.import_file(project_id,path)
            output[key]=media.id; imported.append(media.id); result.imported_media_ids.append(media.id)
        return output

    def _apply_speakers(self,project_id:str,data:dict,resolutions:Mapping[str,Any],result:TemplateApplyResult,created:list[str])->None:
        for index,raw in enumerate(data.get("speakers") or []):
            local=str(raw.get("localId") or f"speaker_{index+1}"); role=str(raw.get("role") or "speaker"); language=str(raw.get("language") or resolutions.get("project_language") or "en")
            name=str(raw.get("name") or role.replace("_"," ").title()); voice_placeholder=str(raw.get("voicePlaceholder") or ""); voice_id=str(resolutions.get(voice_placeholder,"") or "") if voice_placeholder else ""
            item=self.speakers.create(project_id,name,role,language=language,voice_id=voice_id,description=str(raw.get("description") or "")); created.append(item.id); result.created_speaker_ids.append(item.id); result.mapping[local]=item.id
            if voice_placeholder and not voice_id: result.warnings.append(f"Voice Setup Required: {name}")

    def _apply_scenes(self,project_id:str,data:dict,resolutions:Mapping[str,Any],result:TemplateApplyResult,created:list[str])->None:
        for index,raw in enumerate(data.get("scenes") or []):
            local=str(raw.get("localId") or f"scene_{index+1}"); duration=max(250,int(raw.get("durationMs",raw.get("recommendedDurationMs",5000)) or 5000)); scene=self.scenes.add_scene(project_id,str(raw.get("name") or f"Scene {index+1}"),duration); created.append(scene.id); result.created_scene_ids.append(scene.id); result.mapping[local]=scene.id
            if raw.get("backgroundColor"): self.scenes.update_general(project_id,scene.id,background_color=str(raw["backgroundColor"]))
            primary=str(raw.get("primaryMediaPlaceholder") or ""); media_id=str(resolutions.get(primary,"") or "") if primary else ""
            if media_id:
                self.scenes.assign_media(project_id,scene.id,media_id,fit_mode=str(raw.get("fitMode") or "fill"))
            transition=dict(raw.get("transitionOut") or {})
            if transition:self.scenes.set_transition(project_id,scene.id,str(transition.get("type") or "cut"),int(transition.get("durationMs") or 0))
            self._add_overlays(project_id,scene.id,raw.get("overlays") or [],resolutions,result)
            self._add_layers(project_id,scene.id,raw.get("layers") or [],resolutions,result)

    def _add_overlays(self,project_id:str,scene_id:str,overlays:list,resolutions:Mapping[str,Any],result:TemplateApplyResult)->None:
        for index,raw in enumerate(overlays):
            kind=str(raw.get("type") or "body_text"); text=str(resolve_placeholders(raw.get("text") or "",resolutions,preserve_unresolved=False))
            secondary=str(resolve_placeholders(raw.get("secondaryText") or "",resolutions,preserve_unresolved=False))
            if kind=="lower_third": item=self.scenes.add_lower_third(project_id,scene_id,text,secondary)
            else:item=self.scenes.add_text_overlay(project_id,scene_id,text,kind if kind in {"headline","body_text","label","lower_third"} else "body_text")
            updates={k:raw[k] for k in ("x","y","width","height","opacity","rotation","visible") if k in raw}
            if "style" in raw:updates["style"]=dict(raw["style"])
            if "startMs" in raw:updates["startOffsetMs"]=int(raw["startMs"])
            if "endMs" in raw:updates["endOffsetMs"]=int(raw["endMs"])
            if updates:self.scenes.update_overlay(project_id,scene_id,item.id,updates)
            local=str(raw.get("localId") or f"overlay_{index+1}"); result.mapping[local]=item.id

    def _add_layers(self,project_id:str,scene_id:str,layers:list,resolutions:Mapping[str,Any],result:TemplateApplyResult)->None:
        for index,raw in enumerate(layers):
            placeholder=str(raw.get("mediaPlaceholder") or ""); media_id=str(resolutions.get(placeholder,"") or "") if placeholder else ""
            if not media_id: continue
            speaker_ref=str(raw.get("speakerLocalId") or ""); speaker_id=result.mapping.get(speaker_ref,"")
            item=self.visual.add_media_layer(project_id,scene_id,media_id,role=str(raw.get("role") or "overlay_video"),start_ms=int(raw.get("startMs") or 0),duration_ms=(int(raw["durationMs"]) if raw.get("durationMs") not in (None,"") else None),source_in_ms=int(raw.get("sourceInMs") or 0),pip_preset=(str(raw.get("pipPreset")) if raw.get("pipPreset") else None),speaker_id=speaker_id)
            updates={k:raw[k] for k in ("x","y","width","height","opacity","rotation","fitMode","useAudio","audioVolume") if k in raw}
            if updates:item=self.visual.update_layer(project_id,scene_id,item.id,updates)
            chroma=raw.get("chromaKey")
            if isinstance(chroma,dict) and chroma.get("enabled"): item=self.visual.set_chroma_key(project_id,scene_id,item.id,ChromaKeySettings.from_dict(chroma))
            local=str(raw.get("localId") or f"layer_{index+1}"); result.mapping[local]=item.id

    def _apply_scene_layout(self,project_id:str,scene_id:str,data:dict,resolutions:Mapping[str,Any],result:TemplateApplyResult,backups:dict)->None:
        scene,layers,overlays=self.scenes.get(project_id,scene_id)
        if scene_id not in backups:backups[scene_id]=(deepcopy(scene),deepcopy(layers),deepcopy(overlays))
        if bool(data.get("replaceLayers",False)):self.scene_repository.replace_layers(project_id,scene_id,[])
        if bool(data.get("replaceOverlays",False)):self.scene_repository.replace_overlays(project_id,scene_id,[],scene.duration_ms)
        self._add_overlays(project_id,scene_id,data.get("overlays") or [],resolutions,result); self._add_layers(project_id,scene_id,data.get("layers") or [],resolutions,result)

    def _apply_subtitle(self,project_id:str,data:dict,language:str,result:TemplateApplyResult,created:list[str],style_backups:dict[str,dict[str,Any]])->None:
        preset=str(data.get("presetId") or "clean"); tracks=self.subtitles.list_tracks(project_id); target=next((x for x in tracks if getattr(x,"is_default",False)),tracks[0] if tracks else None)
        if target is None:
            target=self.subtitles.create_manual(project_id,language,name=str(data.get("name") or "Template Subtitles"),preset_id=preset); created.append(target.id); result.created_subtitle_track_ids.append(target.id)
        else:
            if target.id not in style_backups:
                _,old_style,_=self.subtitles.get(project_id,target.id)
                old=old_style.to_dict(); style_backups[target.id]={k:v for k,v in old.items() if k not in {"id","project_id","created_at","updated_at"}}
            self.subtitles.apply_preset(project_id,target.id,preset)
        style=data.get("style")
        if isinstance(style,dict) and style:self.subtitles.update_style(project_id,target.id,dict(style))
        result.mapping[str(data.get("localId") or "subtitle_style")]=target.id

    def _apply_transitions(self,project_id:str,data:dict,result:TemplateApplyResult,created_scenes:list[str],selected_scene_id:str)->None:
        kind=str(data.get("type") or "cut"); duration=int(data.get("durationMs") or 0); targets=created_scenes or ([selected_scene_id] if selected_scene_id else [])
        for scene_id in targets:self.scenes.set_transition(project_id,scene_id,kind,duration)

    def _apply_timeline(self,project_id:str,data:dict,result:TemplateApplyResult)->None:
        if not self.timeline_service:return
        # TimelineService already owns canonical track creation. Template only applies logical visibility/lock hints.
        try:self.timeline_service.repository.ensure_tracks(project_id)
        except Exception:pass
        result.recommendations["timelineTracks"]=deepcopy(data.get("tracks") or [])

    def _apply_short_style(self,project_id:str,data:dict,project,result:TemplateApplyResult)->None:
        if self.short_repository is None:return
        item=self.short_repository.get_project(project_id)
        if item is None and str(project.workflow)=="shorts":
            item=ShortProject(project_id=project_id,language=project.language,target_aspect_ratio=project.aspect_ratio,style=str(data.get("style") or "creator"))
        if item is not None:
            item.style=str(data.get("style") or item.style); item.target_aspect_ratio=str(data.get("aspectRatio") or item.target_aspect_ratio); self.short_repository.save_project(item)
    def _apply_news_theme(self,project_id:str,data:dict,result:TemplateApplyResult)->None:
        preset=str(data.get("themeRef") or data.get("presetId") or "")
        if self.news_visual is not None and preset:
            self.news_visual.apply_theme(project_id,preset)
            result.recommendations["newsThemeId"]=preset
        else:
            result.recommendations[TemplateComponentType.NEWS_VISUAL_THEME.value]=deepcopy(data)

    def _apply_story_structure(self,project_id:str,data:dict,result:TemplateApplyResult,mode:str)->None:
        preset=str(data.get("presetId") or "")
        if self.story_outline is not None and preset:
            outline,beats=self.story_outline.latest(project_id)
            if outline is None:
                outline,beats=self.story_outline.create_from_plan(project_id,template_id=preset)
            elif mode=="merge":
                beats=self.story_outline.apply_template(project_id,outline.id,preset,"append")
            else:
                beats=self.story_outline.apply_template(project_id,outline.id,preset,"replace")
            result.recommendations["storyTemplateId"]=preset; result.recommendations["storyBeatCount"]=len(beats)
        else:
            result.recommendations[TemplateComponentType.STORY_STRUCTURE.value]=deepcopy(data)


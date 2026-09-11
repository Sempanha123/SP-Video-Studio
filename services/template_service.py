from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from domain.project import utc_now_iso
from domain.template import Template
from domain.template_component import TemplateComponent, TemplateComponentType
from domain.template_errors import TemplateNotFound, TemplateReadOnly
from domain.template_manifest import TemplateManifest
from domain.template_placeholder import TemplatePlaceholder
from services.template_preview_service import TemplatePreviewService
from services.template_validation_service import TemplateValidationService


class TemplateService:
    def __init__(self,repository,builtin_root:Path,user_root:Path,validation:TemplateValidationService,preview:TemplatePreviewService,package_service,*,project_repository=None,scene_repository=None,phase22_repository=None,subtitle_service=None,short_repository=None,export_presets=None) -> None:
        self.repository=repository; self.builtin_root=Path(builtin_root); self.user_root=Path(user_root); self.validation=validation; self.preview_service=preview; self.packages=package_service
        self.projects=project_repository; self.scenes=scene_repository; self.phase22=phase22_repository; self.subtitles=subtitle_service; self.shorts=short_repository; self.export_presets=export_presets
        self._builtins=self._load_builtins(); self.repository.rebuild_index()

    def _load_builtins(self)->dict[str,Template]:
        result={}
        if not self.builtin_root.exists():return result
        for path in sorted(self.builtin_root.glob("*.json")):
            try:
                item=Template.from_dict(json.loads(path.read_text(encoding="utf-8")),builtin=True); item.manifest_path=str(path); self.validation.validate(item); result[item.id]=item
            except Exception:continue
        return result

    def refresh(self)->None:self._builtins=self._load_builtins(); self.repository.rebuild_index()
    def builtin_ids(self)->set[str]:return set(self._builtins)

    def get(self,template_id:str)->Template:
        item=self._builtins.get(template_id) or self.repository.get(template_id)
        if item is None:raise TemplateNotFound()
        return item

    def list_templates(self,*,query:str="",category:str="all",sort:str="recommended")->list[Template]:
        items=list(self._builtins.values())+self.repository.list_all(); q=query.strip().casefold(); cat=category.strip().casefold()
        if q:items=[x for x in items if q in x.search_text()]
        if cat and cat!="all":items=[x for x in items if x.category.casefold()==cat or x.type_code.casefold()==cat or x.workflow.casefold()==cat]
        recent=self.repository.recent(100); recent_pos={tid:i for i,tid in enumerate(recent)}
        if sort=="name":items.sort(key=lambda x:x.name.casefold())
        elif sort=="recent":items.sort(key=lambda x:(recent_pos.get(x.id,10**6),x.name.casefold()))
        else:items.sort(key=lambda x:(not bool(x.metadata.get("recommended",False)),not x.builtin,x.name.casefold()))
        return items

    def categories(self)->list[str]:
        preferred=["News","Story","Shorts","Interview","Reporter","Documentary","Educational","Creator","Minimal","General Video"]
        known={x.category for x in list(self._builtins.values())+self.repository.list_all()}; return [x for x in preferred if x in known]+sorted(known-set(preferred))

    def preview(self,template_id:str)->dict[str,object]:return self.preview_service.preview(self.get(template_id))

    def duplicate(self,template_id:str,name:str|None=None)->Template:
        source=self.get(template_id); clone=deepcopy(source); clone.template_id=str(uuid4()); clone.name=(name or f"{source.name} Copy").strip(); clone.builtin=False; clone.version="1.0"; clone.created_at=clone.updated_at=utc_now_iso(); clone.author_label="User"; clone.manifest_path=""; return self.save_user(clone)

    def rename(self,template_id:str,name:str)->Template:
        if template_id in self._builtins:raise TemplateReadOnly()
        item=self.get(template_id); item.name=name.strip()
        if not item.name:raise ValueError("Template name is required.")
        return self.save_user(item)

    def delete(self,template_id:str)->None:
        if template_id in self._builtins:raise TemplateReadOnly()
        self.repository.delete(template_id)

    def save_user(self,item:Template)->Template:
        item.builtin=False; self.validation.validate(item); folder=self.user_root/item.id; folder.mkdir(parents=True,exist_ok=True); item.manifest_path=str(folder/"manifest.json")
        template_path=folder/"template.json"; manifest_path=folder/"manifest.json"
        self._atomic_json(template_path,item.to_dict()); self._atomic_json(manifest_path,item.manifest().to_dict()); return self.repository.save(item,template_path,manifest_path)

    def export_package(self,template_id:str,destination:Path)->Path:
        item=self.get(template_id)
        asset_root=(Path(item.manifest_path).parent/"assets") if item.manifest_path else None
        return self.packages.export(item,Path(destination),asset_root=asset_root)

    def import_package(self,package:Path,*,conflict:str="keep_both")->Template:
        existing={x.id for x in self.repository.list_all()}; item,folder=self.packages.import_package(Path(package),self.user_root,conflict=conflict,existing_ids=existing,builtin_ids=self.builtin_ids()); item.builtin=False; item.manifest_path=str(folder/"manifest.json"); self.repository.save(item,folder/"template.json",folder/"manifest.json"); return item

    def save_project_as_template(self,project_id:str,name:str,category:str,description:str,*,include_components:set[str]|None=None,include_text:bool=False)->Template:
        if not all((self.projects,self.scenes)):raise RuntimeError("Project capture services are unavailable.")
        project=self.projects.get_by_id(project_id)
        if project is None:raise KeyError("Project not found.")
        selected=include_components or {"project_settings","scene_structure","speaker_structure","speech_block_structure","subtitle_style","transition_style","short_style","export_recommendation"}
        components:list[TemplateComponent]=[]; placeholders:list[TemplatePlaceholder]=[]
        if "project_settings" in selected:
            components.append(TemplateComponent("project_settings","project_settings",{"workflow":str(project.workflow),"aspectRatio":project.aspect_ratio,"fps":project.fps,"languageMode":"project"}))
        if "scene_structure" in selected:
            scenes=[]
            for sidx,scene in enumerate(self.scenes.list_for_project(project_id),1):
                spec={"localId":f"scene_{sidx}","name":scene.name,"durationMs":scene.duration_ms,"fitMode":scene.fit_mode,"backgroundColor":scene.background_color,"transitionOut":scene.transition_out.to_dict(),"layers":[],"overlays":[]}
                if scene.primary_media_id:
                    pid=f"media_scene_{sidx}_primary"; spec["primaryMediaPlaceholder"]=pid; placeholders.append(TemplatePlaceholder(pid,f"{scene.name} Media","media",False,"Choose project media for this scene.",accepted_media_types=("video","image")))
                for lidx,layer in enumerate(self.scenes.layers(scene.id),1):
                    lp=f"media_scene_{sidx}_layer_{lidx}"; placeholders.append(TemplatePlaceholder(lp,f"{scene.name} Layer {lidx}","media",False,"Choose reusable project media.",accepted_media_types=("video","image")))
                    ld=layer.to_dict(); clean={k:ld[k] for k in ("x","y","width","height","opacity","rotation","role","startMs","durationMs","sourceInMs","fitMode","useAudio","audioVolume","chromaKey") if k in ld}; clean.update({"localId":f"layer_{sidx}_{lidx}","mediaPlaceholder":lp}); spec["layers"].append(clean)
                for oidx,overlay in enumerate(self.scenes.overlays(scene.id),1):
                    od=overlay.to_dict(); text=od.get("text","") if include_text else ""
                    if not include_text and od.get("text"):
                        tid=f"text_scene_{sidx}_overlay_{oidx}"; placeholders.append(TemplatePlaceholder(tid,f"{scene.name} Text {oidx}","text",False)); text="{{"+tid+"}}"
                    spec["overlays"].append({"localId":f"overlay_{sidx}_{oidx}","type":od.get("type","body_text"),"text":text,"secondaryText":od.get("secondaryText","") if include_text else "","x":od.get("x",.1),"y":od.get("y",.1),"width":od.get("width",.8),"height":od.get("height",.2),"opacity":od.get("opacity",1.0),"rotation":od.get("rotation",0.0),"style":dict(od.get("style") or {})})
                scenes.append(spec)
            components.append(TemplateComponent("scene_structure","scene_structure",{"scenes":scenes}))
        if self.phase22 and "speaker_structure" in selected:
            speaker_rows=[]; speaker_local={}
            for idx,speaker in enumerate(self.phase22.speakers(project_id),1):
                local=f"speaker_{idx}"; speaker_local[speaker.id]=local; role=speaker.role_code; voice_placeholder=f"voice_{idx}"
                speaker_rows.append({"localId":local,"name":role.replace("_"," ").title(),"role":role,"language":"{{project_language}}","voicePlaceholder":voice_placeholder})
                placeholders.append(TemplatePlaceholder(voice_placeholder,f"{role.replace('_',' ').title()} Voice","voice",False,role=role,voice_category=str(speaker.metadata.get("voiceCategory","") or "")))
            components.append(TemplateComponent("speaker_structure","speaker_structure",{"speakers":speaker_rows}))
            if "speech_block_structure" in selected:
                blocks=[]
                for idx,block in enumerate(self.phase22.blocks_for_project(project_id),1):
                    blocks.append({"localId":f"speech_{idx}","speakerLocalId":speaker_local.get(block.speaker_id,""),"language":"{{project_language}}","text":block.text if include_text else "","pauseBeforeMs":block.pause_before_ms,"pauseAfterMs":block.pause_after_ms,"sourceType":block.source_type_code})
                components.append(TemplateComponent("speech_block_structure","speech_block_structure",{"blocks":blocks,"contentIncluded":include_text}))
        if self.subtitles and "subtitle_style" in selected:
            tracks=self.subtitles.list_tracks(project_id)
            if tracks:
                target=next((x for x in tracks if getattr(x,"is_default",False)),tracks[0]); _,style,_=self.subtitles.get(project_id,target.id); data=style.to_dict(); preset=str(data.get("metadata",{}).get("presetId","") or "")
                clean=dict(data); [clean.pop(k,None) for k in ("id","project_id","created_at","updated_at")]
                components.append(TemplateComponent("subtitle_style","subtitle_style",{"presetId":preset or "clean","style":clean}))
        if self.shorts and "short_style" in selected:
            short=self.shorts.get_project(project_id)
            if short:components.append(TemplateComponent("short_style","short_style",{"style":short.style,"aspectRatio":short.target_aspect_ratio,"platform":short.platform}))
        if self.export_presets and "export_recommendation" in selected:
            profile=self.export_presets.profile(project_id)
            if profile:components.append(TemplateComponent("export_recommendation","export_recommendation",{"presetId":profile.preset_id}))
        if str(project.workflow)=="news":components.append(TemplateComponent("news_theme","news_visual_theme",{"sourceContentIncluded":False,"claimsIncluded":False}))
        if str(project.workflow)=="story":components.append(TemplateComponent("story_structure","story_structure",{"contentIncluded":False}))
        item=Template(name=name.strip(),template_type=("news" if str(project.workflow)=="news" else "story" if str(project.workflow)=="story" else "short" if str(project.workflow)=="shorts" else "project"),category=category.strip() or "General Video",description=description.strip(),workflow=str(project.workflow),builtin=False,author_label="User",tags=(str(project.workflow),"custom"),supported_aspect_ratios=(project.aspect_ratio,),supported_languages=(),required_features=(),components=components,placeholders=placeholders,metadata={"capturedFromProject":True,"privateContentExcluded":not include_text,"structureOnly":True})
        return self.save_user(item)

    @staticmethod
    def _atomic_json(path:Path,value:dict)->None:
        path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(path.suffix+".tmp"); temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)

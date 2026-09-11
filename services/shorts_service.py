from __future__ import annotations

from copy import deepcopy

from domain.short_candidate import ShortCandidateStatus
from domain.short_project import ShortProject, ShortProjectStatus
from domain.short_style import short_style
from domain.shorts_errors import ShortCandidateInvalid, ShortInvalidRange
from services.short_candidate_service import ShortCandidateService
from services.short_materialization_service import ShortMaterializationService
from services.short_reframe_service import ShortReframeService
from services.short_validation_service import ShortsValidationService
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.short_repository import ShortRepository


class ShortsService:
    def __init__(self, repository: ShortRepository, projects: ProjectRepository, candidates: ShortCandidateService,
                 materializer: ShortMaterializationService, reframe: ShortReframeService, validation: ShortsValidationService,
                 subtitle_service=None, language_service=None, export_preset_service=None, timeline_service=None, dubbing_repository=None) -> None:
        self.repository=repository; self.projects=projects; self.candidates=candidates; self.materializer=materializer; self.reframe=reframe
        self.validation=validation; self.subtitles=subtitle_service; self.languages=language_service; self.export_presets=export_preset_service
        self.timeline=timeline_service; self.dubbing=dubbing_repository

    def load_or_create(self, project_id: str) -> ShortProject:
        item=self.repository.get_project(project_id)
        if item is not None:return item
        project=self.projects.get_by_id(project_id)
        if project is None:raise KeyError("Project not found.")
        item=ShortProject(project_id=project_id,language=project.language,target_aspect_ratio="9:16",metadata={"inMs":0,"outMs":0})
        return self.repository.save_project(item)

    def update_settings(self, project_id: str, *, target_duration_ms: int|None=None, aspect_ratio: str|None=None,
                        language: str|None=None, platform: str|None=None, style: str|None=None) -> ShortProject:
        item=self.load_or_create(project_id)
        if target_duration_ms is not None:item.target_duration_ms=max(1000,int(target_duration_ms))
        if aspect_ratio is not None:item.target_aspect_ratio=str(aspect_ratio)
        if language is not None:item.language=str(language)
        if platform is not None:item.platform=str(platform)
        if style is not None:item.style=short_style(style).name
        return self.repository.save_project(item)

    def set_in(self, project_id: str, position_ms: int) -> ShortProject:
        item=self.load_or_create(project_id); item.metadata["inMs"]=max(0,int(position_ms)); return self.repository.save_project(item)

    def set_out(self, project_id: str, position_ms: int) -> ShortProject:
        item=self.load_or_create(project_id); item.metadata["outMs"]=max(0,int(position_ms)); return self.repository.save_project(item)

    def create_from_in_out(self, project_id: str, media_id: str, *, title: str="Short"):
        item=self.load_or_create(project_id); start=int(item.metadata.get("inMs",0) or 0); end=int(item.metadata.get("outMs",0) or 0)
        if end<=start:raise ShortInvalidRange()
        source_type="video"
        if self.dubbing is not None:
            try:
                output=self.dubbing.latest_output(project_id,"final_mix")
                if output is not None and output.status_code=="ready" and (not output.source_media_id or output.source_media_id==media_id): source_type="dub"
            except Exception: pass
        return self.candidates.create_manual(project_id,media_id,start,end,title=title,language=item.language,target_duration_ms=item.target_duration_ms,source_type=source_type)

    def update_candidate(self, project_id: str, candidate_id: str, *, title: str|None=None, hook: str|None=None, status: str|None=None):
        item=self.repository.get_candidate(candidate_id)
        if item is None or item.project_id!=project_id:raise ShortCandidateInvalid("Short candidate could not be found.")
        if title is not None:item.title=title.strip() or item.title
        if hook is not None:item.hook=hook.strip()
        if status is not None:item.status=status
        self.repository.save_candidate(item,self.repository.segments(item.id)); return item

    def duplicate_candidate(self, project_id: str, candidate_id: str):
        return self.repository.duplicate_candidate(project_id,candidate_id)

    def approve_to_project(self, candidate_id: str, *, title: str|None=None, aspect_ratio: str|None=None, platform: str|None=None, style: str|None=None):
        candidate=self.repository.get_candidate(candidate_id)
        if candidate is None:raise ShortCandidateInvalid("Short candidate could not be found.")
        source_settings=self.load_or_create(candidate.project_id)
        duplicate,target_candidate=self.materializer.create_derived_project(candidate_id,title=title,target_aspect_ratio=aspect_ratio or source_settings.target_aspect_ratio,
                                                                             platform=platform or source_settings.platform,style=style or source_settings.style)
        candidate.status=ShortCandidateStatus.APPROVED; self.repository.save_candidate(candidate,self.repository.segments(candidate.id))
        return duplicate,target_candidate

    def readiness(self, project_id: str, candidate_id: str) -> dict[str,object]:
        item=self.load_or_create(project_id); return self.validation.readiness(project_id,candidate_id,aspect_ratio=item.target_aspect_ratio)

    def recommended_export_preset(self, project_id: str) -> str:
        item=self.load_or_create(project_id)
        # Resolve from the existing export preset registry/service; never redefine platform specs here.
        if self.export_presets is not None:
            for method in ("list_presets","presets","list_all"):
                fn=getattr(self.export_presets,method,None)
                if not callable(fn):continue
                try: presets=fn() if method!="list_presets" else fn(project_id)
                except TypeError:
                    try:presets=fn()
                    except Exception:continue
                except Exception:continue
                for preset in presets or []:
                    pid=getattr(preset,"id",None) or (preset.get("id") if isinstance(preset,dict) else None)
                    platform=getattr(preset,"platform",None) or (preset.get("platform") if isinstance(preset,dict) else None)
                    aspect=getattr(preset,"aspect_ratio",None) or (preset.get("aspectRatio") if isinstance(preset,dict) else None)
                    if platform==item.platform and aspect==item.target_aspect_ratio:return str(pid)
        fallback={"tiktok":"tiktok","youtube_shorts":"youtube_shorts","instagram_reels":"instagram_reels","facebook":"facebook_vertical"}
        if item.platform=="generic":return {"9:16":"generic_vertical","1:1":"generic_square","16:9":"generic_landscape"}.get(item.target_aspect_ratio,"generic_vertical")
        return fallback.get(item.platform,"generic_vertical")

    def source_changed(self, project_id: str) -> bool:
        item=self.load_or_create(project_id)
        source_project=self.projects.get_by_id(item.source_project_id) if item.source_project_id else None
        if source_project is None:return False
        original_update=str(item.metadata.get("sourceProjectUpdatedAt","") or "")
        changed=bool(original_update and original_update!=source_project.updated_at)
        if changed:item.status=ShortProjectStatus.OUTDATED; item.metadata["sourceProjectChanged"]=True; self.repository.save_project(item)
        return changed
    def apply_silence_removal(self, project_id: str, start_ms: int, end_ms: int) -> int:
        if self.timeline is None: raise ShortCandidateInvalid("Timeline editing is unavailable.")
        project=self.projects.get_by_id(project_id)
        if project is None or str(project.workflow)!="shorts": raise ShortCandidateInvalid("Open the independent Short project before removing silence.")
        start=max(0,int(start_ms)); end=max(0,int(end_ms))
        if end<=start: raise ShortInvalidRange()

        def split_boundary(position: int) -> None:
            mapped=self.timeline.project_to_scene_time(project_id,position)
            if not mapped:return
            scene_id,local=mapped; scene=self.timeline.edits.scenes.get(project_id,scene_id)[0]
            if 100<=int(local)<=int(scene.duration_ms)-100:
                self.timeline.edits.split_scene(project_id,scene_id,int(local))

        # Split the right boundary first so the left project's position remains stable.
        split_boundary(end); split_boundary(start)
        removed=0
        for row in list(self.timeline.mapping.scene_ranges(project_id)):
            a=int(row["startMs"]); b=int(row["endMs"])
            if a>=start and b<=end and b>a:
                removed+=b-a; self.timeline.edits.delete_scene(project_id,str(row["sceneId"]))
        if removed<=0: raise ShortCandidateInvalid("The selected silence range did not cover an editable Timeline region.")
        return removed


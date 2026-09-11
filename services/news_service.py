from __future__ import annotations
import hashlib, json, logging, shutil
from pathlib import Path

from domain.news_project import NewsProjectMetadata
from services.news_brief_service import NewsBriefService
from services.news_claim_service import NewsClaimService
from services.news_errors import NewsInvalidSource
from services.news_script_service import NewsScriptService
from services.news_source_service import NewsSourceService
from services.news_validation_service import NewsValidationService, source_fingerprint
from storage.repositories.news_repository import NewsRepository
from storage.repositories.project_repository import ProjectRepository

class NewsService:
    def __init__(self,repository:NewsRepository,project_repository:ProjectRepository,sources:NewsSourceService,claims:NewsClaimService,briefs:NewsBriefService,scripts:NewsScriptService,validation:NewsValidationService,logger=None,*,voice_service=None,narration_service=None,subtitle_service=None)->None:
        self.repository=repository; self.project_repository=project_repository; self.sources=sources; self.claims=claims; self.briefs=briefs; self.scripts=scripts; self.validation=validation; self.logger=logger or logging.getLogger("sp_video_studio.news")
        self.voice_service=voice_service; self.narration_service=narration_service; self.subtitle_service=subtitle_service
    def load_or_create(self,project_id:str)->NewsProjectMetadata:
        project=self.project_repository.get_by_id(project_id)
        if project is None: raise NewsInvalidSource("Project could not be found.")
        if str(project.workflow)!="news": raise NewsInvalidSource("News Studio is available for News workflow projects.")
        meta=self.repository.get_project(project_id)
        if meta is None:
            meta=NewsProjectMetadata(project_id,language=project.language,target_duration_ms=60_000,platform="generic")
            self.repository.upsert_project(meta)
        return meta
    def update_setup(self,project_id:str,*,topic:str|None=None,angle:str|None=None,region:str|None=None,language:str|None=None,target_audience:str|None=None,target_duration_ms:int|None=None,platform:str|None=None)->NewsProjectMetadata:
        m=self.load_or_create(project_id)
        if topic is not None:m.topic=topic.strip()
        if angle is not None:m.angle=angle
        if region is not None:m.region=region.strip()
        if language is not None:m.language=language
        if target_audience is not None:m.target_audience=target_audience
        if target_duration_ms is not None:m.target_duration_ms=int(target_duration_ms)
        if platform is not None:m.platform=platform
        m.source_fingerprint=source_fingerprint(self.repository,project_id); return self.repository.upsert_project(m)
    def overview(self,project_id:str)->dict[str,object]:
        m=self.load_or_create(project_id); script=self.scripts.script_service.repository.get_primary_by_project(project_id)
        readiness=self.validation.readiness(project_id,script.id if script else None); scenes=len(self.scripts.scene_service.list_scenes(project_id)) if self.scripts.scene_service else 0
        voice_ready=bool(self.voice_service and self.voice_service.project_voice(project_id))
        narration=self.narration_service.active(project_id) if self.narration_service else None
        subtitle_count=len(self.subtitle_service.list_tracks(project_id)) if self.subtitle_service else 0
        return {**m.to_dict(),**readiness,"scenes":scenes,"scriptReady":bool(script and any(s.content.strip() for s in self.scripts.script_service.repository.list_sections(script.id))),
                "voiceReady":voice_ready,"narrationReady":bool(narration),"narrationCurrent":bool(narration and self.narration_service.narration_is_current(project_id,narration)) if narration else False,"subtitleCount":subtitle_count,"subtitlesReady":subtitle_count>0}
    def source_fingerprint(self,project_id:str)->str:return source_fingerprint(self.repository,project_id)
    def refresh_outdated_state(self,project_id:str)->dict[str,int]:
        fp=source_fingerprint(self.repository,project_id); briefs=0;mappings=0
        for b in self.repository.list_briefs(project_id):
            if b.source_fingerprint and b.source_fingerprint!=fp and b.status!="draft": b.status="outdated";self.repository.update_brief(b);briefs+=1
        for m in self.repository.mappings(project_id):
            if m.status=="grounded" and any((c:=self.repository.claim(project_id,cid)) is None or c.status_code!="approved" for cid in m.claim_ids):m.status="needs_review";self.repository.update_mapping(m);mappings+=1
        meta=self.load_or_create(project_id);meta.source_fingerprint=fp;self.repository.upsert_project(meta);return {"briefs":briefs,"mappings":mappings}
    def duplicate_project_news(self,source_project_id:str,target_project_id:str,*,script_map:dict[str,str]|None=None,section_map:dict[str,str]|None=None)->dict[str,dict[str,str]]:
        maps=self.repository.duplicate_project(source_project_id,target_project_id,script_map=script_map,section_map=section_map)
        source_project=self.project_repository.get_by_id(source_project_id); target_project=self.project_repository.get_by_id(target_project_id)
        if source_project and target_project:
            old_root=Path(source_project.project_path).resolve(); new_root=Path(target_project.project_path).resolve()
            for source in self.repository.list_sources(target_project_id,include_removed=True):
                if not source.source_path:continue
                try:
                    old=Path(source.source_path).resolve(); rel=old.relative_to(old_root); new=new_root/rel
                except Exception:continue
                if new.exists():source.source_path=str(new);self.repository.update_source(source)
        return maps

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from domain.project import utc_now_iso
from domain.subtitle import SubtitleTrack, SubtitleTrackStatus, SubtitleTrackType
from domain.subtitle_cue import SubtitleCue, subtitle_cue_source_hash
from domain.subtitle_style import SubtitleStyle
from domain.subtitle_word import SubtitleWord
from media.subtitles import ASSExporter, SRTExporter, VTTExporter
from services.subtitle_generation_service import SubtitleGenerationService
from services.subtitle_import_service import SubtitleImportService
from services.subtitle_preset_service import SubtitlePresetService
from services.subtitle_timing_service import SubtitleTimingService
from services.subtitle_validation_service import SubtitleIssue, SubtitleValidationService
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository


class SubtitleServiceError(RuntimeError):
    pass


class SubtitleService:
    def __init__(
        self,
        repository: SubtitleRepository,
        project_repository: ProjectRepository,
        transcript_repository: TranscriptRepository,
        translation_repository: TranslationRepository,
        generation_service: SubtitleGenerationService,
        preset_service: SubtitlePresetService,
        validation_service: SubtitleValidationService,
        timing_service: SubtitleTimingService,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository=repository; self.project_repository=project_repository; self.transcript_repository=transcript_repository
        self.translation_repository=translation_repository; self.generation_service=generation_service; self.preset_service=preset_service
        self.validation_service=validation_service; self.timing_service=timing_service; self.logger=logger or logging.getLogger("sp_video_studio.subtitles")
        self.importer=SubtitleImportService(); self.exporters={"srt":SRTExporter(),"vtt":VTTExporter(),"ass":ASSExporter()}

    def list_tracks(self,project_id:str)->list[SubtitleTrack]: self._require_project(project_id); return self.repository.list_for_project(project_id)

    def source_options(self, project_id: str) -> dict[str, list[dict[str, object]]]:
        self._require_project(project_id)
        transcripts=[]
        for item in self.transcript_repository.list_for_project(project_id):
            if item.status_code in {"ready", "outdated"}:
                transcripts.append({"id":item.transcript_id,"label":f"Transcript · {item.detected_language or item.language_mode}","language":item.detected_language or item.language_mode,"mediaId":item.media_id,"status":item.status_code})
        translations=[]
        for item in self.translation_repository.list_for_project(project_id):
            if item.status_code not in {"failed", "cancelled"}:
                segments=self.translation_repository.segments(item.translation_id)
                if any(seg.start_ms is not None and seg.end_ms is not None for seg in segments):
                    translations.append({"id":item.translation_id,"label":f"{item.source_language.upper()} → {item.target_language.upper()} Translation","sourceLanguage":item.source_language,"targetLanguage":item.target_language,"sourceId":item.source_id,"status":item.status_code})
        return {"transcripts":transcripts,"translations":translations}

    def media_id_for_track(self, project_id: str, track_id: str) -> str:
        track=self._owned_track(project_id,track_id)
        transcript_id=""
        if track.source_type=="transcript": transcript_id=track.source_id
        elif track.source_type=="translation":
            if track.is_bilingual: transcript_id=str(track.metadata.get("transcriptId", ""))
            else:
                translation=self.translation_repository.get(track.source_id)
                if translation and translation.source_type_code=="transcript": transcript_id=translation.source_id
        if not transcript_id: return ""
        transcript=self.transcript_repository.get(transcript_id)
        return transcript.media_id if transcript and transcript.project_id==project_id else ""

    def get(self,project_id:str,track_id:str)->tuple[SubtitleTrack,SubtitleStyle,list[SubtitleCue]]:
        track=self._owned_track(project_id,track_id); style=self.repository.style(track.style_id)
        if style is None: raise SubtitleServiceError("Subtitle style could not be found.")
        return track,style,self.repository.cues(track_id)

    def create_from_transcript(self,project_id:str,transcript_id:str,*,name:str|None=None,preset_id:str="clean",is_default:bool=False)->SubtitleTrack:
        self._require_project(project_id); style=self.preset_service.style_from_preset(project_id,preset_id)
        transcript=self.transcript_repository.get(transcript_id)
        if transcript is None: raise SubtitleServiceError("Transcript could not be found.")
        label=name or f"{(transcript.detected_language or transcript.language_mode or 'en').upper()} Subtitles"
        track,cues=self.generation_service.from_transcript(project_id,transcript_id,label,style,default=is_default or not self.repository.list_for_project(project_id))
        self.repository.create_track(track,style,cues); self.logger.info("Subtitle track created from transcript: %s",track.track_id); return track

    def create_from_translation(self,project_id:str,translation_id:str,*,name:str|None=None,preset_id:str="clean",is_default:bool=False)->SubtitleTrack:
        self._require_project(project_id); style=self.preset_service.style_from_preset(project_id,preset_id)
        translation=self.translation_repository.get(translation_id)
        if translation is None: raise SubtitleServiceError("Translation could not be found.")
        track,cues=self.generation_service.from_translation(project_id,translation_id,name or f"{translation.target_language.upper()} Subtitles",style,default=is_default or not self.repository.list_for_project(project_id))
        self.repository.create_track(track,style,cues); return track

    def create_bilingual(self,project_id:str,transcript_id:str,translation_id:str,*,name:str="Bilingual Subtitles",preset_id:str="clean",primary:str="source")->SubtitleTrack:
        style=self.preset_service.style_from_preset(project_id,preset_id); track,cues=self.generation_service.bilingual(project_id,transcript_id,translation_id,name,style,primary=primary,default=not self.repository.list_for_project(project_id)); self.repository.create_track(track,style,cues); return track

    def create_manual(self,project_id:str,language:str,*,name:str="Manual Subtitles",preset_id:str="clean")->SubtitleTrack:
        self._require_project(project_id); style=self.preset_service.style_from_preset(project_id,preset_id)
        track=SubtitleTrack(project_id=project_id,name=name,language=language,track_type=SubtitleTrackType.MANUAL,source_type="manual",status=SubtitleTrackStatus.DRAFT,style_id=style.style_id,is_default=not self.repository.list_for_project(project_id)); self.repository.create_track(track,style,[]); return track

    def import_file(self,project_id:str,path:Path,language:str,*,preset_id:str="clean",name:str|None=None)->SubtitleTrack:
        track=self.create_manual(project_id,language,name=name or Path(path).stem,preset_id=preset_id)
        cues=self.importer.parse(Path(path),track.track_id); self.repository.replace_cues(project_id,track.track_id,cues); track.status=SubtitleTrackStatus.READY; track.metadata["importedFrom"]=Path(path).suffix.lower(); self.repository.update_track(track); return track

    def update_cue(self,project_id:str,track_id:str,cue_id:str,*,text:str|None=None,secondary_text:str|None=None,start_ms:int|None=None,end_ms:int|None=None,position:str|None=None,alignment:str|None=None)->SubtitleCue:
        self._owned_track(project_id,track_id); cue=self.repository.cue(cue_id)
        if cue is None or cue.track_id!=track_id: raise SubtitleServiceError("Subtitle cue could not be found.")
        if text is not None and text!=cue.text: cue.text=text; cue.edited=True
        if secondary_text is not None and secondary_text!=cue.secondary_text: cue.secondary_text=secondary_text; cue.edited=True
        if start_ms is not None: cue.start_ms=int(start_ms); cue.edited=True
        if end_ms is not None: cue.end_ms=int(end_ms); cue.edited=True
        if position is not None: cue.position=position
        if alignment is not None: cue.alignment=alignment
        return self.repository.update_cue(project_id,cue)

    def add_cue(self,project_id:str,track_id:str,start_ms:int,text:str="",duration_ms:int=2000)->SubtitleCue:
        track=self._owned_track(project_id,track_id); cues=self.repository.cues(track_id); cue=SubtitleCue(track_id=track_id,order=len(cues),start_ms=max(0,int(start_ms)),end_ms=max(0,int(start_ms))+max(300,int(duration_ms)),text=text,edited=bool(text)); self.repository.add_cue(project_id,cue); return cue

    def delete_cue(self,project_id:str,track_id:str,cue_id:str)->None:
        self._owned_track(project_id,track_id); cue=self.repository.cue(cue_id)
        if cue is None or cue.track_id!=track_id: raise SubtitleServiceError("Subtitle cue could not be found.")
        self.repository.delete_cue(project_id,cue_id); self._normalize_persist(project_id,track_id)

    def split_cue(self,project_id:str,track_id:str,cue_id:str,split_ms:int,text_before:str,text_after:str)->tuple[SubtitleCue,SubtitleCue]:
        self._owned_track(project_id,track_id); cues=self.repository.cues(track_id); index=next((i for i,q in enumerate(cues) if q.cue_id==cue_id),-1)
        if index<0: raise SubtitleServiceError("Subtitle cue could not be found.")
        first,second=self.timing_service.split(cues[index],int(split_ms),text_before,text_after); cues[index:index+1]=[first,second]; cues=self.timing_service.normalize(cues); self.repository.replace_cues(project_id,track_id,cues); return first,second

    def merge_cues(self,project_id:str,track_id:str,first_id:str,second_id:str)->SubtitleCue:
        self._owned_track(project_id,track_id); cues=self.timing_service.normalize(self.repository.cues(track_id)); ids=[q.cue_id for q in cues]
        try: a,b=ids.index(first_id),ids.index(second_id)
        except ValueError as exc: raise SubtitleServiceError("Subtitle cue could not be found.") from exc
        if b!=a+1: raise SubtitleServiceError("Only adjacent subtitle cues can be merged.")
        merged=self.timing_service.merge(cues[a],cues[b]); cues[a:b+1]=[merged]; cues=self.timing_service.normalize(cues); self.repository.replace_cues(project_id,track_id,cues); return merged

    def shift_timing(self,project_id:str,track_id:str,delta_ms:int,selected_ids:set[str]|None=None)->list[SubtitleCue]:
        self._owned_track(project_id,track_id); cues=self.timing_service.shift(self.repository.cues(track_id),int(delta_ms),selected_ids); self.repository.replace_cues(project_id,track_id,cues); return cues

    def update_style(self,project_id:str,track_id:str,updates:dict[str,object])->SubtitleStyle:
        track,style,_=self.get(project_id,track_id)
        allowed={"name","font_family","font_size","font_weight","italic","text_color","secondary_text_color","outline_color","outline_width","shadow_enabled","shadow_offset","background_enabled","background_color","background_opacity","alignment","vertical_position","horizontal_margin","vertical_margin","max_lines","max_chars_per_line","line_spacing","highlight_color","highlight_text_color","secondary_scale"}
        for key,value in updates.items():
            if key in allowed: setattr(style,key,value)
        return self.repository.update_style(style)

    def apply_preset(self,project_id:str,track_id:str,preset_id:str)->SubtitleStyle:
        track=self._owned_track(project_id,track_id); old=self.repository.style(track.style_id)
        if old is None: raise SubtitleServiceError("Subtitle style could not be found.")
        new=self.preset_service.style_from_preset(project_id,preset_id); new.style_id=old.style_id; new.created_at=old.created_at; return self.repository.update_style(new)

    def set_default(self,project_id:str,track_id:str)->None: self._owned_track(project_id,track_id); self.repository.set_default(project_id,track_id)

    def rename_track(self,project_id:str,track_id:str,name:str)->SubtitleTrack:
        track=self._owned_track(project_id,track_id); clean=name.strip()
        if not clean: raise SubtitleServiceError("Subtitle track name is required.")
        track.name=clean; return self.repository.update_track(track)

    def duplicate_track(self,project_id:str,track_id:str)->SubtitleTrack:
        source,style,cues=self.get(project_id,track_id); new_style=deepcopy(style); new_style.style_id=str(uuid4()); new_style.created_at=new_style.updated_at=utc_now_iso(); new_style.name=style.name
        clone=SubtitleTrack(project_id=project_id,name=f"{source.name} Copy",language=source.language,track_type=source.track_type_code,source_type=source.source_type,source_id=source.source_id,source_language=source.source_language,status=source.status_code,style_id=new_style.style_id,is_bilingual=source.is_bilingual,secondary_language=source.secondary_language,metadata=dict(source.metadata))
        cloned=[]
        for q in cues:
            cq=SubtitleCue(track_id=clone.track_id,order=q.order,start_ms=q.start_ms,end_ms=q.end_ms,text=q.text,secondary_text=q.secondary_text,position=q.position,alignment=q.alignment,style_override=dict(q.style_override),edited=q.edited,locked=q.locked,source_segment_id=q.source_segment_id,source_hash=q.source_hash,metadata=dict(q.metadata))
            cq.words=[SubtitleWord(cue_id=cq.cue_id,order=w.order,text=w.text,start_ms=w.start_ms,end_ms=w.end_ms,probability=w.probability,highlight_group=w.highlight_group,metadata=dict(w.metadata)) for w in q.words]; cloned.append(cq)
        self.repository.create_track(clone,new_style,cloned); return clone

    def delete_track(self,project_id:str,track_id:str)->None: self._owned_track(project_id,track_id); self.repository.delete_track(project_id,track_id)

    def validate_track(self,project_id:str,track_id:str,media_duration_ms:int|None=None)->list[SubtitleIssue]:
        track,style,cues=self.get(project_id,track_id); return self.validation_service.validate(cues,style,track.language,media_duration_ms)

    def export(self,project_id:str,track_id:str,fmt:str,destination:Path)->Path:
        track,style,cues=self.get(project_id,track_id); issues=self.validation_service.validate(cues,style,track.language)
        if any(i.severity=='error' for i in issues): raise SubtitleServiceError("Subtitle timing contains errors that must be fixed before export.")
        exporter=self.exporters.get(fmt.lower())
        if exporter is None: raise SubtitleServiceError("Unsupported subtitle export format.")
        path=exporter.export(track,cues,style,Path(destination)); self.logger.info("Subtitle track exported: %s -> %s",track_id,path); return path

    def active_cue(self,project_id:str,track_id:str,position_ms:int)->SubtitleCue|None:
        self._owned_track(project_id,track_id); cues=self.repository.cues(track_id)
        lo,hi=0,len(cues)-1; pos=int(position_ms)
        while lo<=hi:
            mid=(lo+hi)//2; cue=cues[mid]
            if pos<cue.start_ms: hi=mid-1
            elif pos>=cue.end_ms: lo=mid+1
            else: return cue
        return None

    def active_word(self,cue:SubtitleCue,position_ms:int)->SubtitleWord|None:
        if not cue.words: return None
        pos=int(position_ms); lo,hi=0,len(cue.words)-1
        while lo<=hi:
            mid=(lo+hi)//2; w=cue.words[mid]
            if pos<w.start_ms: hi=mid-1
            elif pos>=w.end_ms: lo=mid+1
            else: return w
        return None

    def sync_source(self,project_id:str,track_id:str)->dict[str,int]:
        track,style,cues=self.get(project_id,track_id); source=self._source_units(track)
        source_missing = track.status_code == SubtitleTrackStatus.SOURCE_MISSING.value
        existing={q.source_segment_id:q for q in cues if q.source_segment_id}; source_ids={u[0] for u in source}; added=changed=removed=0
        for source_id,text,start,end,secondary in source:
            expected=subtitle_cue_source_hash(source_id,text+("\0"+secondary if secondary else ""),start,end)
            cue=existing.get(source_id)
            if cue is None:
                cue=SubtitleCue(track_id=track_id,order=len(cues),start_ms=start,end_ms=end,text=text,secondary_text=secondary,source_segment_id=source_id,source_hash=expected,metadata={"sourceAdded":True}); cues.append(cue); added+=1
            elif cue.source_hash!=expected:
                cue.metadata["sourceChanged"]=True; changed+=1
            cue.order=next(i for i,u in enumerate(source) if u[0]==source_id)
        for cue in cues:
            if cue.source_segment_id and cue.source_segment_id not in source_ids:
                cue.metadata["sourceMissing"]=True; removed+=1
        if source_missing: track.status=SubtitleTrackStatus.SOURCE_MISSING
        elif changed or removed: track.status=SubtitleTrackStatus.OUTDATED
        elif not added: track.status=SubtitleTrackStatus.READY
        track.metadata["sourceFingerprint"]=""
        self.repository.replace_cues(project_id,track_id,self.timing_service.normalize(cues)); self.repository.update_track(track)
        return {"added":added,"changed":changed,"removed":removed}

    def duplicate_project_subtitles(self,source_project_id:str,target_project_id:str,*,transcript_map:dict[str,str]|None=None,translation_map:dict[str,str]|None=None,transcript_segment_map:dict[str,str]|None=None,translation_segment_map:dict[str,str]|None=None)->int:
        count, _ = self.duplicate_project_subtitles_with_map(source_project_id,target_project_id,transcript_map=transcript_map,translation_map=translation_map,transcript_segment_map=transcript_segment_map,translation_segment_map=translation_segment_map)
        return count

    def duplicate_project_subtitles_with_map(self,source_project_id:str,target_project_id:str,*,transcript_map:dict[str,str]|None=None,translation_map:dict[str,str]|None=None,transcript_segment_map:dict[str,str]|None=None,translation_segment_map:dict[str,str]|None=None)->tuple[int,dict[str,str]]:
        transcript_map=transcript_map or {}; translation_map=translation_map or {}; transcript_segment_map=transcript_segment_map or {}; translation_segment_map=translation_segment_map or {}; count=0; track_map={}
        for track in self.repository.list_for_project(source_project_id):
            style=self.repository.style(track.style_id)
            if style is None: continue
            new_style=deepcopy(style); new_style.style_id=str(uuid4()); new_style.project_id=target_project_id; new_style.created_at=new_style.updated_at=utc_now_iso()
            source_id=track.source_id
            if track.source_type=='transcript': source_id=transcript_map.get(track.source_id,"")
            elif track.source_type=='translation': source_id=translation_map.get(track.source_id,"")
            if track.source_type!='manual' and not source_id: continue
            metadata=dict(track.metadata)
            if track.is_bilingual and metadata.get('transcriptId'):
                metadata['transcriptId']=transcript_map.get(str(metadata['transcriptId']), '')
            clone=SubtitleTrack(project_id=target_project_id,name=track.name,language=track.language,track_type=track.track_type_code,source_type=track.source_type,source_id=source_id,source_language=track.source_language,status=track.status_code,style_id=new_style.style_id,is_default=track.is_default,is_bilingual=track.is_bilingual,secondary_language=track.secondary_language,metadata=metadata)
            cloned=[]
            for cue in self.repository.cues(track.track_id):
                source_seg=cue.source_segment_id
                if track.source_type=='transcript':
                    source_seg=transcript_segment_map.get(source_seg, "")
                elif track.source_type=='translation':
                    source_seg=(transcript_segment_map if track.is_bilingual else translation_segment_map).get(source_seg, "")
                cq=SubtitleCue(track_id=clone.track_id,order=cue.order,start_ms=cue.start_ms,end_ms=cue.end_ms,text=cue.text,secondary_text=cue.secondary_text,position=cue.position,alignment=cue.alignment,style_override=dict(cue.style_override),edited=cue.edited,locked=cue.locked,source_segment_id=source_seg,source_hash=cue.source_hash,metadata=dict(cue.metadata))
                cq.words=[SubtitleWord(cue_id=cq.cue_id,order=w.order,text=w.text,start_ms=w.start_ms,end_ms=w.end_ms,probability=w.probability,highlight_group=w.highlight_group,metadata=dict(w.metadata)) for w in cue.words]; cloned.append(cq)
            self.repository.create_track(clone,new_style,cloned); count+=1; track_map[track.id]=clone.id
        return count, track_map

    def _source_units(self,track:SubtitleTrack)->list[tuple[str,str,int,int,str]]:
        if track.source_type=='transcript':
            transcript=self.transcript_repository.get(track.source_id)
            if transcript is None: track.status=SubtitleTrackStatus.SOURCE_MISSING; self.repository.update_track(track); return []
            return [(s.segment_id,s.text,s.start_ms,s.end_ms,"") for s in self.transcript_repository.segments(track.source_id)]
        if track.source_type=='translation':
            translation=self.translation_repository.get(track.source_id)
            if translation is None: track.status=SubtitleTrackStatus.SOURCE_MISSING; self.repository.update_track(track); return []
            return [(s.segment_id,s.translated_text,int(s.start_ms),int(s.end_ms),"") for s in self.translation_repository.segments(track.source_id) if s.start_ms is not None and s.end_ms is not None]
        return []

    def _normalize_persist(self,project_id:str,track_id:str)->None:
        self.repository.replace_cues(project_id,track_id,self.timing_service.normalize(self.repository.cues(track_id)))

    def _owned_track(self,project_id:str,track_id:str)->SubtitleTrack:
        track=self.repository.get_track(track_id)
        if track is None or track.project_id!=project_id: raise SubtitleServiceError("Subtitle track does not belong to this project.")
        return track

    def _require_project(self,project_id:str):
        project=self.project_repository.get_by_id(project_id)
        if project is None: raise SubtitleServiceError("Project could not be found.")
        return project

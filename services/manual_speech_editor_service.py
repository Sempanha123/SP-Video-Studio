from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from domain.speech_block import SpeechAudioStatus, SpeechSourceType, SpeechTimingStatus
from workers.cancellation import CancellationToken


class ManualSpeechError(RuntimeError):
    pass


def format_timecode(ms: int | None) -> str:
    if ms is None:
        return "—"
    value=max(0,int(ms));h=value//3_600_000;m=(value//60_000)%60;s=(value//1000)%60;mill=value%1000
    return f"{h:02d}:{m:02d}:{s:02d}.{mill:03d}" if h else f"{m:02d}:{s:02d}.{mill:03d}"


def parse_timecode(value: str | int | float) -> int:
    if isinstance(value,(int,float)):
        result=int(value)
        if result<0:raise ManualSpeechError("Time cannot be negative.")
        return result
    text=str(value or "").strip()
    if not text:raise ManualSpeechError("Enter a time value.")
    if text.isdigit():return int(text)
    if re.fullmatch(r"\d{1,2}:\d{2}\.\d{1,3}",text):
        mm,rest=text.split(":",1);ss,milli=rest.split(".",1);return int(mm)*60_000+int(ss)*1000+int(milli.ljust(3,"0")[:3])
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}\.\d{1,3}",text):
        hh,mm,rest=text.split(":",2);ss,milli=rest.split(".",1);return int(hh)*3_600_000+int(mm)*60_000+int(ss)*1000+int(milli.ljust(3,"0")[:3])
    raise ManualSpeechError("Use mm:ss.mmm or hh:mm:ss.mmm time format.")


@dataclass(slots=True)
class GenerationProgress:
    current: int
    total: int
    block_id: str
    speaker: str
    start_ms: int | None


class ManualSpeechEditorService:
    def __init__(self,blocks,multispeaker,audio_repository,voice_service,*,subtitle_service=None,transcript_repository=None,translation_repository=None,logger=None) -> None:
        self.blocks=blocks;self.multispeaker=multispeaker;self.audio=audio_repository;self.voices=voice_service
        self.subtitles=subtitle_service;self.transcripts=transcript_repository;self.translations=translation_repository;self.logger=logger

    def rows(self,project_id:str)->list[dict]:
        speakers={x.id:x for x in self.blocks.repository.speakers(project_id)}
        result=[]
        for block in self.blocks.for_project(project_id):
            speaker=speakers.get(block.speaker_id);voice=None
            try:
                resolved=self.blocks.voice_resolution(project_id,block.id);voice=self.voices.get(resolved["voiceId"])
            except Exception:pass
            takes=self.takes(project_id,block.id);duration=int((block.metadata or {}).get("generatedDurationMs",0) or 0);allocated=block.allocated_duration_ms;delta=duration-allocated if duration and allocated else 0
            result.append({**block.to_dict(),
                "startText":format_timecode(block.timeline_start_ms),"endText":format_timecode(block.timeline_end_ms),
                "speakerName":getattr(speaker,"name","") or "Unassigned","speakerRole":getattr(speaker,"role_code","") or "speaker",
                "voiceName":getattr(voice,"name","") or ("Source Audio" if block.source_type_code==SpeechSourceType.SOURCE_AUDIO.value else "Unresolved"),
                "durationMs":allocated,"durationDeltaMs":delta,"durationStatusText":self._duration_text(block.timing_status_code,delta),
                "audioStatusText":block.audio_status_code.replace("_"," ").title(),"takeCount":len(takes),"takes":takes,
                "canGenerate":block.source_type_code==SpeechSourceType.TTS.value and bool(block.text.strip()),
                "sourceAudio":block.source_type_code==SpeechSourceType.SOURCE_AUDIO.value})
        return result

    def speakers(self,project_id:str)->list[dict]:return [x.to_dict() for x in self.blocks.repository.speakers(project_id)]

    def voices_list(self,*,language:str="all",role:str="all",style:str="",tone:str="",energy:str="",favorites:bool=False)->list[dict]:
        result=[]
        for voice in self.voices.list_all():
            tags={str(x).casefold() for x in list(getattr(voice,"style_tags",[]) or [])};hay=" ".join([getattr(voice,"name",""),getattr(voice,"category",""),getattr(voice,"voice_description",""),*tags]).casefold()
            if language not in {"","all"} and getattr(voice,"language","")!=language:continue
            if role not in {"","all"} and role.casefold() not in str(getattr(voice,"category","")).casefold():continue
            if style and style.casefold() not in hay:continue
            if tone and tone.casefold() not in hay:continue
            if energy and energy.casefold() not in hay:continue
            if favorites and not bool(getattr(voice,"favorite",False)):continue
            result.append(voice.to_dict())
        return result

    def takes(self,project_id:str,block_id:str)->list[dict]:
        block=self.blocks.repository.block(project_id,block_id);active=str(getattr(block,"active_generated_audio_id","") or getattr(block,"audio_id","") or "") if block else ""
        items=self.audio.list_for_speech_block(project_id,block_id) if hasattr(self.audio,"list_for_speech_block") else []
        return [{**item.to_dict(),"active":item.id==active,"label":f"Take {len(items)-i}"} for i,item in enumerate(items)]

    def edit_text(self,project_id:str,block_id:str,text:str):return self.blocks.update(project_id,block_id,text=text,user_modified=True)
    def set_timing_text(self,project_id:str,block_id:str,start_text:str,end_text:str):return self.blocks.set_timing(project_id,block_id,parse_timecode(start_text),parse_timecode(end_text))
    def set_timing(self,project_id:str,block_id:str,start_ms:int,end_ms:int):return self.blocks.set_timing(project_id,block_id,start_ms,end_ms)
    def add(self,project_id:str,section_id:str,*,text:str="New speech",language:str="en",start_ms:int|None=None,end_ms:int|None=None,speaker_id:str="",source_type:str="tts"):
        return self.blocks.add(project_id,section_id,text,speaker_id=speaker_id,language=language,source_type=source_type,start_ms=start_ms,end_ms=end_ms)
    def delete(self,project_id:str,block_ids:Iterable[str])->None:
        for block_id in list(block_ids):self.blocks.delete(project_id,str(block_id))
    def split(self,*args,**kwargs):return self.blocks.split(*args,**kwargs)
    def merge(self,*args,**kwargs):return self.blocks.merge(*args,**kwargs)
    def find(self,*args,**kwargs):return self.blocks.find(*args,**kwargs)
    def replace(self,*args,**kwargs):return self.blocks.replace(*args,**kwargs)
    def bulk_assign(self,*args,**kwargs):return self.blocks.bulk_assign(*args,**kwargs)
    def activate_take(self,project_id:str,block_id:str,audio_id:str):return self.blocks.set_active_take(project_id,block_id,audio_id,self.audio)

    def generate(self,project_id:str,block_ids:Iterable[str]|None=None,*,outdated_only:bool=False,all_rows:bool=False,cancellation:CancellationToken|None=None,progress_callback=None)->list:
        ids=None if all_rows else [str(x) for x in (block_ids or [])]
        if not all_rows and not ids and not outdated_only:return []
        def progress(current,total,block):
            if progress_callback:
                speaker=self.blocks.repository.speaker(project_id,block.speaker_id) if block.speaker_id else None
                progress_callback(GenerationProgress(current,total,block.id,getattr(speaker,"name","") or "Speech",block.timeline_start_ms))
        items=self.multispeaker.generate_sequence(project_id,ids,cancellation,force=bool(ids) or outdated_only,outdated_only=outdated_only,progress_callback=progress)
        for audio in items:
            block_id=str((audio.metadata or {}).get("speechBlockId","") or "")
            if block_id:self.blocks.apply_generated_duration(project_id,block_id,int(audio.duration_ms))
        return items

    def update_subtitle_from_speech(self,project_id:str,block_id:str,track_id:str,*,confirm_edited:bool=False):
        if self.subtitles is None:raise ManualSpeechError("Subtitle service is unavailable.")
        block=self.blocks.repository.block(project_id,block_id)
        if block is None:raise ManualSpeechError("Speech block not found.")
        track,_,cues=self.subtitles.get(project_id,track_id)
        cue=next((q for q in cues if str((q.metadata or {}).get("speechBlockId","") or q.source_segment_id)==block_id),None)
        if cue is None:
            start=block.timeline_start_ms or 0;duration=max(300,block.allocated_duration_ms or 2000);cue=self.subtitles.add_cue(project_id,track_id,start,block.text,duration)
            cue.metadata["speechBlockId"]=block_id;self.subtitles.repository.update_cue(project_id,cue);return cue
        if cue.edited and not confirm_edited:raise ManualSpeechError("This subtitle was manually edited. Confirm before replacing it from speech text.")
        return self.subtitles.update_cue(project_id,track_id,cue.id,text=block.text,start_ms=block.timeline_start_ms if block.timeline_start_ms is not None else cue.start_ms,end_ms=block.timeline_end_ms if block.timeline_end_ms is not None else cue.end_ms)

    def update_speech_from_subtitle(self,project_id:str,block_id:str,track_id:str,cue_id:str):
        if self.subtitles is None:raise ManualSpeechError("Subtitle service is unavailable.")
        _,_,cues=self.subtitles.get(project_id,track_id);cue=next((q for q in cues if q.id==cue_id),None)
        if cue is None:raise ManualSpeechError("Subtitle cue not found.")
        self.blocks.update(project_id,block_id,text=cue.text,user_modified=True);return self.blocks.set_timing(project_id,block_id,cue.start_ms,cue.end_ms)

    def transcript_to_speech(self,project_id:str,section_id:str,transcript_id:str,segment_ids:Iterable[str]|None=None,*,speaker_id:str="",language:str="en")->list:
        if self.transcripts is None:raise ManualSpeechError("Transcript repository is unavailable.")
        selected=None if segment_ids is None else {str(x) for x in segment_ids};segments=self.transcripts.segments(transcript_id);created=[]
        for seg in segments:
            if selected is not None and seg.id not in selected:continue
            meta=dict(getattr(seg,"metadata",{}) or {});sid=speaker_id or str(meta.get("speakerId","") or "")
            created.append(self.blocks.add(project_id,section_id,seg.text,speaker_id=sid,language=language,start_ms=seg.start_ms,end_ms=max(seg.start_ms+1,seg.end_ms)))
        return created

    def translation_to_speech(self,project_id:str,section_id:str,translation_id:str,segment_ids:Iterable[str]|None=None,*,speaker_id:str="",language:str="en")->list:
        if self.translations is None:raise ManualSpeechError("Translation repository is unavailable.")
        selected=None if segment_ids is None else {str(x) for x in segment_ids};segments=self.translations.segments(translation_id);created=[]
        for seg in segments:
            if selected is not None and seg.id not in selected:continue
            text=seg.translated_text or seg.machine_translation
            if not text.strip():continue
            start=seg.start_ms if seg.start_ms is not None else 0;end=seg.end_ms if seg.end_ms is not None else start+2000
            block=self.blocks.add(project_id,section_id,text,speaker_id=speaker_id,language=language,start_ms=start,end_ms=max(start+1,end));block.metadata["translationSegmentId"]=seg.id;block.metadata["translationReviewed"]=bool(seg.reviewed);block.metadata["machineTranslated"]=not bool(seg.reviewed);self.blocks.repository.save_block(project_id,block);created.append(block)
        return created

    @staticmethod
    def _duration_text(status:str,delta_ms:int)->str:
        label=str(status).replace("_"," ").title()
        if not delta_ms:return label
        return f"{label} · {delta_ms/1000:+.2f}s {'long' if delta_ms>0 else 'short'}"

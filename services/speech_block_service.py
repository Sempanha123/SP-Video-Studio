from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from domain.phase22_errors import SpeechBlockInvalid
from domain.speech_block import (
    SpeechAudioStatus,
    SpeechBlock,
    SpeechSourceType,
    SpeechTimingStatus,
    speech_text_hash,
)
from storage.repositories.phase22_repository import Phase22Repository


class SpeechBlockService:
    """Canonical editor for SpeechBlock. No second TTS/timeline segment model is introduced."""
    def __init__(self, repository: Phase22Repository, speakers, languages) -> None:
        self.repository=repository;self.speakers=speakers;self.languages=languages

    def for_section(self,project_id:str,section_id:str,*,migrate_legacy:bool=True)->list[SpeechBlock]:
        return self.repository.ensure_legacy_block(project_id,section_id) if migrate_legacy else self.repository.blocks_for_section(section_id)
    def for_project(self,project_id:str)->list[SpeechBlock]:return self.repository.blocks_for_project(project_id)

    def add(self,project_id:str,section_id:str,text:str="",*,speaker_id:str="",language:str="en",source_type:str="tts",start_ms:int|None=None,end_ms:int|None=None,voice_override_id:str="")->SpeechBlock:
        self.languages.get(language)
        if speaker_id and self.repository.speaker(project_id,speaker_id) is None:raise SpeechBlockInvalid("Speaker not found.")
        if start_ms is not None or end_ms is not None:
            start=0 if start_ms is None else int(start_ms);end=(start+2000) if end_ms is None else int(end_ms);self._validate_time(start,end)
        else:start=end=None
        items=self.repository.blocks_for_section(section_id)
        item=SpeechBlock(project_id=project_id,script_section_id=section_id,order=len(items),text=text,speaker_id=speaker_id,
                         language=language,voice_override_id=voice_override_id,speech_source_type=source_type,
                         timeline_start_ms=start,timeline_end_ms=end,text_hash=speech_text_hash(text),user_modified=bool(text))
        return self.repository.save_block(project_id,item)

    def update(self,project_id:str,block_id:str,**updates)->SpeechBlock:
        item=self._get(project_id,block_id);before=(item.text,item.speaker_id,item.voice_override_id,item.language,item.source_type_code)
        aliases={"speakerId":"speaker_id","voiceOverrideId":"voice_override_id","sourceType":"speech_source_type","speechSourceType":"speech_source_type",
                 "pauseBeforeMs":"pause_before_ms","pauseAfterMs":"pause_after_ms","sceneId":"scene_id","startOffsetMs":"start_offset_ms",
                 "audioId":"audio_id","timelineStartMs":"timeline_start_ms","timelineEndMs":"timeline_end_ms","activeGeneratedAudioId":"active_generated_audio_id",
                 "audioStatus":"audio_status","timingStatus":"timing_status","userModified":"user_modified"}
        allowed={"speaker_id","text","language","voice_override_id","speech_source_type","pause_before_ms","pause_after_ms","scene_id","start_offset_ms","audio_id",
                 "timeline_start_ms","timeline_end_ms","active_generated_audio_id","audio_status","timing_status","user_modified","metadata"}
        for key,value in updates.items():
            attr=aliases.get(key,key)
            if attr not in allowed:continue
            if attr=="language":self.languages.get(str(value))
            if attr=="speaker_id" and value and self.repository.speaker(project_id,str(value)) is None:raise SpeechBlockInvalid("Speaker not found.")
            setattr(item,attr,value)
        if item.timeline_start_ms is not None or item.timeline_end_ms is not None:
            if item.timeline_start_ms is None or item.timeline_end_ms is None:raise SpeechBlockInvalid("Both speech start and end are required when timing is set.")
            self._validate_time(item.timeline_start_ms,item.timeline_end_ms)
        after=(item.text,item.speaker_id,item.voice_override_id,item.language,item.source_type_code)
        if after!=before:
            item.text_hash=speech_text_hash(item.text);item.user_modified=True
            if item.active_generated_audio_id or item.audio_id:item.audio_status=SpeechAudioStatus.OUTDATED
            elif item.source_type_code==SpeechSourceType.TTS.value:item.audio_status=SpeechAudioStatus.NOT_GENERATED
            item.timing_status=SpeechTimingStatus.NEEDS_REVIEW if (item.active_generated_audio_id or item.audio_id) else SpeechTimingStatus.NOT_GENERATED
        return self.repository.save_block(project_id,item)

    def set_timing(self,project_id:str,block_id:str,start_ms:int,end_ms:int,*,mark_adjusted:bool=True)->SpeechBlock:
        self._validate_time(start_ms,end_ms);item=self._get(project_id,block_id);item.timeline_start_ms=int(start_ms);item.timeline_end_ms=int(end_ms)
        if not item.scene_id:item.start_offset_ms=int(start_ms)
        if mark_adjusted and item.active_generated_audio_id:item.timing_status=SpeechTimingStatus.ADJUSTED
        return self.repository.save_block(project_id,item)

    def bulk_assign(self,project_id:str,block_ids:Iterable[str],*,speaker_id:str|None=None,voice_id:str|None=None,language:str|None=None)->list[SpeechBlock]:
        ids={str(x) for x in block_ids};changed=[]
        if language is not None:self.languages.get(language)
        if speaker_id and self.repository.speaker(project_id,speaker_id) is None:raise SpeechBlockInvalid("Speaker not found.")
        for item in self.for_project(project_id):
            if item.id not in ids:continue
            updates={}
            if speaker_id is not None:updates["speaker_id"]=speaker_id
            if voice_id is not None:updates["voice_override_id"]=voice_id
            if language is not None:updates["language"]=language
            changed.append(self.update(project_id,item.id,**updates))
        return changed

    def split(self,project_id:str,block_id:str,split_ms:int,text_before:str,text_after:str)->tuple[SpeechBlock,SpeechBlock]:
        original=self._get(project_id,block_id);split=int(split_ms)
        if original.timeline_start_ms is None or original.timeline_end_ms is None:raise SpeechBlockInvalid("Set Start and End before splitting this speech block.")
        if split<=original.timeline_start_ms or split>=original.timeline_end_ms:raise SpeechBlockInvalid("Split time must be inside the speech block.")
        if not text_before.strip() or not text_after.strip():raise SpeechBlockInvalid("Both split speech texts are required.")
        first=deepcopy(original);first.text=text_before;first.timeline_end_ms=split;first.text_hash=speech_text_hash(text_before);first.audio_status=SpeechAudioStatus.OUTDATED if first.active_generated_audio_id else SpeechAudioStatus.NOT_GENERATED;first.timing_status=SpeechTimingStatus.NEEDS_REVIEW;first.user_modified=True
        second=deepcopy(original);from uuid import uuid4;second.block_id=str(uuid4());second.order=original.order+1;second.text=text_after;second.timeline_start_ms=split;second.start_offset_ms=split if not second.scene_id else second.start_offset_ms;second.text_hash=speech_text_hash(text_after);second.audio_id="";second.active_generated_audio_id="";second.audio_status=SpeechAudioStatus.NOT_GENERATED;second.timing_status=SpeechTimingStatus.NOT_GENERATED;second.user_modified=True
        section=self.repository.blocks_for_section(original.script_section_id)
        for item in section:
            if item.order>original.order:item.order+=1
        self.repository.save_blocks(project_id,[x for x in section if x.id!=original.id]);self.repository.save_block(project_id,first);self.repository.save_block(project_id,second)
        return self._get(project_id,first.id),self._get(project_id,second.id)

    def merge(self,project_id:str,first_id:str,second_id:str,*,speaker_id:str|None=None,voice_id:str|None=None)->SpeechBlock:
        a=self._get(project_id,first_id);b=self._get(project_id,second_id)
        if a.script_section_id!=b.script_section_id:raise SpeechBlockInvalid("Only speech blocks in the same script section can be merged.")
        items=self.repository.blocks_for_section(a.script_section_id);ids=[x.id for x in items]
        if second_id not in ids or first_id not in ids or ids.index(second_id)!=ids.index(first_id)+1:raise SpeechBlockInvalid("Only adjacent speech blocks can be merged.")
        chosen_speaker=speaker_id if speaker_id is not None else (a.speaker_id if a.speaker_id==b.speaker_id else "")
        chosen_voice=voice_id if voice_id is not None else (a.voice_override_id if a.voice_override_id==b.voice_override_id else "")
        if a.speaker_id!=b.speaker_id and speaker_id is None:raise SpeechBlockInvalid("Choose which speaker to keep before merging these blocks.")
        if a.voice_override_id!=b.voice_override_id and voice_id is None:raise SpeechBlockInvalid("Choose which voice to keep before merging these blocks.")
        a.text=self._join_text(a.text,b.text,a.language);a.text_hash=speech_text_hash(a.text);a.speaker_id=chosen_speaker;a.voice_override_id=chosen_voice
        if a.timeline_start_ms is not None and b.timeline_end_ms is not None:a.timeline_end_ms=b.timeline_end_ms
        a.audio_status=SpeechAudioStatus.OUTDATED if a.active_generated_audio_id else SpeechAudioStatus.NOT_GENERATED;a.timing_status=SpeechTimingStatus.NEEDS_REVIEW;a.user_modified=True
        self.repository.save_block(project_id,a);self.repository.delete_block(project_id,b.id);self.repository.normalize_block_order(project_id,a.script_section_id);return self._get(project_id,a.id)

    def find(self,project_id:str,query:str,*,case_sensitive:bool=False)->list[SpeechBlock]:
        q=query if case_sensitive else query.casefold();return [x for x in self.for_project(project_id) if q in (x.text if case_sensitive else x.text.casefold())]

    def replace(self,project_id:str,query:str,replacement:str,*,block_ids:Iterable[str]|None=None,replace_all:bool=True,case_sensitive:bool=False)->list[SpeechBlock]:
        if not query:return []
        selected=None if block_ids is None else {str(x) for x in block_ids};changed=[]
        for item in self.for_project(project_id):
            if selected is not None and item.id not in selected:continue
            source=item.text
            if case_sensitive:
                if query not in source:continue
                new=source.replace(query,replacement,-1 if replace_all else 1)
            else:
                low=source.casefold();needle=query.casefold();pos=low.find(needle)
                if pos<0:continue
                if not replace_all:new=source[:pos]+replacement+source[pos+len(query):]
                else:
                    pieces=[];cursor=0
                    while True:
                        pos=low.find(needle,cursor)
                        if pos<0:pieces.append(source[cursor:]);break
                        pieces.extend((source[cursor:pos],replacement));cursor=pos+len(query)
                    new="".join(pieces)
            changed.append(self.update(project_id,item.id,text=new))
        return changed

    def set_active_take(self,project_id:str,block_id:str,audio_id:str,audio_repository)->SpeechBlock:
        item=self._get(project_id,block_id);audio=audio_repository.get(audio_id)
        if audio is None or str(audio.project_id)!=project_id:raise SpeechBlockInvalid("Generated take not found in this project.")
        if str((audio.metadata or {}).get("speechBlockId",""))!=block_id:raise SpeechBlockInvalid("Generated take does not belong to this speech block.")
        item.active_generated_audio_id=audio.id;item.audio_id=audio.id;item.audio_status=SpeechAudioStatus.READY;self.repository.save_block(project_id,item);self.apply_generated_duration(project_id,item.id,int(audio.duration_ms));return self._get(project_id,item.id)

    def apply_generated_duration(self,project_id:str,block_id:str,duration_ms:int)->SpeechBlock:
        item=self._get(project_id,block_id);allocated=item.allocated_duration_ms;duration=max(0,int(duration_ms))
        item.metadata["generatedDurationMs"]=duration;item.metadata["durationDeltaMs"]=duration-allocated if allocated else 0
        if allocated<=0:item.timing_status=SpeechTimingStatus.NEEDS_REVIEW
        else:
            delta=duration-allocated;ratio=duration/max(1,allocated)
            if abs(delta)<=1000 or 0.92<=ratio<=1.08:item.timing_status=SpeechTimingStatus.FITS
            elif delta<0:item.timing_status=SpeechTimingStatus.SHORT
            elif ratio>1.35:item.timing_status=SpeechTimingStatus.VERY_LONG
            else:item.timing_status=SpeechTimingStatus.LONG
        return self.repository.save_block(project_id,item)

    def fit_audio(self,project_id:str,block_id:str,duration_ms:int)->SpeechBlock:
        item=self._get(project_id,block_id);allocated=item.allocated_duration_ms
        if allocated<=0 or duration_ms<=0:raise SpeechBlockInvalid("Speech timing and generated duration are required before fitting audio.")
        rate=float(duration_ms)/float(allocated)
        if not 0.8<=rate<=1.25:raise SpeechBlockInvalid("The required speed change is too large. Extend the segment or regenerate instead.")
        item.metadata["fitAudioRate"]=round(rate,6);item.timing_status=SpeechTimingStatus.ADJUSTED;return self.repository.save_block(project_id,item)

    def extend_segment(self,project_id:str,block_id:str,duration_ms:int)->SpeechBlock:
        item=self._get(project_id,block_id)
        if item.timeline_start_ms is None:raise SpeechBlockInvalid("Set speech timing first.")
        item.timeline_end_ms=item.timeline_start_ms+max(1,int(duration_ms));item.timing_status=SpeechTimingStatus.ADJUSTED;return self.repository.save_block(project_id,item)

    def move(self,project_id:str,block_id:str,new_index:int)->list[SpeechBlock]:
        item=self._get(project_id,block_id);items=self.repository.blocks_for_section(item.script_section_id);old=next((i for i,v in enumerate(items) if v.id==block_id),-1)
        if old<0:raise SpeechBlockInvalid("Speech block not found.")
        moving=items.pop(old);items.insert(max(0,min(int(new_index),len(items))),moving)
        for order,block in enumerate(items):block.order=order
        self.repository.save_blocks(project_id,items);return self.repository.blocks_for_section(item.script_section_id)

    def delete(self,project_id:str,block_id:str)->None:
        item=self._get(project_id,block_id);section_id=item.script_section_id;self.repository.delete_block(project_id,block_id);self.repository.normalize_block_order(project_id,section_id)

    def voice_resolution(self,project_id:str,block_id:str)->dict[str,str]:
        item=self._get(project_id,block_id);voice,source=self.speakers.resolve_voice(project_id,item);return {"speakerId":item.speaker_id,"voiceId":voice.voice_id,"source":source,"language":item.language}

    def _get(self,project_id:str,block_id:str)->SpeechBlock:
        item=self.repository.block(project_id,block_id)
        if item is None:raise SpeechBlockInvalid("Speech block not found.")
        return item
    @staticmethod
    def _validate_time(start_ms:int,end_ms:int)->None:
        if int(start_ms)<0:raise SpeechBlockInvalid("Speech start cannot be negative.")
        if int(end_ms)<=int(start_ms):raise SpeechBlockInvalid("Speech end must be after start.")
    @staticmethod
    def _join_text(a:str,b:str,language:str)->str:
        a=a.rstrip();b=b.lstrip()
        if not a:return b
        if not b:return a
        # Khmer/Thai scripts do not require Latin-style word spacing.
        if language in {"km","th"}:return a+b
        return a+" "+b

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from domain.generated_audio import GeneratedAudio
from domain.speech_block import SpeechAudioStatus, SpeechSourceType
from engines.tts.types import TTSRequest
from workers.cancellation import CancellationToken


class MultiSpeakerTTSService:
    """Existing Phase 22 multi-speaker TTS engine with take-safe regeneration."""
    def __init__(self, repository, speakers, voice_service, tts_service, audio_repository, project_repository) -> None:
        self.repository=repository;self.speakers=speakers;self.voices=voice_service;self.tts=tts_service;self.audio=audio_repository;self.projects=project_repository

    def _completed_audio(self,block):
        audio_id=str(getattr(block,'active_generated_audio_id','') or getattr(block,'audio_id','') or '')
        if not audio_id:return None
        item=None
        for name in ('get_by_id','get'):
            getter=getattr(self.audio,name,None)
            if callable(getter):
                try:item=getter(audio_id)
                except Exception:item=None
                if item is not None:break
        path=Path(str(getattr(item,'file_path','') or '')) if item is not None else None
        return item if path is not None and path.is_file() else None

    def generate_block(self,project_id:str,block_id:str,cancellation:CancellationToken|None=None,*,force:bool=False)->GeneratedAudio:
        block=self.repository.block(project_id,block_id)
        if block is None:raise KeyError('Speech block not found.')
        if block.source_type_code!=SpeechSourceType.TTS.value:raise ValueError('This speech block uses source/manual audio. TTS is not automatic.')
        if not block.text.strip():raise ValueError('Speech text is required before generation.')
        existing=self._completed_audio(block)
        if existing is not None and not force and str(getattr(block,'audio_status_code',''))!='outdated':return existing
        previous_id=str(getattr(block,'active_generated_audio_id','') or getattr(block,'audio_id','') or '')
        block.audio_status=SpeechAudioStatus.GENERATING;self.repository.save_block(project_id,block)
        try:
            voice,resolution=self.speakers.resolve_voice(project_id,block);project=self.projects.get_by_id(project_id)
            if project is None:raise KeyError('Project not found.')
            root=Path(project.project_path)/'generated'/'speech';root.mkdir(parents=True,exist_ok=True);output=root/f'{block.id}-{uuid4().hex[:8]}.wav'
            config=self.voices.voice_config(voice.voice_id)
            request=TTSRequest(project_id=project_id,text=block.text,language=block.language,output_path=output,voice_config=config,section_id=block.script_section_id,
                metadata={'speechBlockId':block.id,'speakerId':block.speaker_id,'voiceId':voice.voice_id,'voiceResolution':resolution})
            result=self.tts.generate(request,cancellation)
            text_hash=hashlib.sha256(block.text.encode('utf-8')).hexdigest()
            item=GeneratedAudio(project_id=project_id,engine=voice.engine_id or 'voxcpm2',model_id='voxcpm2',language=block.language,
                voice_mode=config.mode_code,voice_config=config.to_dict() if hasattr(config,'to_dict') else {},text_hash=text_hash,file_path=str(result.output_path),
                section_id=block.script_section_id,duration_ms=result.duration_ms,sample_rate=result.sample_rate,channels=result.channels,
                metadata={'speechBlockId':block.id,'speakerId':block.speaker_id,'voiceId':voice.voice_id,'voiceResolution':resolution,
                          'engineVersion':result.engine_version,'modelVersion':result.model_version,'take':True})
            self.audio.create(item)
            block.active_generated_audio_id=item.id;block.audio_id=item.id;block.text_hash=text_hash;block.audio_status=SpeechAudioStatus.READY
            block.metadata.update({'generatedVoiceId':voice.voice_id,'generatedSpeakerId':block.speaker_id,'generatedTextHash':item.text_hash,
                                   'generatedDurationMs':int(result.duration_ms)})
            self.repository.save_block(project_id,block);return item
        except Exception:
            # A failed/cancelled regeneration must never destroy the last successful take.
            latest=self.repository.block(project_id,block_id) or block
            latest.active_generated_audio_id=previous_id;latest.audio_id=previous_id
            if cancellation is not None and cancellation.is_cancelled:
                latest.audio_status=SpeechAudioStatus.CANCELLED
            else:
                latest.audio_status=SpeechAudioStatus.FAILED if not previous_id else SpeechAudioStatus.OUTDATED
            self.repository.save_block(project_id,latest)
            raise

    def generate_sequence(self,project_id:str,block_ids:list[str]|None=None,cancellation:CancellationToken|None=None,*,force:bool=False,outdated_only:bool=False,progress_callback=None)->list[GeneratedAudio]:
        selected=set(block_ids or []);candidates=[]
        for block in self.repository.blocks_for_project(project_id):
            if selected and block.id not in selected:continue
            if block.source_type_code!=SpeechSourceType.TTS.value or not block.text.strip():continue
            if outdated_only and str(getattr(block,'audio_status_code',''))!='outdated':continue
            candidates.append(block)
        result=[];total=len(candidates)
        for index,block in enumerate(candidates,1):
            if cancellation:cancellation.raise_if_cancelled()
            block.audio_status=SpeechAudioStatus.QUEUED;self.repository.save_block(project_id,block)
            if progress_callback:progress_callback(index,total,block)
            existing=self._completed_audio(block)
            result.append(existing if existing is not None and not force and str(getattr(block,'audio_status_code',''))!='outdated' else self.generate_block(project_id,block.id,cancellation,force=force or outdated_only))
        return result

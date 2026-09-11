from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any

@dataclass(slots=True)
class AudioClip:
    clip_id:str; project_id:str; track_id:str; source_path:str; timeline_start_ms:int; duration_ms:int; source_in_ms:int=0; source_out_ms:int=0; gain_db:float=0.0; pan:float=0.0; fade_in_ms:int=0; fade_out_ms:int=0; muted:bool=False; speaker_id:str=''; speaker_name:str=''; language:str=''; source_audio_id:str=''; metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def id(self):return self.clip_id
    @property
    def end_ms(self):return self.timeline_start_ms+self.duration_ms
    def validate(self):
        if not self.clip_id or not self.project_id or not self.track_id:raise ValueError('Audio clip requires id, project and track.')
        if not self.source_path:raise ValueError('Audio clip source is missing.')
        if self.timeline_start_ms<0 or self.duration_ms<=0 or self.source_in_ms<0:raise ValueError('Audio clip timing is invalid.')
        if self.source_out_ms and self.source_out_ms<=self.source_in_ms:raise ValueError('Audio source range is invalid.')
        if not -60.0<=float(self.gain_db)<=12.0:raise ValueError('Clip gain must be between -60 and +12 dB.')
        if not -1.0<=float(self.pan)<=1.0:raise ValueError('Clip pan must be between -1 and +1.')
        if self.fade_in_ms<0 or self.fade_out_ms<0 or self.fade_in_ms+self.fade_out_ms>self.duration_ms:raise ValueError('Audio clip fades are invalid.')
    def to_dict(self):
        return {'id':self.id,'projectId':self.project_id,'trackId':self.track_id,'sourcePath':self.source_path,'timelineStartMs':self.timeline_start_ms,'durationMs':self.duration_ms,'sourceInMs':self.source_in_ms,'sourceOutMs':self.source_out_ms,'gainDb':self.gain_db,'pan':self.pan,'fadeInMs':self.fade_in_ms,'fadeOutMs':self.fade_out_ms,'muted':self.muted,'speakerId':self.speaker_id,'speakerName':self.speaker_name,'language':self.language,'sourceAudioId':self.source_audio_id,'metadata':dict(self.metadata)}

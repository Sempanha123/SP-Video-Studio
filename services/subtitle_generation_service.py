from __future__ import annotations

from domain.subtitle import SubtitleTrack, SubtitleTrackStatus, SubtitleTrackType, subtitle_source_fingerprint
from domain.subtitle_cue import SubtitleCue, subtitle_cue_source_hash
from domain.subtitle_word import SubtitleWord
from domain.subtitle_style import SubtitleStyle
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository


class SubtitleGenerationService:
    def __init__(self, transcript_repository: TranscriptRepository, translation_repository: TranslationRepository) -> None:
        self.transcript_repository=transcript_repository; self.translation_repository=translation_repository

    def from_transcript(self, project_id:str, transcript_id:str, name:str, style:SubtitleStyle, *, default:bool=False)->tuple[SubtitleTrack,list[SubtitleCue]]:
        transcript=self.transcript_repository.get(transcript_id)
        if transcript is None or transcript.project_id!=project_id: raise ValueError("Transcript does not belong to this project.")
        language=transcript.detected_language or (transcript.language_mode if transcript.language_mode!='auto' else 'en')
        segments=self.transcript_repository.segments(transcript_id)
        track=SubtitleTrack(project_id=project_id,name=name,language=language,track_type=SubtitleTrackType.TRANSCRIPT,source_type='transcript',source_id=transcript_id,source_language=language,status=SubtitleTrackStatus.READY,style_id=style.style_id,is_default=default,metadata={"sourceFingerprint":subtitle_source_fingerprint([(s.segment_id,s.text,s.start_ms,s.end_ms) for s in segments])})
        cues=[]
        for index,seg in enumerate(segments):
            cue=SubtitleCue(track_id=track.track_id,order=index,start_ms=seg.start_ms,end_ms=seg.end_ms,text=seg.text,source_segment_id=seg.segment_id,source_hash=subtitle_cue_source_hash(seg.segment_id,seg.text,seg.start_ms,seg.end_ms))
            cue.words=[SubtitleWord(cue_id=cue.cue_id,order=i,text=w.text,start_ms=w.start_ms,end_ms=w.end_ms,probability=w.probability,metadata=dict(w.metadata)) for i,w in enumerate(seg.words)]
            cues.append(cue)
        return track,cues

    def from_translation(self, project_id:str, translation_id:str, name:str, style:SubtitleStyle, *, default:bool=False)->tuple[SubtitleTrack,list[SubtitleCue]]:
        translation=self.translation_repository.get(translation_id)
        if translation is None or translation.project_id!=project_id: raise ValueError("Translation does not belong to this project.")
        segments=[s for s in self.translation_repository.segments(translation_id) if s.start_ms is not None and s.end_ms is not None and s.translated_text.strip()]
        if not segments: raise ValueError("This translation does not contain timed segments.")
        track=SubtitleTrack(project_id=project_id,name=name,language=translation.target_language,track_type=SubtitleTrackType.TRANSLATION,source_type='translation',source_id=translation_id,source_language=translation.source_language,status=SubtitleTrackStatus.READY,style_id=style.style_id,is_default=default,metadata={"translationReviewed":all(s.reviewed for s in segments),"sourceFingerprint":subtitle_source_fingerprint([(s.segment_id,s.translated_text,s.start_ms,s.end_ms) for s in segments])})
        cues=[SubtitleCue(track_id=track.track_id,order=i,start_ms=int(s.start_ms),end_ms=int(s.end_ms),text=s.translated_text,source_segment_id=s.segment_id,source_hash=subtitle_cue_source_hash(s.segment_id,s.translated_text,s.start_ms,s.end_ms),metadata={"reviewed":s.reviewed}) for i,s in enumerate(segments)]
        return track,cues

    def bilingual(self, project_id:str, transcript_id:str, translation_id:str, name:str, style:SubtitleStyle, *, primary='source', default=False)->tuple[SubtitleTrack,list[SubtitleCue]]:
        transcript=self.transcript_repository.get(transcript_id); translation=self.translation_repository.get(translation_id)
        if transcript is None or transcript.project_id!=project_id: raise ValueError("Transcript does not belong to this project.")
        if translation is None or translation.project_id!=project_id or translation.source_id!=transcript_id: raise ValueError("Translation is not aligned to the selected transcript.")
        trans_by_source={s.source_segment_id:s for s in self.translation_repository.segments(translation_id)}
        source_segments=self.transcript_repository.segments(transcript_id)
        source_language=transcript.detected_language or (transcript.language_mode if transcript.language_mode!='auto' else translation.source_language)
        target_language=translation.target_language
        language=source_language if primary=='source' else target_language; secondary=target_language if primary=='source' else source_language
        track=SubtitleTrack(project_id=project_id,name=name,language=language,track_type=SubtitleTrackType.BILINGUAL,source_type='translation',source_id=translation_id,source_language=source_language,status=SubtitleTrackStatus.READY,style_id=style.style_id,is_default=default,is_bilingual=True,secondary_language=secondary,metadata={"transcriptId":transcript_id,"primaryOrder":primary})
        cues=[]; missing=[]
        for seg in source_segments:
            translated=trans_by_source.get(seg.segment_id)
            if translated is None or not translated.translated_text.strip(): missing.append(seg.segment_id); continue
            source_text,target_text=seg.text,translated.translated_text
            text,secondary_text=(source_text,target_text) if primary=='source' else (target_text,source_text)
            cue=SubtitleCue(track_id=track.track_id,order=len(cues),start_ms=seg.start_ms,end_ms=seg.end_ms,text=text,secondary_text=secondary_text,source_segment_id=seg.segment_id,source_hash=subtitle_cue_source_hash(seg.segment_id,source_text+'\0'+target_text,seg.start_ms,seg.end_ms),metadata={"translationSegmentId":translated.segment_id})
            if primary=='source': cue.words=[SubtitleWord(cue_id=cue.cue_id,order=i,text=w.text,start_ms=w.start_ms,end_ms=w.end_ms,probability=w.probability) for i,w in enumerate(seg.words)]
            cues.append(cue)
        if missing: track.metadata['unmatchedSourceSegmentIds']=missing
        return track,cues

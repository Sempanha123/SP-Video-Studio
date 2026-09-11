from __future__ import annotations

from dataclasses import dataclass

from domain.subtitle_cue import SubtitleCue
from domain.subtitle_word import SubtitleWord
from domain.shorts_errors import ShortCaptionError
from storage.repositories.short_repository import ShortRepository
from storage.repositories.transcript_repository import TranscriptRepository


SHORT_CAPTION_PRESETS = ("creator","bold","karaoke","clean")


@dataclass(frozen=True, slots=True)
class CaptionGrouping:
    max_words: int = 4
    max_chars: int = 32
    max_duration_ms: int = 2200


class ShortCaptionService:
    def __init__(self, shorts: ShortRepository, transcripts: TranscriptRepository, subtitle_service, language_service=None) -> None:
        self.shorts=shorts; self.transcripts=transcripts; self.subtitle_service=subtitle_service; self.languages=language_service

    def group_words(self, words, language: str, settings: CaptionGrouping | None=None) -> list[dict[str,object]]:
        config=settings or CaptionGrouping(); items=[w for w in words if str(getattr(w,"text","") or "").strip()]
        groups=[]; current=[]
        for word in items:
            candidate=current+[word]
            text=self._text(candidate,language)
            duration=int(getattr(candidate[-1],"end_ms",0))-int(getattr(candidate[0],"start_ms",0))
            if current and (len(candidate)>max(1,config.max_words) or len(text)>max(4,config.max_chars) or duration>max(300,config.max_duration_ms)):
                groups.append(self._row(current,language)); current=[word]
            else: current=candidate
        if current: groups.append(self._row(current,language))
        return groups

    def build_candidate_cues(self, candidate_id: str, *, max_words: int=4, max_chars: int=32, max_duration_ms: int=2200) -> list[dict[str,object]]:
        candidate=self.shorts.get_candidate(candidate_id)
        if candidate is None: raise ShortCaptionError("Short candidate could not be found.")
        segments=self.shorts.segments(candidate_id); transcript_id=candidate.source_id if candidate.source_type_code=="transcript" else str(candidate.metadata.get("transcriptId","") or "")
        if not transcript_id: raise ShortCaptionError("Create or select a transcript before generating timed Short captions.")
        transcript=self.transcripts.get(transcript_id)
        if transcript is None: raise ShortCaptionError("Transcript could not be found.")
        source_segments=self.transcripts.segments(transcript_id); words=[word for seg in source_segments for word in seg.words]
        settings=CaptionGrouping(max(2,min(6,int(max_words))),max(8,int(max_chars)),max(500,int(max_duration_ms)))
        output=[]; assembled=0
        for short_segment in segments:
            selected=[w for w in words if int(w.start_ms)>=short_segment.source_start_ms and int(w.end_ms)<=short_segment.source_end_ms]
            for row in self.group_words(selected,candidate.language,settings):
                output.append({**row,"startMs":assembled+int(row["startMs"])-short_segment.source_start_ms,
                               "endMs":assembled+int(row["endMs"])-short_segment.source_start_ms})
            assembled+=short_segment.duration_ms
        return output

    def create_track(self, project_id: str, candidate_id: str, *, preset_id: str="creator", max_words: int=4) -> str:
        preset=preset_id if preset_id in SHORT_CAPTION_PRESETS else "clean"
        candidate=self.shorts.get_candidate(candidate_id)
        if candidate is None or candidate.project_id!=project_id: raise ShortCaptionError("Short candidate could not be found in this project.")
        rows=self.build_candidate_cues(candidate_id,max_words=max_words)
        track=self.subtitle_service.create_manual(project_id,candidate.language,name=f"{candidate.title} Captions",preset_id=preset)
        cues=[]
        for order,row in enumerate(rows):
            cue=SubtitleCue(track_id=track.id,order=order,start_ms=int(row["startMs"]),end_ms=int(row["endMs"]),text=str(row["text"]),
                            edited=False,metadata={"shortCandidateId":candidate.id,"shortCaption":True})
            cue.words=[]
            for wi,w in enumerate(row["words"]):
                cue.words.append(SubtitleWord(cue_id=cue.id,order=wi,text=str(w["text"]),start_ms=int(w["startMs"]),end_ms=int(w["endMs"]),probability=w.get("probability")))
            cues.append(cue)
        self.subtitle_service.repository.replace_cues(project_id,track.id,cues)
        return track.id

    def apply_preset(self, project_id: str, track_id: str, preset_id: str) -> object:
        if preset_id not in SHORT_CAPTION_PRESETS: raise ShortCaptionError("Unknown Short caption preset.")
        return self.subtitle_service.apply_preset(project_id,track_id,preset_id)

    def word_highlight_available(self, project_id: str, track_id: str) -> bool:
        try: _,_,cues=self.subtitle_service.get(project_id,track_id)
        except Exception: return False
        return bool(cues) and all(bool(cue.words) for cue in cues)

    @staticmethod
    def _text(words,language:str) -> str:
        raw=[str(getattr(w,"text","") or "") for w in words]
        # Preserve explicit leading whitespace emitted by Whisper when available.
        if any(text[:1].isspace() for text in raw): return "".join(raw).strip()
        tokens=[text.strip() for text in raw if text.strip()]
        return ("" if language=="th" else " ").join(tokens)

    @classmethod
    def _row(cls,words,language:str) -> dict[str,object]:
        return {"text":cls._text(words,language),"startMs":int(words[0].start_ms),"endMs":int(words[-1].end_ms),
                "words":[{"text":str(w.text).strip(),"startMs":int(w.start_ms),"endMs":int(w.end_ms),"probability":getattr(w,"probability",None)} for w in words]}

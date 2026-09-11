from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from domain.short_candidate import ShortCandidate, ShortCandidateStatus
from domain.short_project import ShortSourceType
from domain.short_segment import ShortSegment
from domain.shorts_errors import ShortCandidateInvalid, ShortInvalidRange, ShortSourceMissing
from storage.repositories.media_repository import MediaRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.short_repository import ShortRepository
from storage.repositories.transcript_repository import TranscriptRepository


class ShortCandidateService:
    """Manual/deterministic highlight selection. It never claims semantic or viral ranking."""
    def __init__(self, repository: ShortRepository, media: MediaRepository, transcripts: TranscriptRepository, scenes: SceneRepository) -> None:
        self.repository=repository; self.media=media; self.transcripts=transcripts; self.scenes=scenes

    def create_manual(self, project_id: str, media_id: str, start_ms: int, end_ms: int, *, title: str="Short", language: str="en", target_duration_ms: int=30_000, source_type: str="video") -> ShortCandidate:
        self._range(start_ms,end_ms); asset=self.media.get_by_id(media_id)
        if asset is None or asset.project_id!=project_id or asset.type!="video": raise ShortSourceMissing()
        if asset.duration_ms and int(end_ms)>int(asset.duration_ms): raise ShortInvalidRange("The Out point is outside the source video.")
        fingerprint=self.media_fingerprint(asset)
        stype=ShortSourceType(source_type) if source_type in {"video","dub","manual"} else ShortSourceType.VIDEO
        candidate=ShortCandidate(project_id,stype,media_id,title.strip() or "Short",int(start_ms),int(end_ms),language=language,
                                 source_project_id=project_id,source_entity_ids=[media_id],source_fingerprint=fingerprint,
                                 score_metadata={"selection":"manual"},metadata={"targetDurationMs":int(target_duration_ms),"suggested":False})
        segment=ShortSegment(candidate.id,0,int(start_ms),int(end_ms),media_id,{"mediaId":media_id})
        self.repository.save_candidate(candidate,[segment]); return candidate

    def create_from_transcript(self, project_id: str, transcript_id: str, segment_ids: Iterable[str], *, title: str="Transcript Short", target_duration_ms: int=30_000) -> ShortCandidate:
        transcript=self.transcripts.get(transcript_id)
        if transcript is None or transcript.project_id!=project_id: raise ShortSourceMissing("Transcript could not be found in this project.")
        selected_set={str(x) for x in segment_ids}; all_segments=self.transcripts.segments(transcript_id); selected=[x for x in all_segments if x.id in selected_set]
        if not selected: raise ShortCandidateInvalid("Select at least one transcript segment.")
        selected.sort(key=lambda x:(x.start_ms,x.order)); start=selected[0].start_ms; end=selected[-1].end_ms; self._range(start,end)
        text=" ".join(x.text.strip() for x in selected if x.text.strip())
        raw={"transcript":transcript_id,"updated":getattr(transcript,"updated_at",""),"segments":[(x.id,x.start_ms,x.end_ms,x.text) for x in selected]}
        fingerprint=self._hash(raw)
        language=transcript.detected_language or (transcript.language_mode if transcript.language_mode!="auto" else "en")
        candidate=ShortCandidate(project_id,ShortSourceType.TRANSCRIPT,transcript_id,title.strip() or "Transcript Short",start,end,language=language,
                                 source_project_id=project_id,source_entity_ids=[x.id for x in selected],source_fingerprint=fingerprint,
                                 score_metadata={"selection":"transcript"},metadata={"mediaId":transcript.media_id,"text":text,"targetDurationMs":target_duration_ms})
        # Transcript selection is intentionally one contiguous source range; selected IDs remain attached for provenance.
        segment=ShortSegment(candidate.id,0,start,end,transcript_id,{"mediaId":transcript.media_id,"transcriptSegmentIds":[x.id for x in selected]})
        self.repository.save_candidate(candidate,[segment]); return candidate

    def create_from_scenes(self, project_id: str, scene_ids: Iterable[str], *, title: str="Scene Short", target_duration_ms: int=30_000, source_type: str="scenes", language: str="en") -> ShortCandidate:
        wanted={str(x) for x in scene_ids}; scenes=[x for x in self.scenes.list_for_project(project_id) if x.id in wanted]
        if not scenes: raise ShortCandidateInvalid("Select at least one scene.")
        scenes.sort(key=lambda x:x.order); cursor=0; segments=[]; source_entities=[]
        for order,scene in enumerate(scenes):
            duration=max(1,int(scene.duration_ms)); media_start=int(scene.source_start_ms or 0); media_end=int(scene.source_end_ms) if scene.source_end_ms is not None else media_start+duration
            segments.append(ShortSegment("pending",order,media_start,media_end,scene.id,{"sceneId":scene.id,"mediaId":scene.primary_media_id,"projectTimelineStartMs":cursor}))
            source_entities.append(scene.id); cursor+=duration
        stype=ShortSourceType(source_type) if source_type in {x.value for x in ShortSourceType} else ShortSourceType.SCENES
        fingerprint=self._hash([(x.id,x.updated_at,x.duration_ms,x.primary_media_id,x.source_start_ms,x.source_end_ms,x.metadata) for x in scenes])
        candidate=ShortCandidate(project_id,stype,project_id,title.strip() or "Scene Short",0,cursor,language=language,source_project_id=project_id,
                                 source_entity_ids=source_entities,source_fingerprint=fingerprint,score_metadata={"selection":"scenes"},
                                 metadata={"targetDurationMs":target_duration_ms,"sourceSceneIds":source_entities})
        for s in segments:s.candidate_id=candidate.id
        self.repository.save_candidate(candidate,segments); return candidate

    def create_multi_range(self, project_id: str, media_id: str, ranges: list[dict[str,object]], *, title: str="Multi-range Short", language: str="en", target_duration_ms: int=30_000) -> ShortCandidate:
        asset=self.media.get_by_id(media_id)
        if asset is None or asset.project_id!=project_id or asset.type!="video": raise ShortSourceMissing()
        segments=[]; total=0
        for order,raw in enumerate(ranges):
            start=int(raw.get("startMs",0)); end=int(raw.get("endMs",0)); self._range(start,end)
            if asset.duration_ms and end>asset.duration_ms: raise ShortInvalidRange("A selected range is outside the source video.")
            seg=ShortSegment("pending",order,start,end,str(raw.get("sourceEntityId",media_id) or media_id),dict(raw.get("metadata",{}) or {})); seg.metadata.setdefault("mediaId",media_id); segments.append(seg); total+=seg.duration_ms
        if not segments: raise ShortCandidateInvalid("Add at least one source range.")
        candidate=ShortCandidate(project_id,ShortSourceType.MANUAL,media_id,title.strip() or "Multi-range Short",segments[0].source_start_ms,segments[-1].source_end_ms,
                                 language=language,source_project_id=project_id,source_entity_ids=[s.source_entity_id for s in segments],
                                 source_fingerprint=self.media_fingerprint(asset),score_metadata={"selection":"manual_multi_range"},
                                 metadata={"targetDurationMs":target_duration_ms,"assembledDurationMs":total,"rippleGapsRemoved":True})
        for s in segments:s.candidate_id=candidate.id
        self.repository.save_candidate(candidate,segments); return candidate

    def suggest_from_transcript(self, project_id: str, transcript_id: str, target_duration_ms: int, *, limit: int=6) -> list[ShortCandidate]:
        transcript=self.transcripts.get(transcript_id)
        if transcript is None or transcript.project_id!=project_id: raise ShortSourceMissing("Transcript could not be found.")
        items=self.transcripts.segments(transcript_id); output=[]; start_index=0
        # Sliding deterministic groups; no semantic quality claim.
        while start_index<len(items) and len(output)<max(1,int(limit)):
            group=[]; base=items[start_index].start_ms
            for seg in items[start_index:]:
                if group and seg.end_ms-base>target_duration_ms*1.20: break
                group.append(seg)
                if seg.end_ms-base>=target_duration_ms*.75: break
            if group:
                candidate=self.create_from_transcript(project_id,transcript_id,[x.id for x in group],title=f"Suggested {len(output)+1}",target_duration_ms=target_duration_ms)
                candidate.score_metadata={"selection":"suggested","basis":"transcript_boundaries"}; candidate.metadata["suggested"]=True; self.repository.save_candidate(candidate,self.repository.segments(candidate.id)); output.append(candidate)
                start_index += max(1,len(group))
            else: start_index+=1
        return output

    def silence_suggestions(self, transcript_id: str, *, threshold_ms: int=1200) -> list[dict[str,int]]:
        items=self.transcripts.segments(transcript_id); result=[]
        for previous,current in zip(items,items[1:]):
            gap=int(current.start_ms)-int(previous.end_ms)
            if gap>=max(250,int(threshold_ms)): result.append({"startMs":int(previous.end_ms),"endMs":int(current.start_ms),"durationMs":gap})
        return result

    def mark_outdated_if_changed(self, candidate_id: str) -> bool:
        candidate=self.repository.get_candidate(candidate_id)
        if candidate is None: raise KeyError("Short candidate not found.")
        current=candidate.source_fingerprint
        if candidate.source_type_code in {"video","manual"}:
            asset=self.media.get_by_id(candidate.source_id); current=self.media_fingerprint(asset) if asset else "missing"
        elif candidate.source_type_code=="transcript":
            transcript=self.transcripts.get(candidate.source_id)
            if transcript:
                selected_ids=set(candidate.source_entity_ids)
                selected=[x for x in self.transcripts.segments(candidate.source_id) if x.id in selected_ids]
                selected.sort(key=lambda x:(x.start_ms,x.order))
                current=self._hash({"transcript":transcript.id,"updated":getattr(transcript,"updated_at",""),"segments":[(x.id,x.start_ms,x.end_ms,x.text) for x in selected]})
            else:
                current="missing"
        changed=not current or current!=candidate.source_fingerprint
        if changed:
            candidate.status=ShortCandidateStatus.OUTDATED; candidate.metadata["sourceChanged"]=True; self.repository.save_candidate(candidate,self.repository.segments(candidate.id))
        return changed

    @staticmethod
    def _range(start_ms:int,end_ms:int) -> None:
        if int(start_ms)<0 or int(end_ms)<=int(start_ms): raise ShortInvalidRange()

    @staticmethod
    def _hash(value) -> str:
        return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(",",":")).encode("utf-8")).hexdigest()

    @classmethod
    def media_fingerprint(cls, asset) -> str:
        if asset is None:return ""
        path=Path(asset.project_path); stat=None
        try:
            s=path.stat(); stat=(s.st_size,s.st_mtime_ns)
        except OSError: stat=(0,0)
        return cls._hash((asset.id,asset.duration_ms,asset.width,asset.height,stat))

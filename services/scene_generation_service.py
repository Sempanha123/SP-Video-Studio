from __future__ import annotations

import hashlib
from dataclasses import dataclass

from domain.scene import Scene
from domain.script_section import ScriptSection
from domain.transcript_segment import TranscriptSegment
from services.script_analysis_service import ScriptAnalysisService
from storage.repositories.generated_audio_repository import GeneratedAudioRepository


def script_section_source_hash(section: ScriptSection) -> str:
    return hashlib.sha256(f"{section.section_id}\0{section.title}\0{int(section.enabled)}\0{section.content}".encode("utf-8")).hexdigest()


def transcript_segment_source_hash(segment: TranscriptSegment) -> str:
    return hashlib.sha256(f"{segment.segment_id}\0{segment.start_ms}\0{segment.end_ms}\0{segment.text}".encode("utf-8")).hexdigest()


class SceneGenerationService:
    def __init__(self, analysis: ScriptAnalysisService, audio_repository: GeneratedAudioRepository) -> None:
        self.analysis=analysis; self.audio_repository=audio_repository

    def from_script_section(self, project_id: str, section: ScriptSection, language: str, pace: str, order: int) -> Scene:
        estimate=self.analysis.analyze_text(section.content,language,pace).estimated_duration_ms
        audio_id=""; duration=max(5000,estimate)
        candidates=self.audio_repository.list_for_section(project_id,section.section_id)
        for item in candidates:
            if str(item.status)=="completed":
                audio_id=item.id; duration=max(500, int(item.duration_ms or duration)); break
        return Scene(project_id=project_id,order=order,name=section.title,duration_ms=duration,script_section_id=section.section_id,narration_audio_id=audio_id,source_hash=script_section_source_hash(section),metadata={"sourceType":"script","sourceTitle":section.title})

    def from_transcript_group(self, project_id: str, segments: list[TranscriptSegment], order: int, name: str) -> Scene:
        if not segments: raise ValueError("Transcript scene group is empty.")
        start=min(item.start_ms for item in segments); end=max(item.end_ms for item in segments)
        digest=hashlib.sha256()
        for item in segments: digest.update(transcript_segment_source_hash(item).encode("ascii"))
        return Scene(project_id=project_id,order=order,name=name,duration_ms=max(500,end-start),transcript_segment_id=segments[0].segment_id,source_hash=digest.hexdigest(),metadata={"sourceType":"transcript","sourceSegmentIds":[s.segment_id for s in segments],"sourceStartMs":start,"sourceEndMs":end})

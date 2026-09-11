from __future__ import annotations

from dataclasses import dataclass, field

from domain.dub_audio import DubAudioOutputStatus
from domain.dub_segment import DubAudioStatus, DubSegment, DubTimingStatus
from domain.dubbing_project import DubbingProject
from services.dubbing_alignment_service import DubbingAlignmentService


@dataclass(slots=True)
class DubbingReadiness:
    state: str
    blocking: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {"state": self.state, "blocking": list(self.blocking), "warnings": list(self.warnings), "summary": dict(self.summary)}


class DubbingValidationService:
    def __init__(self, alignment: DubbingAlignmentService | None = None) -> None:
        self.alignment = alignment or DubbingAlignmentService()

    def validate(self, project: DubbingProject, segments: list[DubSegment], final_output=None) -> DubbingReadiness:
        blocking: list[str] = []; warnings: list[str] = []
        if not project.source_media_id: blocking.append("Missing source video.")
        if not project.transcript_id: blocking.append("Missing transcript.")
        if not project.translation_id: blocking.append("Missing translation.")
        if not project.target_voice_id and not any(s.voice_id for s in segments): blocking.append("Choose a target voice.")
        missing = [s for s in segments if s.audio_status_code in {DubAudioStatus.PENDING.value, DubAudioStatus.FAILED.value, DubAudioStatus.CANCELLED.value}]
        outdated = [s for s in segments if s.audio_status_code == DubAudioStatus.OUTDATED.value]
        review = [s for s in segments if s.timing_status_code in {DubTimingStatus.NEEDS_REVIEW.value, DubTimingStatus.VERY_LONG.value}]
        overlaps = self.alignment.detect_overlaps(segments)
        if missing: blocking.append(f"{len(missing)} dub segment(s) are missing or failed.")
        if overlaps: blocking.append(f"{len(overlaps)} spoken overlap(s) must be reviewed.")
        if outdated: warnings.append(f"{len(outdated)} dub segment(s) are out of date.")
        if review: warnings.append(f"{len(review)} segment(s) need timing review.")
        if any(not bool(s.metadata.get("translationReviewed", False)) for s in segments):
            warnings.append("Some translated lines have not been reviewed.")
        if final_output is None or getattr(final_output, "status_code", "") != DubAudioOutputStatus.READY.value:
            blocking.append("Final dubbed audio mix is unavailable.")
        state = "Not Ready" if blocking else ("Needs Review" if warnings else "Ready")
        return DubbingReadiness(state, blocking, warnings, {
            "segments": len(segments), "readySegments": sum(s.audio_status_code == DubAudioStatus.READY.value for s in segments),
            "timingReview": len(review), "overlaps": len(overlaps), "outdated": len(outdated),
        })

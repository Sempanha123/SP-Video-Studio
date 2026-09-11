from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from storage.repositories.media_repository import MediaRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.short_repository import ShortRepository


@dataclass(frozen=True, slots=True)
class ShortIssue:
    severity: str
    code: str
    message: str


class ShortsValidationService:
    def __init__(self, repository: ShortRepository, media: MediaRepository, scenes: SceneRepository, subtitle_service=None) -> None:
        self.repository=repository; self.media=media; self.scenes=scenes; self.subtitles=subtitle_service

    def validate_candidate(self, candidate_id: str, *, target_duration_ms: int | None=None) -> list[ShortIssue]:
        candidate=self.repository.get_candidate(candidate_id)
        if candidate is None:return [ShortIssue("error","missing_candidate","Short candidate could not be found.")]
        issues=[]; segments=self.repository.segments(candidate_id)
        if not segments: issues.append(ShortIssue("error","empty_range","Set an In and Out range before creating the Short."))
        for seg in segments:
            if seg.source_end_ms<=seg.source_start_ms: issues.append(ShortIssue("error","invalid_range","Set an Out point after the In point."))
        target=int(target_duration_ms or candidate.metadata.get("targetDurationMs",0) or 0); actual=sum(s.duration_ms for s in segments) or candidate.duration_ms
        if target>0 and actual>target*1.18: issues.append(ShortIssue("warning","over_target",f"This Short is {actual/1000:.1f}s, above the {target/1000:.0f}s target."))
        elif target>0 and actual<target*.45: issues.append(ShortIssue("info","under_target",f"This Short is {actual/1000:.1f}s, below the {target/1000:.0f}s target."))
        return issues

    def readiness(self, project_id: str, candidate_id: str, *, aspect_ratio: str="9:16") -> dict[str,object]:
        issues=self.validate_candidate(candidate_id); scenes=self.scenes.list_enabled(project_id); visuals=bool(scenes)
        missing=False
        for scene in scenes:
            if scene.primary_media_id:
                asset=self.media.get_by_id(scene.primary_media_id)
                if asset is None or not Path(asset.project_path).is_file(): missing=True
        tracks=self.subtitles.list_tracks(project_id) if self.subtitles is not None else []
        if missing: issues.append(ShortIssue("error","missing_media","The source video for this Short is unavailable."))
        if not visuals: issues.append(ShortIssue("error","no_visuals","Create the editable Short sequence before export."))
        status="Not Ready" if any(i.severity=="error" for i in issues) else ("Needs Review" if any(i.severity=="warning" for i in issues) else "Ready")
        return {"status":status,"durationMs":sum(s.duration_ms for s in scenes),"aspect":aspect_ratio,"captions":"Ready" if tracks else "Optional",
                "audio":"Ready" if visuals and not missing else "Check","visuals":"Ready" if visuals and not missing else "Not Ready",
                "export":"Ready" if status=="Ready" else status,"issues":[{"severity":i.severity,"code":i.code,"message":i.message} for i in issues]}

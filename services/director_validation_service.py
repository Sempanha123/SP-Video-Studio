from __future__ import annotations

from dataclasses import dataclass

from domain.director_plan import DirectorPlan
from domain.director_profile import PLATFORM_PROFILES, WORKFLOW_PROFILES
from domain.director_scene_plan import DirectorScenePlan
from domain.project import SUPPORTED_ASPECT_RATIOS, SUPPORTED_LANGUAGES


@dataclass(frozen=True, slots=True)
class DirectorIssue:
    severity: str
    code: str
    message: str

    def to_dict(self) -> dict[str,str]: return {"severity":self.severity,"code":self.code,"message":self.message}


class DirectorValidationService:
    def __init__(self, voice_categories_provider=None, subtitle_presets_provider=None) -> None:
        self.voice_categories_provider = voice_categories_provider
        self.subtitle_presets_provider = subtitle_presets_provider

    def validate(self, plan: DirectorPlan, scenes: list[DirectorScenePlan]) -> list[DirectorIssue]:
        issues=[]
        try: plan.validate()
        except ValueError as exc: issues.append(DirectorIssue("error","invalid_plan",str(exc)))
        if plan.workflow not in WORKFLOW_PROFILES: issues.append(DirectorIssue("error","workflow","Unsupported workflow."))
        if plan.platform not in PLATFORM_PROFILES: issues.append(DirectorIssue("error","platform","Unsupported platform."))
        if plan.language not in SUPPORTED_LANGUAGES: issues.append(DirectorIssue("error","language","Unsupported language."))
        if plan.aspect_ratio not in SUPPORTED_ASPECT_RATIOS: issues.append(DirectorIssue("error","aspect_ratio","Unsupported aspect ratio."))
        if not scenes: issues.append(DirectorIssue("error","no_scenes","Plan needs at least one scene."))
        total=0
        for item in scenes:
            try:item.validate()
            except ValueError as exc:issues.append(DirectorIssue("error","scene",str(exc)))
            total+=max(0,item.target_duration_ms)
        if plan.target_duration_ms>0 and scenes:
            ratio=abs(total-plan.target_duration_ms)/plan.target_duration_ms
            if ratio>.05: issues.append(DirectorIssue("warning","duration_tolerance","Planned scene durations differ from the target by more than 5%."))
        needed={"format","script","scenes","pacing","voice","subtitles","visuals","music","transitions","hook","outro"}
        present={r.category for r in plan.recommendations}
        missing=needed-present
        if missing: issues.append(DirectorIssue("error","recommendations","Missing recommendations: "+", ".join(sorted(missing))))
        voice_rec=plan.recommendation("voice")
        if voice_rec is not None and self.voice_categories_provider is not None:
            try: categories={str(v).casefold() for v in self.voice_categories_provider()}
            except Exception: categories=set()
            if categories and str(voice_rec.value).casefold() not in categories:
                issues.append(DirectorIssue("warning","voice_category","No installed Voice Studio category exactly matches this recommendation."))
        subtitle_rec=plan.recommendation("subtitles")
        if subtitle_rec is not None and self.subtitle_presets_provider is not None:
            try: presets={str(v).casefold() for v in self.subtitle_presets_provider()}
            except Exception: presets=set()
            if presets and str(subtitle_rec.value).casefold() not in presets:
                issues.append(DirectorIssue("error","subtitle_preset","Recommended subtitle preset is unavailable."))
        return issues

    def readiness(self, plan: DirectorPlan, scenes: list[DirectorScenePlan]) -> str:
        issues=self.validate(plan,scenes)
        if any(i.severity=="error" for i in issues):return "invalid"
        if issues:return "needs_review"
        return "ready"

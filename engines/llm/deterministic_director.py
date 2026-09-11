from __future__ import annotations

from typing import Any

from domain.director_plan import DIRECTOR_RULE_ENGINE_VERSION, DirectorPlan, DirectorRequest
from domain.director_recommendation import DirectorRecommendation
from domain.director_scene_plan import DirectorScenePlan
from domain.director_profile import PLATFORM_PROFILES, WORKFLOW_PROFILES
from engines.base import EngineCapabilities
from engines.llm.base import LLMEngine
from engines.llm.types import DirectorProviderMetadata
from services.director_rule_engine import DirectorRuleEngine


class DeterministicDirectorProvider(LLMEngine):
    provider = DirectorProviderMetadata(
        "deterministic", "Local Director", False, False, True, True,
        "Planning runs locally with deterministic rules. Project content is not sent anywhere.",
    )

    def __init__(self, rules: DirectorRuleEngine | None = None) -> None:
        self.rules = rules or DirectorRuleEngine()

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities("Local Director", DIRECTOR_RULE_ENGINE_VERSION, {"structured_output","offline","multilingual"})

    def generate(self, prompt: str, **options: object) -> str:
        raise NotImplementedError("The deterministic Director produces structured plans, not chat text.")

    def generate_structured(self, task: str, input: Any, schema: object | None = None, context: dict[str, Any] | None = None) -> tuple[DirectorPlan, list[DirectorScenePlan]]:
        if task != "director_plan" or not isinstance(input, DirectorRequest):
            raise ValueError("Unsupported deterministic Director task.")
        return self.create_plan(input, context or {})

    def create_plan(self, request: DirectorRequest, context: dict[str, Any]) -> tuple[DirectorPlan, list[DirectorScenePlan]]:
        request.validate()
        aspect=self.rules.recommend_aspect_ratio(request,str(context.get("project_aspect_ratio") or "16:9"))
        script_target=self.rules.script_target(request)
        script_sections=list(context.get("script_sections") or [])
        preferred_count=len(script_sections) if request.content_source_type=="script" and script_sections else None
        dist=self.rules.scene_distribution(request,preferred_count=preferred_count)
        hook_title,hook_reason=self.rules.hook(request.workflow)
        outro_title,outro_reason=self.rules.outro(request.workflow)
        voice=self.rules.voice_category(request); subtitle=self.rules.subtitle_preset(request)
        visual=self.rules.visual_style(request,dict(context.get("media_counts") or {})); transition=self.rules.transition(request); music=self.rules.music(request)
        pace=self.rules.effective_pace(request)
        recommendations=[
            DirectorRecommendation("format","Aspect Ratio",aspect,f"{PLATFORM_PROFILES[request.platform].name} planning uses this presentation format."),
            DirectorRecommendation("script","Script Target",script_target,f"Target is estimated for {request.target_duration_ms/1000:.0f}s at {pace} pacing."),
            DirectorRecommendation("scenes","Scene Count",dist.count,f"{pace.title()} pacing uses shorter or longer visual beats instead of one fixed scene length."),
            DirectorRecommendation("pacing","Visual Pace",pace,f"{PLATFORM_PROFILES[request.platform].name} and the selected workflow favor this visual rhythm."),
            DirectorRecommendation("voice","Voice Style",voice,f"{WORKFLOW_PROFILES[request.workflow].name} projects benefit from this voice category."),
            DirectorRecommendation("subtitles","Subtitle Preset",subtitle,"The subtitle preset is chosen from the existing Subtitle Studio registry for the workflow/platform."),
            DirectorRecommendation("visuals","Visual Style",visual,"This visual approach matches the workflow and available project media without generating new assets."),
            DirectorRecommendation("music","Music",music,"Music stays secondary to narration and content clarity."),
            DirectorRecommendation("transitions","Transition",transition,"Use restrained transitions appropriate to the selected workflow."),
            DirectorRecommendation("hook",hook_title,hook_title,hook_reason),
            DirectorRecommendation("outro",outro_title,outro_title,outro_reason),
        ]
        notices=[]
        if request.workflow=="news" and request.content_source_type=="idea":
            notices.append("AI Director can plan the video structure, but News Studio will require sources before generating factual content.")
        if context.get("script_estimated_duration_ms",0) and int(context["script_estimated_duration_ms"]) > request.target_duration_ms*1.10:
            current=int(context["script_estimated_duration_ms"]); reduction=max(0,round((1-request.target_duration_ms/current)*100))
            notices.append(f"Existing script is estimated at {current/1000:.0f}s versus the {request.target_duration_ms/1000:.0f}s target. Consider reducing narration by about {reduction}%.")
        if request.content_source_type=="scenes" and context.get("scene_count"):
            notices.append(f"Existing project has {int(context['scene_count'])} scenes totaling {int(context.get('scene_duration_ms',0))/1000:.0f}s; this plan recommends {dist.count} scenes for the target.")
        plan=DirectorPlan(project_id=request.project_id,request_id=request.id,workflow=request.workflow,platform=request.platform,language=request.language,target_duration_ms=request.target_duration_ms,aspect_ratio=aspect,source_type=request.content_source_type,source_id=request.content_source_id,status="review",source_fingerprint=str(context.get("source_fingerprint") or ""),recommendations=recommendations,metadata={"provider":self.provider.provider_id,"providerName":self.provider.name,"offline":True,"privacy":self.provider.privacy_description,"audience":request.audience,"style":request.style,"pace":pace,"tone":request.tone,"idea":request.content_text,"notices":notices,"sourceSummary":dict(context.get("source_summary") or {})})
        scene_plans=[]
        generic_titles=self.rules.scene_titles(request.workflow,dist.count)
        for i,duration in enumerate(dist.durations_ms):
            section=script_sections[i] if i<len(script_sections) else None
            title=str(section.get("title")) if section else generic_titles[i][0]
            purpose=generic_titles[i][1]
            script_section_id=str(section.get("id") or "") if section else ""
            scene_plans.append(DirectorScenePlan(plan.id,i,title,purpose,duration,script_section_id=script_section_id,visual_type=visual,visual_description="Use relevant project media or a supporting visual that matches this scene's purpose.",overlay_recommendation="Key phrase" if request.workflow in {"news","shorts"} else "",voice_style=voice,subtitle_style=subtitle,transition=transition,metadata={"ruleEngineVersion":DIRECTOR_RULE_ENGINE_VERSION}))
        return plan,scene_plans

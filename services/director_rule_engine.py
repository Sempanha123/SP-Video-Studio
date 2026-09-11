from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from domain.director_plan import DirectorRequest
from domain.director_profile import PLATFORM_PROFILES, WORKFLOW_PROFILES
from services.script_analysis_service import KHMER_CHARS_PER_MINUTE, PACE_WPM


@dataclass(frozen=True, slots=True)
class SceneDistribution:
    count: int
    durations_ms: tuple[int, ...]


class DirectorRuleEngine:
    version = "1.0"

    def recommend_aspect_ratio(self, request: DirectorRequest, project_aspect_ratio: str = "16:9") -> str:
        if request.aspect_ratio_mode != "auto":
            return request.aspect_ratio_mode
        profile = PLATFORM_PROFILES[request.platform]
        return project_aspect_ratio if request.platform == "generic" else profile.aspect_ratio

    def effective_pace(self, request: DirectorRequest) -> str:
        if request.pace in {"slow", "fast"}:
            return request.pace
        if request.workflow == "shorts" or request.platform in {"tiktok", "youtube_shorts", "instagram_reels"}:
            return "fast"
        if request.workflow == "story" and request.platform == "youtube":
            return "slow"
        return "balanced"

    def script_target(self, request: DirectorRequest) -> dict[str, int | str]:
        pace = self.effective_pace(request)
        seconds = request.target_duration_ms / 1000
        script_pace = {"slow": "slow", "balanced": "normal", "fast": "fast"}[pace]
        if request.language == "km":
            rate = KHMER_CHARS_PER_MINUTE[script_pace]
            return {"metric": "characters", "value": max(1, round(rate * seconds / 60)), "pace": pace}
        rate = PACE_WPM[script_pace]
        return {"metric": "words", "value": max(1, round(rate * seconds / 60)), "pace": pace}

    def scene_distribution(self, request: DirectorRequest, *, preferred_count: int | None = None) -> SceneDistribution:
        pace = self.effective_pace(request)
        base_ms = {"fast": 3800, "balanced": 6000, "slow": 8500}[pace]
        factor = {"news": .9, "story": 1.12, "translate": 1.0, "video": 1.0, "shorts": .82}[request.workflow]
        avg = max(1500, int(base_ms * factor))
        count = preferred_count or max(2, min(60, round(request.target_duration_ms / avg)))
        count = max(1, int(count))
        if count == 1:
            return SceneDistribution(1, (request.target_duration_ms,))
        weights = [0.68] + [1.0] * max(0, count - 2) + [0.78]
        total_weight = sum(weights)
        raw = [max(700, round(request.target_duration_ms * w / total_weight)) for w in weights]
        delta = request.target_duration_ms - sum(raw)
        raw[-1] = max(500, raw[-1] + delta)
        if sum(raw) != request.target_duration_ms:
            raw[-1] += request.target_duration_ms - sum(raw)
        return SceneDistribution(count, tuple(raw))

    def hook(self, workflow: str) -> tuple[str, str]:
        mapping = {
            "news": ("Direct Summary", "Open with a one-sentence summary of the most important provided point."),
            "story": ("Story Hook", "Open with a short moment or question that creates curiosity without revealing the resolution."),
            "translate": ("Direct Context", "Open with concise source context so the translated presentation is immediately understandable."),
            "video": ("Direct Statement", "Open with the core promise or topic in one clear sentence."),
            "shorts": ("Visual Hook", "Use the first 1–3 seconds for a direct visual or concise statement that establishes the topic."),
        }
        return mapping[workflow]

    def outro(self, workflow: str) -> tuple[str, str]:
        mapping = {
            "news": ("Closing Summary", "End with a brief recap; do not force a call to action."),
            "story": ("Resolution", "Close the narrative by resolving the main development and leaving one clear final beat."),
            "translate": ("Source-faithful Close", "Close naturally without adding claims that are not present in the source."),
            "video": ("Next Step", "End with a concise next step or summary appropriate to the content."),
            "shorts": ("Short CTA", "Use a brief closing action or question only if it fits the content."),
        }
        return mapping[workflow]

    def visual_style(self, request: DirectorRequest, media_counts: dict[str, int] | None = None) -> str:
        media_counts = media_counts or {}
        if media_counts.get("video", 0) and media_counts.get("image", 0):
            return "mixed_media"
        if request.workflow == "news": return "news_graphics"
        if request.workflow == "story": return "documentary"
        if request.workflow == "shorts": return "text_led"
        return WORKFLOW_PROFILES[request.workflow].visual_style

    def subtitle_preset(self, request: DirectorRequest) -> str:
        workflow = WORKFLOW_PROFILES[request.workflow]
        if request.subtitle_preference:
            return request.subtitle_preference
        if request.workflow == "shorts": return "creator"
        if request.workflow == "news": return "news"
        if request.workflow == "story": return "documentary"
        return workflow.subtitle_presets[0]

    def voice_category(self, request: DirectorRequest) -> str:
        if request.voice_preference:
            return request.voice_preference
        return WORKFLOW_PROFILES[request.workflow].default_voice_category

    def transition(self, request: DirectorRequest) -> str:
        if request.workflow == "story": return "fade"
        if request.workflow == "news": return "cut"
        if request.workflow == "shorts": return "cut"
        return WORKFLOW_PROFILES[request.workflow].transition

    def music(self, request: DirectorRequest) -> dict[str, str]:
        style = {"news":"neutral","story":"cinematic","translate":"neutral","video":"uplifting","shorts":"technology"}[request.workflow]
        return {"level": WORKFLOW_PROFILES[request.workflow].music_level, "style": style}

    @staticmethod
    def scene_titles(workflow: str, count: int) -> list[tuple[str, str]]:
        if count <= 0: return []
        if workflow == "story":
            stages=[("Hook","Create curiosity"),("Setup","Establish the situation"),("Development","Develop the central idea"),("Peak","Present the strongest moment"),("Resolution","Resolve the story")]
        elif workflow == "news":
            stages=[("Hook","Lead with the key provided point"),("Context","Establish context"),("Main Update","Present the central update"),("Details","Add supporting details"),("Closing Summary","Recap without adding facts")]
        elif workflow == "translate":
            stages=[("Opening","Introduce source context"),("Main Segment","Present translated content"),("Supporting Segment","Continue source-aligned content"),("Closing","Close without adding source claims")]
        elif workflow == "shorts":
            stages=[("Hook","Capture attention in the first seconds"),("Core Beat","Deliver one concise point"),("Support","Reinforce the point visually"),("Close","Finish with a concise action or question")]
        else:
            stages=[("Opening","Introduce the topic"),("Main Point","Develop the core idea"),("Support","Add supporting context"),("Close","Finish clearly")]
        result=[]
        for i in range(count):
            if i==0: title,purpose=stages[0]
            elif i==count-1: title,purpose=stages[-1]
            else:
                base=stages[min(i,len(stages)-2)]
                title,purpose=base
                if count > len(stages) and i>=len(stages)-1: title=f"{base[0]} {i}" 
            result.append((title,purpose))
        return result

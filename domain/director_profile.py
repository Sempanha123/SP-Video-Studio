from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformProfile:
    code: str
    name: str
    aspect_ratio: str
    pace: str
    subtitle_prominence: str
    hook_importance: str


@dataclass(frozen=True, slots=True)
class WorkflowProfile:
    code: str
    name: str
    default_voice_category: str
    subtitle_presets: tuple[str, ...]
    transition: str
    visual_style: str
    music_level: str


PLATFORM_PROFILES: dict[str, PlatformProfile] = {
    "tiktok": PlatformProfile("tiktok", "TikTok", "9:16", "fast", "high", "high"),
    "youtube_shorts": PlatformProfile("youtube_shorts", "YouTube Shorts", "9:16", "fast", "high", "high"),
    "instagram_reels": PlatformProfile("instagram_reels", "Instagram Reels", "9:16", "fast", "high", "high"),
    "youtube": PlatformProfile("youtube", "YouTube", "16:9", "balanced", "medium", "medium"),
    "facebook": PlatformProfile("facebook", "Facebook", "16:9", "balanced", "medium", "medium"),
    "generic": PlatformProfile("generic", "Generic", "16:9", "balanced", "medium", "medium"),
}

WORKFLOW_PROFILES: dict[str, WorkflowProfile] = {
    "news": WorkflowProfile("news", "News", "News Anchor", ("news", "clean"), "cut", "news_graphics", "very_low"),
    "story": WorkflowProfile("story", "Story", "Storyteller", ("documentary", "clean"), "fade", "mixed_media", "low"),
    "translate": WorkflowProfile("translate", "Translate", "Professional", ("clean", "documentary"), "cut", "mixed_media", "very_low"),
    "video": WorkflowProfile("video", "Video", "Professional", ("clean", "minimal"), "cut", "mixed_media", "low"),
    "shorts": WorkflowProfile("shorts", "Shorts", "Energetic", ("creator", "bold"), "cut", "text_led", "low"),
}

SUPPORTED_AUDIENCES = {"general", "beginners", "technical", "professional", "young_adult", "business"}
SUPPORTED_STYLES = {"modern", "clean", "professional", "news", "documentary", "storytelling", "energetic", "minimal", "educational", "creator"}
SUPPORTED_PACES = {"slow", "balanced", "fast"}
SUPPORTED_TONES = {"neutral", "confident", "friendly", "energetic", "calm", "serious", "inspirational"}
DURATION_PRESETS_MS = (15_000, 30_000, 45_000, 60_000, 90_000, 120_000, 180_000, 300_000)

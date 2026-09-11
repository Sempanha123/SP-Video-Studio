from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ShortStyleName(StrEnum):
    CLEAN = "clean"
    CREATOR = "creator"
    NEWS = "news"
    DOCUMENTARY = "documentary"
    MINIMAL = "minimal"


@dataclass(frozen=True, slots=True)
class ShortStyle:
    name: str
    caption_preset: str
    transition: str = "cut"
    hook_overlay_type: str = "headline"


SHORT_STYLES: dict[str, ShortStyle] = {
    "clean": ShortStyle("clean", "clean", "cut"),
    "creator": ShortStyle("creator", "creator", "cut"),
    "news": ShortStyle("news", "bold", "quick_fade"),
    "documentary": ShortStyle("documentary", "clean", "quick_fade"),
    "minimal": ShortStyle("minimal", "clean", "cut"),
}


def short_style(name: str) -> ShortStyle:
    return SHORT_STYLES.get(str(name or "clean").lower(), SHORT_STYLES["clean"])

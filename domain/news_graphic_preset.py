from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True, slots=True)
class NewsGraphicPreset:
    preset_id: str
    name: str
    graphic_type: str
    variant: str
    layout_id: str
    version: int = 1
    description: str = ""
    metadata: dict[str,Any] = field(default_factory=dict)
    def to_dict(self)->dict[str,Any]: return {"id":self.preset_id,"name":self.name,"type":self.graphic_type,"variant":self.variant,"layoutId":self.layout_id,"version":self.version,"description":self.description,"metadata":dict(self.metadata)}

BUILTIN_GRAPHIC_PRESETS=(
    NewsGraphicPreset("headline_full","Headline • Full Screen","headline","full_screen","headline_focus"),
    NewsGraphicPreset("headline_lower","Headline • Lower","headline","lower_headline","media_headline"),
    NewsGraphicPreset("breaking_clean","Breaking News","breaking","restrained","headline_focus"),
    NewsGraphicPreset("fact_focus","Fact Card","fact","card","fact_focus"),
    NewsGraphicPreset("number_large","Large Number","number","large_number","number_focus"),
    NewsGraphicPreset("quote_full","Quote • Full Screen","quote","full_screen","quote_focus"),
    NewsGraphicPreset("source_compact","Source • Compact","source","compact","source_focus"),
    NewsGraphicPreset("lower_simple","Lower Third • Simple","lower_third","simple_line","media_lower_third"),
    NewsGraphicPreset("topic_compact","Topic Label","topic","compact","full_media"),
    NewsGraphicPreset("intro_clean","Intro","intro","clean","intro"),
    NewsGraphicPreset("outro_clean","Outro","outro","clean","outro"),
)
GRAPHIC_PRESET_BY_ID={x.preset_id:x for x in BUILTIN_GRAPHIC_PRESETS}

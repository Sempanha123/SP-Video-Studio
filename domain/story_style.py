from __future__ import annotations
from dataclasses import dataclass

STORY_SCRIPT_STYLES=("narrative","conversational","cinematic","educational","documentary","minimal")
MUSIC_DIRECTIONS=("calm","cinematic","uplifting","tense","none")

@dataclass(frozen=True,slots=True)
class StoryStyle:
    script_style:str="narrative"
    music_direction:str="none"
    visual_pacing:str="balanced"

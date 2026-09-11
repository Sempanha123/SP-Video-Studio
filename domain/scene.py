from dataclasses import dataclass, field


@dataclass(slots=True)
class Scene:
    scene_id: str
    index: int
    start_time: float = 0.0
    duration: float = 0.0
    narration: str = ""
    media: list[str] = field(default_factory=list)
    overlays: list[dict[str, object]] = field(default_factory=list)
    transition: str = "cut"
    subtitle_settings: dict[str, object] = field(default_factory=dict)
    audio_settings: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

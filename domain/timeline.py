from dataclasses import dataclass, field


@dataclass(slots=True)
class Timeline:
    duration: float = 0.0
    tracks: dict[str, list[object]] = field(default_factory=dict)

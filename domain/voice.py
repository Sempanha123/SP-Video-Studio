from dataclasses import dataclass, field


@dataclass(slots=True)
class VoiceProfile:
    voice_id: str
    name: str
    language: str
    engine: str
    style: str = "Conversational"
    capabilities: set[str] = field(default_factory=set)

from __future__ import annotations

import json
from pathlib import Path

from domain.voice_profile import VoiceProfile


VOICE_REGISTRY_VERSION = 1


class VoiceRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or (Path(__file__).resolve().parents[1] / "resources" / "voices" / "builtin_voices.json")
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self.version = int(payload.get("voice_registry_version", 0))
        if self.version != VOICE_REGISTRY_VERSION:
            raise ValueError("Unsupported built-in voice registry version.")
        self._voices: dict[str, VoiceProfile] = {}
        for item in payload.get("voices", []):
            voice = VoiceProfile(
                voice_id=str(item["id"]),
                name=str(item["name"]),
                voice_type=str(item.get("voice_type", "preset")),
                language=str(item["language"]),
                category=str(item["category"]),
                engine_id=str(item.get("engine_id", "voxcpm2")),
                voice_description=str(item.get("voice_description", "")),
                style_tags=[str(value) for value in item.get("style_tags", [])],
                description=str(item.get("description", "")),
                settings=dict(item.get("default_settings", {})),
                is_builtin=True,
                validated=True,
            )
            voice.validate()
            if voice.voice_id in self._voices:
                raise ValueError(f"Duplicate built-in voice ID: {voice.voice_id}")
            self._voices[voice.voice_id] = voice

    def list_all(self) -> list[VoiceProfile]:
        return list(self._voices.values())

    def get(self, voice_id: str) -> VoiceProfile | None:
        return self._voices.get(voice_id)

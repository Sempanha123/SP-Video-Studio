from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from domain.shortcut_context import ShortcutContext


class CommandCategory(StrEnum):
    GENERAL = "General"
    PROJECT = "Project"
    PLAYBACK = "Playback"
    TIMELINE = "Timeline"
    EDITING = "Editing"
    MEDIA = "Media"
    SPEECH_TTS = "Speech & TTS"
    SUBTITLES = "Subtitles"
    AUDIO = "Audio"
    VIEW = "View"
    NAVIGATION = "Navigation"
    EXPORT = "Export"


@dataclass(slots=True)
class Command:
    id: str
    name: str
    description: str
    category: CommandCategory
    default_shortcut: str = ""
    current_shortcut: str = ""
    context: ShortcutContext = ShortcutContext.GLOBAL
    enabled: bool = True
    checkable: bool = False
    dangerous: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = self.id.strip()
        if not self.id:
            raise ValueError("Command id is required.")
        if not self.current_shortcut:
            self.current_shortcut = self.default_shortcut

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "defaultShortcut": self.default_shortcut,
            "shortcut": self.current_shortcut,
            "context": self.context.value,
            "enabled": self.enabled,
            "checkable": self.checkable,
            "dangerous": self.dangerous,
            "metadata": dict(self.metadata),
        }

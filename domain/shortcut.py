from __future__ import annotations

from dataclasses import dataclass

from domain.shortcut_context import ShortcutContext


PROTECTED_TEXT_SEQUENCES = {
    "Space",
    "Delete",
    "Backspace",
    "Enter",
    "Return",
    "Left",
    "Right",
    "Up",
    "Down",
    "Home",
    "End",
    "Ctrl+A",
    "Ctrl+C",
    "Ctrl+V",
    "Ctrl+X",
    "Ctrl+Z",
    "Ctrl+Y",
    "Ctrl+Shift+Z",
    "Ctrl+B",
    "Ctrl+D",
    "Ctrl+F",
    "Ctrl+Enter",
    "Alt+Left",
    "Alt+Right",
    "Alt+Up",
    "Alt+Down",
    "I",
    "O",
    "X",
    "M",
    "S",
    "Q",
    "W",
    "+",
    "-",
}

RESERVED_EDITING_SEQUENCES = {
    "Ctrl+A", "Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+Z", "Ctrl+Y", "Ctrl+Shift+Z"
}


@dataclass(frozen=True, slots=True)
class ShortcutBinding:
    command_id: str
    sequence: str
    context: ShortcutContext
    enabled: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "commandId": self.command_id,
            "sequence": self.sequence,
            "context": self.context.value,
            "enabled": self.enabled,
        }

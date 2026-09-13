from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from domain.command import Command
from domain.shortcut import RESERVED_EDITING_SEQUENCES
from domain.shortcut_context import contexts_overlap


@dataclass(slots=True, frozen=True)
class ShortcutConflict:
    command_id: str
    command_name: str
    sequence: str
    reason: str = "overlapping-context"


class ShortcutConflictService:
    def conflicts(
        self,
        sequence: str,
        command_id: str,
        commands: Iterable[Command],
    ) -> list[ShortcutConflict]:
        target = next((item for item in commands if item.id == command_id), None)
        if target is None or not sequence:
            return []
        found: list[ShortcutConflict] = []
        for item in commands:
            if item.id == command_id or not item.current_shortcut:
                continue
            if item.current_shortcut == sequence and contexts_overlap(target.context, item.context):
                found.append(
                    ShortcutConflict(item.id, item.name, sequence)
                )
        return found

    @staticmethod
    def reserved_warning(sequence: str, command_id: str) -> str:
        if sequence not in RESERVED_EDITING_SEQUENCES:
            return ""
        safe_prefixes = ("edit.", "timeline.", "speech.", "subtitle.")
        if command_id.startswith(safe_prefixes):
            return ""
        return f"{sequence} is a protected editing shortcut. Reassign it only if you are sure."

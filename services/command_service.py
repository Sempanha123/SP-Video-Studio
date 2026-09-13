from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from domain.command import Command
from domain.shortcut_context import ShortcutContext, context_priority


class CommandService:
    def __init__(self, commands: Iterable[Command] = ()) -> None:
        self._commands: dict[str, Command] = {}
        self._recent: deque[str] = deque(maxlen=12)
        for command in commands:
            self.register(command)

    def register(self, command: Command) -> None:
        if command.id in self._commands:
            raise ValueError(f"Command already registered: {command.id}")
        self._commands[command.id] = command

    def get(self, command_id: str) -> Command | None:
        return self._commands.get(command_id)

    def all(self) -> list[Command]:
        return list(self._commands.values())

    def enabled_for_context(self, context: str | ShortcutContext) -> list[Command]:
        priorities = set(context_priority(context))
        return [
            command
            for command in self._commands.values()
            if command.enabled and command.context in priorities
        ]

    def can_execute(
        self,
        command_id: str,
        context: str | ShortcutContext,
        *,
        project_open: bool = True,
    ) -> bool:
        command = self.get(command_id)
        if command is None or not command.enabled:
            return False
        if command.metadata.get("requiresProject", False) and not project_open:
            return False
        return command.context in set(context_priority(context))

    def mark_executed(self, command_id: str) -> None:
        if command_id in self._commands:
            try:
                self._recent.remove(command_id)
            except ValueError:
                pass
            self._recent.appendleft(command_id)

    def recent(self, context: str | ShortcutContext, project_open: bool = True) -> list[Command]:
        return [
            self._commands[item]
            for item in self._recent
            if self.can_execute(item, context, project_open=project_open)
        ]

    def search(
        self,
        query: str,
        context: str | ShortcutContext,
        *,
        project_open: bool = True,
        limit: int = 50,
        include_disabled: bool = False,
    ) -> list[Command]:
        needle = (query or "").strip().casefold()
        candidates = list(self._commands.values())
        if not include_disabled:
            candidates = [
                item for item in candidates
                if self.can_execute(item.id, context, project_open=project_open)
            ]
        if not needle:
            recent = self.recent(context, project_open)
            seen = {item.id for item in recent}
            ordered = recent + sorted(
                (item for item in candidates if item.id not in seen),
                key=lambda item: (item.category.value, item.name.casefold()),
            )
            return ordered[:limit]

        ranked: list[tuple[int, str, Command]] = []
        for command in candidates:
            hay = " ".join(
                (
                    command.name,
                    command.description,
                    command.category.value,
                    command.id.replace(".", " "),
                )
            ).casefold()
            score = _fuzzy_score(needle, hay)
            if score is not None:
                ranked.append((score, command.name.casefold(), command))
        ranked.sort(key=lambda row: (row[0], row[1]))
        return [row[2] for row in ranked[:limit]]


def _fuzzy_score(needle: str, haystack: str) -> int | None:
    if needle == haystack:
        return 0
    pos = haystack.find(needle)
    if pos >= 0:
        return 1 + pos
    tokens = needle.split()
    if tokens and all(token in haystack for token in tokens):
        return 30 + sum(haystack.find(token) for token in tokens)
    # Cheap subsequence search keeps a 1000-command registry responsive.
    index = 0
    gap = 0
    for char in needle:
        found = haystack.find(char, index)
        if found < 0:
            return None
        gap += found - index
        index = found + 1
    return 100 + gap

from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from services.command_service import CommandService
from services.shortcut_conflict_service import ShortcutConflictService
from services.shortcut_service import ShortcutService, normalize_sequence


class ShortcutController(QObject):
    changed = Signal()
    conflictDetected = Signal(str, str, str)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(
        self,
        commands: CommandService,
        shortcuts: ShortcutService,
        conflicts: ShortcutConflictService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.commands = commands
        self.shortcuts = shortcuts
        self.conflicts = conflicts
        self._pending_command = ""
        self._pending_sequence = ""

    @Property("QVariantList", notify=changed)
    def rows(self) -> list[dict[str, object]]:
        return [item.to_dict() for item in self.commands.all()]

    @Slot(str, result="QVariantList")
    def search(self, text: str) -> list[dict[str, object]]:
        needle = (text or "").strip().casefold()
        rows = self.commands.all()
        if needle:
            rows = [
                item for item in rows
                if needle in item.name.casefold()
                or needle in item.category.value.casefold()
                or needle in item.id.casefold()
                or needle in str(item.current_shortcut or "").casefold()
            ]
        return [item.to_dict() for item in rows]

    @Slot(str, str, result=bool)
    def setShortcut(self, command_id: str, sequence: str) -> bool:
        try:
            normalized = normalize_sequence(sequence)
            warning = self.conflicts.reserved_warning(normalized, command_id)
            if warning:
                self._pending_command = command_id
                self._pending_sequence = normalized
                self.conflictDetected.emit(command_id, normalized, warning)
                return False
            conflicts = self.shortcuts.assign(command_id, normalized, replace=False)
            if conflicts:
                first = conflicts[0]
                self._pending_command = command_id
                self._pending_sequence = normalized
                self.conflictDetected.emit(
                    command_id,
                    normalized,
                    f"{normalized} is already used by {first.command_name}.",
                )
                return False
            self.changed.emit()
            self.operationSucceeded.emit("Keyboard shortcut updated.")
            return True
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "Shortcut could not be updated.")
            return False

    @Slot(result=bool)
    def replaceConflict(self) -> bool:
        if not self._pending_command:
            return False
        try:
            self.shortcuts.assign(
                self._pending_command, self._pending_sequence, replace=True
            )
            self._pending_command = ""
            self._pending_sequence = ""
            self.changed.emit()
            self.operationSucceeded.emit("Shortcut replaced.")
            return True
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "Shortcut could not be replaced.")
            return False

    @Slot()
    def cancelConflict(self) -> None:
        self._pending_command = ""
        self._pending_sequence = ""

    @Slot(str)
    def resetCommand(self, command_id: str) -> None:
        try:
            self.shortcuts.reset(command_id)
            self.changed.emit()
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "Shortcut could not be reset.")

    @Slot()
    def resetAll(self) -> None:
        try:
            self.shortcuts.reset_all()
            self.changed.emit()
            self.operationSucceeded.emit("Keyboard shortcuts reset to defaults.")
        except Exception as exc:
            self.operationFailed.emit(str(exc) or "Shortcuts could not be reset.")

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from domain.shortcut_context import ShortcutContext
from services.command_service import CommandService
from services.shortcut_service import ShortcutService, normalize_sequence


class CommandController(QObject):
    stateChanged = Signal()
    registryChanged = Signal()
    commandTriggered = Signal(str)
    commandRejected = Signal(str)
    paletteRequested = Signal()
    shortcutsRequested = Signal()
    operationFailed = Signal(str)

    def __init__(
        self,
        commands: CommandService,
        shortcuts: ShortcutService,
        logger: logging.Logger | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.commands = commands
        self.shortcuts = shortcuts
        self.logger = logger or logging.getLogger("sp_video_studio.commands")
        self._context = ShortcutContext.GLOBAL
        self._text_editing = False
        self._modal_open = False
        self._project_open = False
        self._window_active = True

    @Property(str, notify=stateChanged)
    def context(self) -> str:
        return self._context.value

    @Property(bool, notify=stateChanged)
    def textEditing(self) -> bool:
        return self._text_editing

    @Property(bool, notify=stateChanged)
    def modalOpen(self) -> bool:
        return self._modal_open

    @Property(bool, notify=stateChanged)
    def projectOpen(self) -> bool:
        return self._project_open

    @Property("QVariantList", notify=stateChanged)
    def activeBindings(self) -> list[dict[str, object]]:
        if not self._window_active:
            return []
        return [
            binding.to_dict()
            for binding in self.shortcuts.bindings(
                self._context,
                text_editing=self._text_editing,
                modal_open=self._modal_open,
                project_open=self._project_open,
            )
        ]

    @Property("QVariantList", notify=registryChanged)
    def registry(self) -> list[dict[str, object]]:
        return [item.to_dict() for item in self.commands.all()]

    @Slot(str)
    def setContext(self, value: str) -> None:
        try:
            current = ShortcutContext(value)
        except ValueError:
            current = ShortcutContext.GLOBAL
        if current != self._context:
            self._context = current
            self.stateChanged.emit()

    @Slot(bool)
    def setTextEditing(self, value: bool) -> None:
        value = bool(value)
        if value != self._text_editing:
            self._text_editing = value
            self.stateChanged.emit()

    @Slot(bool)
    def setModalOpen(self, value: bool) -> None:
        value = bool(value)
        if value != self._modal_open:
            self._modal_open = value
            self.stateChanged.emit()

    @Slot(bool)
    def setProjectOpen(self, value: bool) -> None:
        value = bool(value)
        if value != self._project_open:
            self._project_open = value
            self.stateChanged.emit()

    @Slot(bool)
    def setWindowActive(self, value: bool) -> None:
        value = bool(value)
        if value != self._window_active:
            self._window_active = value
            self.stateChanged.emit()

    @Slot(str, result=bool)
    def dispatch(self, sequence: str) -> bool:
        if not self._window_active:
            return False
        command = self.shortcuts.command_for_sequence(
            normalize_sequence(sequence),
            self._context,
            text_editing=self._text_editing,
            modal_open=self._modal_open,
            project_open=self._project_open,
        )
        if command is None:
            return False
        return self.trigger(command.id)

    @Slot(str, result=bool)
    def trigger(self, command_id: str) -> bool:
        if command_id == "app.command_palette":
            self.paletteRequested.emit()
            self.commands.mark_executed(command_id)
            return True
        if command_id == "app.shortcuts":
            self.shortcutsRequested.emit()
            self.commands.mark_executed(command_id)
            return True
        if not self.commands.can_execute(
            command_id, self._context, project_open=self._project_open
        ):
            self.commandRejected.emit(command_id)
            return False
        try:
            self.commands.mark_executed(command_id)
            self.commandTriggered.emit(command_id)
            return True
        except Exception as exc:
            self.logger.exception("Command execution failed: %s", command_id)
            self.operationFailed.emit(str(exc) or "That command could not be completed.")
            return False

    @Slot(str, result="QVariantList")
    def search(self, query: str) -> list[dict[str, object]]:
        return [
            item.to_dict()
            for item in self.commands.search(
                query,
                self._context,
                project_open=self._project_open,
                limit=60,
            )
        ]

    @Slot(str, result=str)
    def shortcutFor(self, command_id: str) -> str:
        command = self.commands.get(command_id)
        return command.current_shortcut if command is not None else ""

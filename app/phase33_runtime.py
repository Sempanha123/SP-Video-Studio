from __future__ import annotations

"""Phase 33 command/shortcut runtime layered on the Phase 32 runtime."""

import app.manual_speech_runtime as p32
import app.phase31_runtime as p31
from services.command_service import CommandService
from services.settings_service import SettingsService
from services.shortcut_conflict_service import ShortcutConflictService
from services.shortcut_service import ShortcutService, default_commands
from ui.controllers.command_controller import CommandController
from ui.controllers.shortcut_controller import ShortcutController
from ui.controllers.productivity_speech_controller import ProductivitySpeechController


def _install_productivity(container):
    logger = container.resolve("logger")
    settings = container.resolve(SettingsService)
    commands = CommandService(default_commands())
    conflicts = ShortcutConflictService()
    shortcuts = ShortcutService(commands, settings, conflicts, logger)
    for cls, value in (
        (CommandService, commands),
        (ShortcutConflictService, conflicts),
        (ShortcutService, shortcuts),
    ):
        try:
            container.register_instance(cls, value)
        except Exception:
            pass
    return commands, shortcuts, conflicts, logger


def run() -> int:
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return p32.run()

    original_install = p31._install
    original_speech_controller = p32.ManualSpeechController
    p32.ManualSpeechController = ProductivitySpeechController
    registered = {"done": False}

    def install(container):
        result = original_install(container)
        commands, shortcuts, conflicts, logger = _install_productivity(container)
        if not registered["done"]:
            class RuntimeCommandController(CommandController):
                def __init__(self, parent=None):
                    super().__init__(commands, shortcuts, logger=logger, parent=parent)

            class RuntimeShortcutController(ShortcutController):
                def __init__(self, parent=None):
                    super().__init__(commands, shortcuts, conflicts, parent=parent)

            qmlRegisterSingletonType(
                RuntimeCommandController,
                "SPVideoStudio.Commands",
                1,
                0,
                "Commands",
            )
            qmlRegisterSingletonType(
                RuntimeShortcutController,
                "SPVideoStudio.Commands",
                1,
                0,
                "Shortcuts",
            )
            registered["done"] = True
        return result

    p31._install = install
    try:
        return p32.run()
    finally:
        p31._install = original_install
        p32.ManualSpeechController = original_speech_controller

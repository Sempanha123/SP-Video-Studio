from __future__ import annotations
from abc import ABC, abstractmethod

class BaseCommand(ABC):
    label: str = "Edit"
    merge_key: str = ""
    @abstractmethod
    def execute(self) -> None: ...
    @abstractmethod
    def undo(self) -> None: ...
    def redo(self) -> None: self.execute()
    def merge_with(self, other: "BaseCommand") -> bool: return False

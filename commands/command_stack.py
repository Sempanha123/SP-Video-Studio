from __future__ import annotations
from commands.base_command import BaseCommand

class CommandStack:
    def __init__(self, limit: int = 150) -> None:
        self.limit=max(1,int(limit)); self._undo:list[BaseCommand]=[]; self._redo:list[BaseCommand]=[]
    @property
    def can_undo(self)->bool: return bool(self._undo)
    @property
    def can_redo(self)->bool: return bool(self._redo)
    @property
    def undo_label(self)->str: return self._undo[-1].label if self._undo else ""
    @property
    def redo_label(self)->str: return self._redo[-1].label if self._redo else ""
    def execute(self, command:BaseCommand)->None:
        command.execute(); self.push_executed(command)
    def push_executed(self, command:BaseCommand)->None:
        if self._undo and command.merge_key and self._undo[-1].merge_key==command.merge_key and self._undo[-1].merge_with(command):
            self._redo.clear(); return
        self._undo.append(command); self._redo.clear()
        if len(self._undo)>self.limit: del self._undo[:len(self._undo)-self.limit]
    def undo(self)->bool:
        if not self._undo: return False
        command=self._undo.pop(); command.undo(); self._redo.append(command); return True
    def redo(self)->bool:
        if not self._redo: return False
        command=self._redo.pop(); command.redo(); self._undo.append(command); return True
    def clear(self)->None: self._undo.clear(); self._redo.clear()

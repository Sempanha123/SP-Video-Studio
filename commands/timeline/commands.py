from __future__ import annotations
from collections.abc import Callable
from commands.base_command import BaseCommand

class TimelineCommand(BaseCommand):
    def __init__(self,label:str,do:Callable[[],None],undo:Callable[[],None],*,redo:Callable[[],None]|None=None,merge_key:str="") -> None:
        self.label=label; self._do=do; self._undo_fn=undo; self._redo_fn=redo or do; self.merge_key=merge_key
    def execute(self)->None: self._do()
    def undo(self)->None: self._undo_fn()
    def redo(self)->None: self._redo_fn()

class ValueCommand(TimelineCommand):
    """Coalesces completed drag/slider edits with the same semantic key."""
    def __init__(self,label:str,setter:Callable[[object],None],before:object,after:object,merge_key:str):
        self.setter=setter; self.before=before; self.after=after
        super().__init__(label,lambda:setter(after),lambda:setter(before),redo=lambda:setter(after),merge_key=merge_key)
    def merge_with(self,other:BaseCommand)->bool:
        if not isinstance(other,ValueCommand) or other.merge_key!=self.merge_key: return False
        self.after=other.after; self._do=lambda:self.setter(self.after); self._redo_fn=lambda:self.setter(self.after); return True

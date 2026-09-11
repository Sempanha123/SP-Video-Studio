from __future__ import annotations

import gc
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock


class AIResourceConflict(RuntimeError): pass


@dataclass(slots=True)
class _Engine:
    unload: Callable[[], None]
    busy: Callable[[], bool]
    loaded: Callable[[], bool]
    last_used: float = 0.0


class AIResourceManager:
    """Coordinates heavy local engines without preloading them at startup."""
    def __init__(self, profile: str = "balanced", idle_timeout_seconds: float = 300.0) -> None:
        self._lock=RLock();self._engines:dict[str,_Engine]={};self.profile=profile;self.idle_timeout_seconds=max(10.0,float(idle_timeout_seconds))

    def register(self,engine_id:str,unload:Callable[[],None],busy:Callable[[],bool],loaded:Callable[[],bool]|None=None)->None:
        with self._lock:self._engines[engine_id]=_Engine(unload,busy,loaded or (lambda:True),0.0)

    def set_profile(self,profile:str)->None:self.profile=str(profile or "balanced")

    def touch(self,engine_id:str)->None:
        with self._lock:
            item=self._engines.get(engine_id)
            if item:item.last_used=time.monotonic()

    def prepare(self,engine_id:str,device:str)->None:
        self.touch(engine_id)
        if not str(device).startswith("cuda"):return
        with self._lock:
            for other_id,item in tuple(self._engines.items()):
                if other_id==engine_id:continue
                if item.busy():raise AIResourceConflict(f"{other_id} is currently using GPU resources.")
                if item.loaded():item.unload()
        gc.collect()

    def release_idle(self,now:float|None=None,upcoming:set[str]|None=None)->list[str]:
        if self.profile not in {"auto","low_memory","balanced"}:return []
        cutoff=(now if now is not None else time.monotonic())-self.idle_timeout_seconds
        upcoming=upcoming or set();released=[]
        with self._lock:
            for engine_id,item in self._engines.items():
                if engine_id in upcoming or item.busy() or not item.loaded():continue
                aggressive=self.profile=="low_memory"
                if aggressive or (item.last_used and item.last_used<=cutoff):
                    item.unload();released.append(engine_id)
        if released:gc.collect()
        return released

    def run_with_oom_retry(self,engine_id:str,device:str,operation:Callable[[],object],is_oom:Callable[[BaseException],bool]|None=None):
        self.prepare(engine_id,device)
        try:
            value=operation();self.touch(engine_id);return value
        except BaseException as exc:
            checker=is_oom or (lambda e:"out of memory" in str(e).casefold() or "cuda oom" in str(e).casefold())
            if not checker(exc):raise
            self._release_inactive(exclude=engine_id);gc.collect()
            # Exactly one retry. A second OOM is surfaced to the caller.
            value=operation();self.touch(engine_id);return value

    def _release_inactive(self,exclude:str="")->list[str]:
        released=[]
        with self._lock:
            for engine_id,item in self._engines.items():
                if engine_id==exclude or item.busy() or not item.loaded():continue
                item.unload();released.append(engine_id)
        return released

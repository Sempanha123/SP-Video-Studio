from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic, time
from typing import Callable, Iterable

from domain.autosave_state import AutosaveStatus, ProjectAutosaveState
from domain.recovery_errors import AutosaveFailed


@dataclass(slots=True)
class AutosavePolicy:
    """Backward-compatible deterministic debounce helper used by older controllers/tests."""
    delay_seconds: float = 1.5
    touched_at: float | None = None
    @property
    def pending(self) -> bool: return self.touched_at is not None
    def touch(self, now: float) -> None: self.touched_at=float(now)
    def due(self, now: float) -> bool: return self.touched_at is not None and float(now)-self.touched_at>=self.delay_seconds
    def clear(self) -> None: self.touched_at=None


SaveHandler=Callable[[str,set[str],int],None]

class AutosaveService:
    """Application-wide revision-aware autosave coordinator.

    Controllers keep transient UI buffers, but all save timing/revision bookkeeping is
    centralized here. Handlers are registered by domain and invoked only when their
    topic is dirty. Structural actions can mark dirty with immediate=True.
    """
    DEFAULT_DEBOUNCE=1.5
    TOPIC_DELAYS={
        'script':1.5,'translation':1.5,'subtitle_text':1.5,'speech_text':1.5,'news_text':1.5,'story_text':1.5,
        'scene_inspector':0.9,'short_metadata':1.0,'timeline':0.35,'subtitle_timing':0.55,'reframe':0.5,
        'structural':0.0,'project_settings':0.0,'speaker':0.0,'template_apply':0.0,'batch_checkpoint':0.0,
    }
    def __init__(self,repository,*,clock:Callable[[],float]=time,logger=None):
        self.repository=repository; self.clock=clock; self.logger=logger; self._handlers:dict[str,SaveHandler]={}; self._states:dict[str,ProjectAutosaveState]={}; self._lock=RLock(); self._listeners=[]
    def register_handler(self,topic:str,handler:SaveHandler)->None:self._handlers[str(topic)]=handler
    def on_change(self,listener:Callable[[ProjectAutosaveState],None])->None:self._listeners.append(listener)
    def state(self,project_id:str)->ProjectAutosaveState:
        with self._lock:
            state=self._states.get(project_id)
            if state is None:
                state=self.repository.get_autosave(project_id) or ProjectAutosaveState(project_id)
                self._states[project_id]=state
            return state
    def mark_dirty(self,project_id:str,topic:str='structural',*,immediate:bool=False,now:float|None=None)->int:
        if not project_id:return 0
        stamp=self.clock() if now is None else float(now);delay=0.0 if immediate else float(self.TOPIC_DELAYS.get(topic,self.DEFAULT_DEBOUNCE))
        with self._lock:
            state=self.state(project_id);rev=state.mark_dirty([topic],now=stamp,delay_seconds=delay);self.repository.save_autosave(state);self._emit(state)
        if immediate:self.flush(project_id,reason=f'immediate:{topic}')
        return rev
    def mark_structural_saved(self,project_id:str,topic:str='structural')->int:
        """Use when an existing service already persisted a structural transaction."""
        stamp=self.clock()
        with self._lock:
            state=self.state(project_id);rev=state.mark_dirty([topic],now=stamp,delay_seconds=0);state.complete_save(rev,now=stamp);self.repository.save_autosave(state);self._emit(state);return rev
    def tick(self,now:float|None=None)->list[str]:
        stamp=self.clock() if now is None else float(now);done=[]
        for pid in list(self._states):
            if self.state(pid).due(stamp):
                try:self.flush(pid,reason='debounce');done.append(pid)
                except AutosaveFailed:pass
        return done
    def flush(self,project_id:str,*,reason:str='manual',topics:Iterable[str]|None=None)->bool:
        if not project_id:return True
        with self._lock:
            state=self.state(project_id)
            if not state.dirty:
                if state.status_code not in {AutosaveStatus.CLEAN.value,AutosaveStatus.SAVED.value}:
                    state.status=AutosaveStatus.SAVED;self.repository.save_autosave(state);self._emit(state)
                return True
            revision=state.begin_save(now=self.clock());dirty=set(state.dirty_topics);selected=set(topics or dirty);self.repository.save_autosave(state);self._emit(state)
        try:
            for topic in sorted(selected):
                handler=self._handlers.get(topic)
                if handler:handler(project_id,dirty,revision)
        except Exception as exc:
            with self._lock:
                state=self.state(project_id);state.fail_save(str(exc));self.repository.save_autosave(state);self._emit(state)
            if self.logger:self.logger.exception('Autosave failed for project %s',project_id)
            raise AutosaveFailed('Your latest changes could not be saved.') from exc
        with self._lock:
            state=self.state(project_id)
            # Remove only topics represented by this save if no newer edit has reused them.
            if state.project_revision==revision:state.dirty_topics.difference_update(selected)
            state.complete_save(revision,now=self.clock());self.repository.save_autosave(state);self._emit(state)
            if state.project_revision>revision and state.scheduled_at is None:
                state.status=AutosaveStatus.SCHEDULED;state.scheduled_at=self.clock()+self.DEFAULT_DEBOUNCE;self.repository.save_autosave(state);self._emit(state)
        return True
    def critical_flush(self,project_id:str,*,reason:str)->bool:
        try:return self.flush(project_id,reason=reason)
        except AutosaveFailed:return False
    def flush_all(self,*,reason:str='shutdown')->bool:
        ok=True
        ids=set(self._states)|{x.project_id for x in self.repository.list_dirty()}
        for pid in ids:
            if not self.critical_flush(pid,reason=reason):ok=False
        return ok
    def retry(self,project_id:str)->bool:return self.flush(project_id,reason='retry')
    def dirty_projects(self)->list[str]:
        ids=set(self._states)|{x.project_id for x in self.repository.list_dirty()}
        return [pid for pid in ids if self.state(pid).dirty]
    def display_state(self,project_id:str)->str:
        s=self.state(project_id);code=s.status_code
        return {'saving':'Saving…','dirty':'Unsaved changes','scheduled':'Unsaved changes','failed':'Save failed','clean':'Saved','saved':'Saved'}.get(code,'Saved')
    def _emit(self,state):
        for cb in tuple(self._listeners):
            try:cb(state)
            except Exception:pass

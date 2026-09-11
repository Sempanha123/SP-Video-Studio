from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from domain.subtitle_cue import SubtitleCue
from services.subtitle_timing_service import SubtitleTimingService


class SubtitleCueListModel(QAbstractListModel):
    CueIdRole=Qt.UserRole+1; OrderRole=CueIdRole+1; StartMsRole=OrderRole+1; EndMsRole=StartMsRole+1
    TimeRole=EndMsRole+1; TextRole=TimeRole+1; SecondaryTextRole=TextRole+1; EditedRole=SecondaryTextRole+1
    LockedRole=EditedRole+1; SourceChangedRole=LockedRole+1; SourceMissingRole=SourceChangedRole+1; WarningRole=SourceMissingRole+1
    ActiveRole=WarningRole+1; ActiveWordRole=ActiveRole+1; HasWordsRole=ActiveWordRole+1
    _ROLES={CueIdRole:b"cueId",OrderRole:b"cueOrder",StartMsRole:b"startMs",EndMsRole:b"endMs",TimeRole:b"timeText",TextRole:b"cueText",SecondaryTextRole:b"secondaryText",EditedRole:b"edited",LockedRole:b"locked",SourceChangedRole:b"sourceChanged",SourceMissingRole:b"sourceMissing",WarningRole:b"warning",ActiveRole:b"active",ActiveWordRole:b"activeWord",HasWordsRole:b"hasWords"}
    def __init__(self,parent=None): super().__init__(parent); self._all=[]; self._visible=[]; self._query=""; self._filter="all"; self._playhead=0; self._active_row=-1
    def roleNames(self): return self._ROLES
    def rowCount(self,parent=QModelIndex()): return 0 if parent.isValid() else len(self._visible)
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid() or not 0<=index.row()<len(self._visible): return None
        q=self._visible[index.row()]; warning=str(q.metadata.get("validationWarning", "")); active=q.start_ms<=self._playhead<q.end_ms
        active_word=""
        if active:
            for w in q.words:
                if w.start_ms<=self._playhead<w.end_ms: active_word=w.text; break
        values={self.CueIdRole:q.cue_id,self.OrderRole:q.order,self.StartMsRole:q.start_ms,self.EndMsRole:q.end_ms,self.TimeRole:f"{SubtitleTimingService.format_timestamp(q.start_ms)} → {SubtitleTimingService.format_timestamp(q.end_ms)}",self.TextRole:q.text,self.SecondaryTextRole:q.secondary_text,self.EditedRole:q.edited,self.LockedRole:q.locked,self.SourceChangedRole:bool(q.metadata.get("sourceChanged")),self.SourceMissingRole:bool(q.metadata.get("sourceMissing")),self.WarningRole:warning,self.ActiveRole:active,self.ActiveWordRole:active_word,self.HasWordsRole:bool(q.words)}
        return q.text if role==Qt.DisplayRole else values.get(role)
    def replace(self,cues): self.beginResetModel(); self._all=list(cues); self._apply(); self.endResetModel()
    def set_search(self,value): self.beginResetModel(); self._query=(value or "").casefold().strip(); self._apply(); self.endResetModel()
    def set_filter(self,value): self.beginResetModel(); self._filter=(value or "all").lower(); self._apply(); self.endResetModel()
    def set_playhead(self,value):
        old=self._active_row; self._playhead=int(value); self._active_row=self._find_active_row(self._playhead)
        roles=[self.ActiveRole,self.ActiveWordRole]
        if old>=0 and old<len(self._visible): self.dataChanged.emit(self.index(old,0),self.index(old,0),roles)
        if self._active_row>=0 and self._active_row<len(self._visible) and self._active_row!=old: self.dataChanged.emit(self.index(self._active_row,0),self.index(self._active_row,0),roles)
    def _find_active_row(self,position):
        lo,hi=0,len(self._visible)-1
        while lo<=hi:
            mid=(lo+hi)//2; cue=self._visible[mid]
            if position<cue.start_ms: hi=mid-1
            elif position>=cue.end_ms: lo=mid+1
            else: return mid
        return -1
    def cue(self,cue_id): return next((q for q in self._all if q.cue_id==cue_id),None)
    def all_cues(self): return list(self._all)
    def _apply(self):
        def match(q):
            if self._query and self._query not in (q.text+'\n'+q.secondary_text).casefold(): return False
            if self._filter=='edited' and not q.edited: return False
            if self._filter=='source_changed' and not q.metadata.get('sourceChanged'): return False
            if self._filter=='warnings' and not q.metadata.get('validationWarning'): return False
            return True
        self._visible=[q for q in self._all if match(q)]
        self._active_row=self._find_active_row(self._playhead)

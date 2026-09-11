from __future__ import annotations

from typing import Any
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class SceneListModel(QAbstractListModel):
    IdRole=Qt.UserRole+1; NumberRole=IdRole+1; NameRole=NumberRole+1; DurationRole=NameRole+1; DurationTextRole=DurationRole+1
    StatusRole=DurationTextRole+1; StatusNameRole=StatusRole+1; EnabledRole=StatusNameRole+1; MediaRole=EnabledRole+1
    ThumbnailRole=MediaRole+1; NarrationRole=ThumbnailRole+1; SubtitleRole=NarrationRole+1; SourceRole=SubtitleRole+1; SelectedRole=SourceRole+1
    _ROLES={IdRole:b"sceneId",NumberRole:b"sceneNumber",NameRole:b"sceneName",DurationRole:b"durationMs",DurationTextRole:b"durationText",StatusRole:b"sceneStatus",StatusNameRole:b"statusName",EnabledRole:b"enabled",MediaRole:b"hasMedia",ThumbnailRole:b"thumbnailUrl",NarrationRole:b"hasNarration",SubtitleRole:b"hasSubtitle",SourceRole:b"sourceLabel",SelectedRole:b"selected"}
    def __init__(self,parent=None): super().__init__(parent); self._items:list[dict[str,Any]]=[]; self._selected=""
    def roleNames(self): return self._ROLES
    def rowCount(self,parent=QModelIndex()): return 0 if parent.isValid() else len(self._items)
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid() or not 0<=index.row()<len(self._items): return None
        item=self._items[index.row()]
        values={self.IdRole:item.get('id',''),self.NumberRole:item.get('number',0),self.NameRole:item.get('name',''),self.DurationRole:item.get('durationMs',0),self.DurationTextRole:item.get('durationText',''),self.StatusRole:item.get('status',''),self.StatusNameRole:item.get('statusName',''),self.EnabledRole:item.get('enabled',True),self.MediaRole:item.get('hasMedia',False),self.ThumbnailRole:item.get('thumbnailUrl',''),self.NarrationRole:item.get('hasNarration',False),self.SubtitleRole:item.get('hasSubtitle',False),self.SourceRole:item.get('sourceLabel',''),self.SelectedRole:item.get('id')==self._selected}
        return item.get('name','') if role==Qt.DisplayRole else values.get(role)
    def replace(self,items:list[dict[str,Any]],selected_id:str=""):
        self.beginResetModel(); self._items=[dict(x) for x in items]; self._selected=selected_id; self.endResetModel()
    def set_selected(self,scene_id:str):
        if scene_id==self._selected:return
        old=self._selected; self._selected=scene_id
        for row,item in enumerate(self._items):
            if item.get('id') in {old,scene_id}:
                idx=self.index(row,0); self.dataChanged.emit(idx,idx,[self.SelectedRole])

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class VoiceListModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    NameRole = IdRole + 1
    TypeRole = NameRole + 1
    LanguageRole = TypeRole + 1
    LanguageNameRole = LanguageRole + 1
    CategoryRole = LanguageNameRole + 1
    TagsRole = CategoryRole + 1
    DescriptionRole = TagsRole + 1
    EngineRole = DescriptionRole + 1
    FavoriteRole = EngineRole + 1
    BuiltinRole = FavoriteRole + 1
    SelectedRole = BuiltinRole + 1
    RecommendedRole = SelectedRole + 1
    VoiceDataRole = RecommendedRole + 1

    _ROLES = {
        IdRole: b"voiceId", NameRole: b"name", TypeRole: b"voiceType",
        LanguageRole: b"language", LanguageNameRole: b"languageName", CategoryRole: b"category",
        TagsRole: b"styleTags", DescriptionRole: b"description", EngineRole: b"engineName",
        FavoriteRole: b"favorite", BuiltinRole: b"isBuiltin", SelectedRole: b"selected",
        RecommendedRole: b"recommended", VoiceDataRole: b"voiceData",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._selected_id = ""

    def roleNames(self):
        return self._ROLES

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {
            self.IdRole: item.get("id", ""), self.NameRole: item.get("name", ""),
            self.TypeRole: item.get("voiceType", "preset"), self.LanguageRole: item.get("language", "en"),
            self.LanguageNameRole: item.get("languageName", "English"), self.CategoryRole: item.get("category", ""),
            self.TagsRole: item.get("styleTags", []), self.DescriptionRole: item.get("description", ""),
            self.EngineRole: item.get("engineName", "VoxCPM2"), self.FavoriteRole: bool(item.get("favorite", False)),
            self.BuiltinRole: bool(item.get("isBuiltin", False)), self.SelectedRole: item.get("id") == self._selected_id,
            self.RecommendedRole: bool(item.get("recommended", False)), self.VoiceDataRole: item,
        }
        return mapping.get(role)

    def replace(self, items: list[dict[str, Any]], selected_id: str = "") -> None:
        self.beginResetModel()
        self._items = [dict(item) for item in items]
        self._selected_id = selected_id
        self.endResetModel()

    def set_selected(self, voice_id: str) -> None:
        if voice_id == self._selected_id:
            return
        old = self._selected_id
        self._selected_id = voice_id
        for row, item in enumerate(self._items):
            if item.get("id") in {old, voice_id}:
                idx = self.index(row, 0)
                self.dataChanged.emit(idx, idx, [self.SelectedRole])

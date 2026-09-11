from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QUrl

from domain.media import MediaAsset
from ui.models.media_format import format_duration, format_file_size, format_resolution


class MediaListModel(QAbstractListModel):
    MediaIdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    TypeRole = Qt.UserRole + 3
    TypeNameRole = Qt.UserRole + 4
    ThumbnailRole = Qt.UserRole + 5
    DurationRole = Qt.UserRole + 6
    ResolutionRole = Qt.UserRole + 7
    SizeRole = Qt.UserRole + 8
    StatusRole = Qt.UserRole + 9
    StatusNameRole = Qt.UserRole + 10
    ImportedAtRole = Qt.UserRole + 11
    ProjectPathRole = Qt.UserRole + 12

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._assets: list[MediaAsset] = []

    def roleNames(self):
        return {
            self.MediaIdRole: b"mediaId",
            self.NameRole: b"name",
            self.TypeRole: b"mediaType",
            self.TypeNameRole: b"typeName",
            self.ThumbnailRole: b"thumbnail",
            self.DurationRole: b"duration",
            self.ResolutionRole: b"resolution",
            self.SizeRole: b"fileSize",
            self.StatusRole: b"status",
            self.StatusNameRole: b"statusName",
            self.ImportedAtRole: b"importedAt",
            self.ProjectPathRole: b"projectPath",
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._assets)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._assets):
            return None
        asset = self._assets[index.row()]
        values = {
            self.MediaIdRole: asset.asset_id,
            self.NameRole: asset.name,
            self.TypeRole: asset.type,
            self.TypeNameRole: asset.type.title(),
            self.ThumbnailRole: self._thumbnail_url(asset),
            self.DurationRole: format_duration(asset.duration_ms),
            self.ResolutionRole: format_resolution(asset.width, asset.height),
            self.SizeRole: format_file_size(asset.file_size),
            self.StatusRole: str(asset.status),
            self.StatusNameRole: str(asset.status).replace("_", " ").title(),
            self.ImportedAtRole: asset.imported_at,
            self.ProjectPathRole: asset.project_path,
        }
        if role == Qt.DisplayRole:
            return asset.name
        return values.get(role)

    def replace_assets(self, assets: list[MediaAsset]) -> None:
        self.beginResetModel()
        self._assets = list(assets)
        self.endResetModel()

    def asset_at(self, row: int) -> MediaAsset | None:
        if 0 <= row < len(self._assets):
            return self._assets[row]
        return None

    @staticmethod
    def _thumbnail_url(asset: MediaAsset) -> str:
        if not asset.thumbnail_path:
            return ""
        path = Path(asset.thumbnail_path)
        if not path.is_file():
            return ""
        return QUrl.fromLocalFile(str(path)).toString()

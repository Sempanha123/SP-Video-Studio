from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class ModelListModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    NameRole = IdRole + 1
    FamilyRole = NameRole + 1
    PurposeRole = FamilyRole + 1
    DescriptionRole = PurposeRole + 1
    StatusRole = DescriptionRole + 1
    StatusDisplayRole = StatusRole + 1
    ProgressRole = StatusDisplayRole + 1
    DownloadedBytesRole = ProgressRole + 1
    TotalBytesRole = DownloadedBytesRole + 1
    DownloadSpeedRole = TotalBytesRole + 1
    CurrentFileRole = DownloadSpeedRole + 1
    InstalledRole = CurrentFileRole + 1
    VerifiedRole = InstalledRole + 1
    RecommendedRole = VerifiedRole + 1
    CompatibilityRole = RecommendedRole + 1
    CompatibilityDisplayRole = CompatibilityRole + 1
    InstallPathRole = CompatibilityDisplayRole + 1
    DiskUsageRole = InstallPathRole + 1
    DiskUsageDisplayRole = DiskUsageRole + 1
    DownloadSizeDisplayRole = DiskUsageDisplayRole + 1
    DiskSizeDisplayRole = DownloadSizeDisplayRole + 1
    LicenseRole = DiskSizeDisplayRole + 1
    VersionRole = LicenseRole + 1
    SourceIdentifierRole = VersionRole + 1
    LanguagesRole = SourceIdentifierRole + 1
    ErrorMessageRole = LanguagesRole + 1
    InUseCountRole = ErrorMessageRole + 1
    ModelDataRole = InUseCountRole + 1

    _ROLE_NAMES = {
        IdRole: b"modelId",
        NameRole: b"name",
        FamilyRole: b"family",
        PurposeRole: b"purpose",
        DescriptionRole: b"description",
        StatusRole: b"status",
        StatusDisplayRole: b"statusDisplay",
        ProgressRole: b"progress",
        DownloadedBytesRole: b"downloadedBytes",
        TotalBytesRole: b"totalBytes",
        DownloadSpeedRole: b"downloadSpeed",
        CurrentFileRole: b"currentFile",
        InstalledRole: b"installed",
        VerifiedRole: b"verified",
        RecommendedRole: b"recommended",
        CompatibilityRole: b"compatibility",
        CompatibilityDisplayRole: b"compatibilityDisplay",
        InstallPathRole: b"installPath",
        DiskUsageRole: b"diskUsage",
        DiskUsageDisplayRole: b"diskUsageDisplay",
        DownloadSizeDisplayRole: b"downloadSizeDisplay",
        DiskSizeDisplayRole: b"diskSizeDisplay",
        LicenseRole: b"license",
        VersionRole: b"version",
        SourceIdentifierRole: b"sourceIdentifier",
        LanguagesRole: b"languages",
        ErrorMessageRole: b"errorMessage",
        InUseCountRole: b"inUseCount",
        ModelDataRole: b"modelData",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []

    def roleNames(self) -> dict[int, bytes]:
        return self._ROLE_NAMES

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {
            self.IdRole: item.get("id", ""),
            self.NameRole: item.get("name", ""),
            self.FamilyRole: item.get("family", ""),
            self.PurposeRole: item.get("purpose", ""),
            self.DescriptionRole: item.get("description", ""),
            self.StatusRole: item.get("status", "not_installed"),
            self.StatusDisplayRole: item.get("statusDisplay", "Not Installed"),
            self.ProgressRole: float(item.get("progress", 0.0)),
            self.DownloadedBytesRole: int(item.get("downloadedBytes", 0)),
            self.TotalBytesRole: int(item.get("totalBytes", 0)),
            self.DownloadSpeedRole: float(item.get("downloadSpeed", 0.0)),
            self.CurrentFileRole: item.get("currentFile", ""),
            self.InstalledRole: bool(item.get("installed", False)),
            self.VerifiedRole: item.get("verificationStatus") == "verified",
            self.RecommendedRole: bool(item.get("recommended", False)),
            self.CompatibilityRole: item.get("compatibility", "unknown"),
            self.CompatibilityDisplayRole: item.get("compatibilityDisplay", "Unknown"),
            self.InstallPathRole: item.get("installPath", ""),
            self.DiskUsageRole: int(item.get("diskUsageBytes", 0)),
            self.DiskUsageDisplayRole: item.get("diskUsageDisplay", "0 B"),
            self.DownloadSizeDisplayRole: item.get("downloadSizeDisplay", "Unknown"),
            self.DiskSizeDisplayRole: item.get("diskSizeDisplay", "Unknown"),
            self.LicenseRole: item.get("license", ""),
            self.VersionRole: item.get("version", ""),
            self.SourceIdentifierRole: item.get("sourceIdentifier", ""),
            self.LanguagesRole: ", ".join(item.get("supportedLanguages", [])),
            self.ErrorMessageRole: item.get("errorMessage", ""),
            self.InUseCountRole: int(item.get("inUseCount", 0)),
            self.ModelDataRole: item,
        }
        return mapping.get(role)

    def replace(self, items: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._items = [dict(item) for item in items]
        self.endResetModel()

    def update_model(self, model_id: str, changes: dict[str, Any]) -> None:
        for row, item in enumerate(self._items):
            if item.get("id") != model_id:
                continue
            item.update(changes)
            left = self.index(row, 0)
            self.dataChanged.emit(left, left, list(self._ROLE_NAMES.keys()))
            return

    def get(self, model_id: str) -> dict[str, Any] | None:
        for item in self._items:
            if item.get("id") == model_id:
                return dict(item)
        return None

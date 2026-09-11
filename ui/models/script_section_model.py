from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from domain.script_section import ScriptSection
from services.script_analysis_service import ScriptAnalysisService


class ScriptSectionListModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    OrderRole = Qt.UserRole + 2
    TypeRole = Qt.UserRole + 3
    TitleRole = Qt.UserRole + 4
    PreviewRole = Qt.UserRole + 5
    EnabledRole = Qt.UserRole + 6
    MetricRole = Qt.UserRole + 7
    DurationRole = Qt.UserRole + 8
    SelectedRole = Qt.UserRole + 9
    SceneSourceRole = Qt.UserRole + 10

    def __init__(self, analysis: ScriptAnalysisService, parent=None) -> None:
        super().__init__(parent)
        self._analysis = analysis
        self._sections: list[ScriptSection] = []
        self._language = "en"
        self._pace = "normal"
        self._selected_id = ""

    def roleNames(self):
        return {
            self.IdRole: b"sectionId",
            self.OrderRole: b"sectionOrder",
            self.TypeRole: b"sectionType",
            self.TitleRole: b"title",
            self.PreviewRole: b"preview",
            self.EnabledRole: b"sectionEnabled",
            self.MetricRole: b"metric",
            self.DurationRole: b"durationText",
            self.SelectedRole: b"selected",
            self.SceneSourceRole: b"sceneSource",
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._sections)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid() or not 0 <= index.row() < len(self._sections):
            return None
        section = self._sections[index.row()]
        result = self._analysis.analyze_text(section.content, self._language, self._pace)
        if role == self.IdRole:
            return section.section_id
        if role == self.OrderRole:
            return section.order
        if role == self.TypeRole:
            return section.type
        if role == self.TitleRole:
            return section.title
        if role == self.PreviewRole:
            return " ".join(section.content.strip().split())[:72]
        if role == self.EnabledRole:
            return section.enabled
        if role == self.MetricRole:
            suffix = "chars" if result.metric_label == "characters" else "words"
            return f"{result.metric_value} {suffix}"
        if role == self.DurationRole:
            return self._analysis.format_duration(result.estimated_duration_ms)
        if role == self.SelectedRole:
            return section.section_id == self._selected_id
        if role == self.SceneSourceRole:
            return bool(section.metadata.get("scene_source", True))
        return None

    def set_sections(self, sections: list[ScriptSection], language: str, pace: str, selected_id: str = "") -> None:
        self.beginResetModel()
        self._sections = sections
        self._language = language
        self._pace = pace
        self._selected_id = selected_id
        self.endResetModel()

    def set_selected(self, section_id: str) -> None:
        if section_id == self._selected_id:
            return
        old = self._selected_id
        self._selected_id = section_id
        for i, section in enumerate(self._sections):
            if section.section_id in {old, section_id}:
                idx = self.index(i, 0)
                self.dataChanged.emit(idx, idx, [self.SelectedRole])

    def section_changed(self, section_id: str) -> None:
        for i, section in enumerate(self._sections):
            if section.section_id == section_id:
                idx = self.index(i, 0)
                self.dataChanged.emit(idx, idx)
                return

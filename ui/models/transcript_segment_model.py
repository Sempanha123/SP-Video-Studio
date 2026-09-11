from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from domain.transcript_segment import TranscriptSegment
from services.transcript_analysis_service import format_timestamp_ms


class TranscriptSegmentListModel(QAbstractListModel):
    SegmentIdRole = Qt.UserRole + 1
    OrderRole = Qt.UserRole + 2
    StartMsRole = Qt.UserRole + 3
    EndMsRole = Qt.UserRole + 4
    StartTextRole = Qt.UserRole + 5
    EndTextRole = Qt.UserRole + 6
    TextRole = Qt.UserRole + 7
    OriginalTextRole = Qt.UserRole + 8
    EditedRole = Qt.UserRole + 9
    WordCountRole = Qt.UserRole + 10

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._all: list[TranscriptSegment] = []
        self._visible: list[TranscriptSegment] = []
        self._query = ""

    def roleNames(self):
        return {
            self.SegmentIdRole: b"segmentId",
            self.OrderRole: b"segmentOrder",
            self.StartMsRole: b"startMs",
            self.EndMsRole: b"endMs",
            self.StartTextRole: b"startText",
            self.EndTextRole: b"endText",
            self.TextRole: b"segmentText",
            self.OriginalTextRole: b"originalText",
            self.EditedRole: b"edited",
            self.WordCountRole: b"wordCount",
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._visible)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._visible):
            return None
        item = self._visible[index.row()]
        values = {
            self.SegmentIdRole: item.segment_id,
            self.OrderRole: item.order,
            self.StartMsRole: item.start_ms,
            self.EndMsRole: item.end_ms,
            self.StartTextRole: format_timestamp_ms(item.start_ms),
            self.EndTextRole: format_timestamp_ms(item.end_ms),
            self.TextRole: item.text,
            self.OriginalTextRole: item.original_text,
            self.EditedRole: bool(item.edited),
            self.WordCountRole: len(item.words),
        }
        if role == Qt.DisplayRole:
            return item.text
        return values.get(role)

    def replace(self, segments: list[TranscriptSegment]) -> None:
        self.beginResetModel()
        self._all = list(segments)
        self._apply_filter()
        self.endResetModel()

    def set_search(self, query: str) -> None:
        query = (query or "").strip().lower()
        if query == self._query:
            return
        self.beginResetModel()
        self._query = query
        self._apply_filter()
        self.endResetModel()

    def update_text(self, segment_id: str, text: str, edited: bool) -> None:
        for item in self._all:
            if item.segment_id == segment_id:
                item.text = text
                item.edited = edited
                break
        self.beginResetModel()
        self._apply_filter()
        self.endResetModel()

    def segment(self, segment_id: str) -> TranscriptSegment | None:
        return next((item for item in self._all if item.segment_id == segment_id), None)

    def all_segments(self) -> list[TranscriptSegment]:
        return list(self._all)

    def _apply_filter(self) -> None:
        if not self._query:
            self._visible = list(self._all)
        else:
            self._visible = [item for item in self._all if self._query in item.text.lower()]

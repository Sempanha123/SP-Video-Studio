from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from domain.translation_segment import TranslationSegment
from services.transcript_analysis_service import format_timestamp_ms


class TranslationSegmentListModel(QAbstractListModel):
    SegmentIdRole = Qt.UserRole + 1
    SourceSegmentIdRole = SegmentIdRole + 1
    OrderRole = SourceSegmentIdRole + 1
    StartMsRole = OrderRole + 1
    EndMsRole = StartMsRole + 1
    TimeTextRole = EndMsRole + 1
    SourceTextRole = TimeTextRole + 1
    MachineTextRole = SourceTextRole + 1
    TranslatedTextRole = MachineTextRole + 1
    StatusRole = TranslatedTextRole + 1
    StatusNameRole = StatusRole + 1
    EditedRole = StatusNameRole + 1
    ReviewedRole = EditedRole + 1
    LockedRole = ReviewedRole + 1
    WarningsRole = LockedRole + 1
    OrphanedRole = WarningsRole + 1

    _ROLES = {
        SegmentIdRole: b"segmentId",
        SourceSegmentIdRole: b"sourceSegmentId",
        OrderRole: b"segmentOrder",
        StartMsRole: b"startMs",
        EndMsRole: b"endMs",
        TimeTextRole: b"timeText",
        SourceTextRole: b"sourceText",
        MachineTextRole: b"machineTranslation",
        TranslatedTextRole: b"translatedText",
        StatusRole: b"segmentStatus",
        StatusNameRole: b"statusName",
        EditedRole: b"edited",
        ReviewedRole: b"reviewed",
        LockedRole: b"locked",
        WarningsRole: b"qualityWarnings",
        OrphanedRole: b"orphaned",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._all: list[TranslationSegment] = []
        self._visible: list[TranslationSegment] = []
        self._query = ""
        self._status_filter = "all"

    def roleNames(self):
        return self._ROLES

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._visible)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._visible):
            return None
        item = self._visible[index.row()]
        time_text = ""
        if item.start_ms is not None and item.end_ms is not None:
            time_text = f"{format_timestamp_ms(item.start_ms)} → {format_timestamp_ms(item.end_ms)}"
        values = {
            self.SegmentIdRole: item.segment_id,
            self.SourceSegmentIdRole: item.source_segment_id,
            self.OrderRole: item.order,
            self.StartMsRole: item.start_ms if item.start_ms is not None else -1,
            self.EndMsRole: item.end_ms if item.end_ms is not None else -1,
            self.TimeTextRole: time_text,
            self.SourceTextRole: item.source_text,
            self.MachineTextRole: item.machine_translation,
            self.TranslatedTextRole: item.translated_text,
            self.StatusRole: item.status_code,
            self.StatusNameRole: item.display_status,
            self.EditedRole: item.edited,
            self.ReviewedRole: item.reviewed,
            self.LockedRole: item.locked,
            self.WarningsRole: list(item.metadata.get("qualityWarnings", [])),
            self.OrphanedRole: item.status_code == "orphaned",
        }
        if role == Qt.DisplayRole:
            return item.translated_text
        return values.get(role)

    def replace(self, segments: list[TranslationSegment]) -> None:
        self.beginResetModel()
        self._all = list(segments)
        self._apply_filter()
        self.endResetModel()

    def update_item(self, updated: TranslationSegment) -> None:
        for index, item in enumerate(self._all):
            if item.segment_id == updated.segment_id:
                self._all[index] = updated
                break
        self.beginResetModel()
        self._apply_filter()
        self.endResetModel()

    def set_search(self, query: str) -> None:
        value = (query or "").strip().casefold()
        if value == self._query:
            return
        self.beginResetModel()
        self._query = value
        self._apply_filter()
        self.endResetModel()

    def set_filter(self, status_filter: str) -> None:
        value = (status_filter or "all").strip().lower()
        if value == self._status_filter:
            return
        self.beginResetModel()
        self._status_filter = value
        self._apply_filter()
        self.endResetModel()

    def segment(self, segment_id: str) -> TranslationSegment | None:
        return next((item for item in self._all if item.segment_id == segment_id), None)

    def all_segments(self) -> list[TranslationSegment]:
        return list(self._all)

    def _apply_filter(self) -> None:
        def matches(item: TranslationSegment) -> bool:
            if self._query:
                haystack = f"{item.source_text}\n{item.translated_text}".casefold()
                if self._query not in haystack:
                    return False
            mode = self._status_filter
            if mode == "reviewed" and not item.reviewed:
                return False
            if mode == "unreviewed" and item.reviewed:
                return False
            if mode == "edited" and not item.edited:
                return False
            if mode == "locked" and not item.locked:
                return False
            if mode == "needs_attention" and item.status_code != "needs_attention":
                return False
            return True

        self._visible = [item for item in self._all if matches(item)]

from __future__ import annotations

from PySide6.QtCore import Slot

from ui.controllers.manual_speech_controller import ManualSpeechController


class ProductivitySpeechController(ManualSpeechController):
    """Phase 33 keyboard productivity additions without a second speech model."""

    @Slot(result=bool)
    def duplicateSelected(self) -> bool:
        try:
            if len(self._selected) != 1:
                self.operationFailed.emit("Select one SpeechBlock to duplicate.")
                return False
            block_id = next(iter(self._selected))
            source = self.service.blocks.repository.block(self._project_id, block_id)
            if source is None:
                self.operationFailed.emit("Speech block not found.")
                return False
            rows = self.service.blocks.repository.blocks_for_section(source.script_section_id)
            start = max([int(item.timeline_end_ms or 0) for item in rows] or [0])
            duration = max(1, int(source.allocated_duration_ms or 2000))
            clone = self.service.blocks.add(
                self._project_id,
                source.script_section_id,
                source.text,
                speaker_id=source.speaker_id,
                language=source.language,
                source_type=source.source_type_code,
                start_ms=start,
                end_ms=start + duration,
                voice_override_id=source.voice_override_id,
            )
            clone.pause_before_ms = source.pause_before_ms
            clone.pause_after_ms = source.pause_after_ms
            clone.metadata = dict(source.metadata or {})
            clone.metadata.pop("generatedDurationMs", None)
            clone.metadata.pop("durationDeltaMs", None)
            self.service.blocks.repository.save_block(self._project_id, clone)
            self._selected = {clone.id}
            self.selectionChanged.emit()
            return self._changed("Speech block duplicated")
        except Exception as exc:
            self._fail(exc)
            return False

    @Slot(int, result=bool)
    def selectRelative(self, delta: int) -> bool:
        if not self._rows:
            return False
        ids = [str(row.get("id", "")) for row in self._rows if row.get("id")]
        if not ids:
            return False
        current = next(iter(self._selected), "")
        try:
            index = ids.index(current)
        except ValueError:
            index = 0 if int(delta) >= 0 else len(ids) - 1
        else:
            index = max(0, min(len(ids) - 1, index + int(delta)))
        selected = ids[index]
        self._selected = {selected}
        self.selectionChanged.emit()
        self.seekRow(selected)
        return True

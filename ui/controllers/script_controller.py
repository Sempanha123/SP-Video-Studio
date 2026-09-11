from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from domain.project import utc_now_iso
from domain.script import Script
from domain.script_section import ScriptSection
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService, ScriptServiceError
from ui.models.script_section_model import ScriptSectionListModel


LANGUAGE_NAMES = {"en": "English", "km": "Khmer"}
PACE_NAMES = {"slow": "Slow", "normal": "Normal", "fast": "Fast"}


class ScriptController(QObject):
    scriptChanged = Signal()
    selectedSectionChanged = Signal()
    analysisChanged = Signal()
    dirtyChanged = Signal()
    saveStateChanged = Signal()
    currentProjectChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self, service: ScriptService, analysis: ScriptAnalysisService, logger=None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.analysis_service = analysis
        self.logger = logger or logging.getLogger("sp_video_studio.script_controller")
        self.sectionModel = ScriptSectionListModel(analysis, self)
        self._project_id = ""
        self._script: Script | None = None
        self._sections: list[ScriptSection] = []
        self._selected_id = ""
        self._dirty_ids: set[str] = set()
        self._dirty_script = False
        self._save_state = "Saved"
        self._analysis: dict[str, object] = self._empty_analysis()

        self._autosave = QTimer(self)
        self._autosave.setSingleShot(True)
        self._autosave.setInterval(1500)
        self._autosave.timeout.connect(self.save)
        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(400)
        self._analysis_timer.timeout.connect(self._recalculate_analysis)

    @Property(str, notify=currentProjectChanged)
    def currentProjectId(self) -> str:
        return self._project_id

    @Property("QVariantMap", notify=scriptChanged)
    def script(self) -> dict[str, object]:
        if self._script is None:
            return {}
        return {
            **self._script.to_dict(),
            "languageName": LANGUAGE_NAMES.get(self._script.language, self._script.language),
            "paceName": PACE_NAMES.get(str(self._script.pace), str(self._script.pace).title()),
        }

    @Property(QObject, constant=True)
    def sections(self):
        return self.sectionModel

    @Property("QVariantMap", notify=selectedSectionChanged)
    def selectedSection(self) -> dict[str, object]:
        section = self._selected_section()
        if section is None:
            return {}
        return section.to_dict()

    @Property("QVariantMap", notify=analysisChanged)
    def analysis(self) -> dict[str, object]:
        return self._analysis

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return bool(self._dirty_ids or self._dirty_script)

    @Property(str, notify=saveStateChanged)
    def saveState(self) -> str:
        return self._save_state

    @Slot(str, result=bool)
    def load(self, project_id: str) -> bool:
        project_id = (project_id or "").strip()
        if project_id == self._project_id and self._script is not None:
            return True
        if self.dirty and not self.save():
            return False
        self._autosave.stop()
        self._analysis_timer.stop()
        self._project_id = project_id
        self._script = None
        self._sections = []
        self._selected_id = ""
        self._dirty_ids.clear()
        self._dirty_script = False
        if not project_id:
            self.sectionModel.set_sections([], "en", "normal")
            self._analysis = self._empty_analysis()
            self.currentProjectChanged.emit(); self.scriptChanged.emit(); self.selectedSectionChanged.emit(); self.analysisChanged.emit()
            return True
        try:
            self._script, self._sections = self.service.load_or_create(project_id)
            self._selected_id = self._sections[0].section_id if self._sections else ""
            self._refresh_model()
            self._recalculate_analysis()
            self._set_save_state("Saved")
            self.currentProjectChanged.emit(); self.scriptChanged.emit(); self.selectedSectionChanged.emit(); self.dirtyChanged.emit()
            return True
        except Exception as exc:
            self.logger.exception("Could not load project script")
            self.operationFailed.emit(self._friendly_error(exc))
            return False

    @Slot(str, result=bool)
    def selectSection(self, section_id: str) -> bool:
        if section_id == self._selected_id:
            return True
        if self.dirty and not self.save():
            return False
        if not any(item.section_id == section_id for item in self._sections):
            return False
        self._selected_id = section_id
        self.sectionModel.set_selected(section_id)
        self.selectedSectionChanged.emit()
        return True

    @Slot(str, str)
    def updateSectionContent(self, section_id: str, text: str) -> None:
        section = self._section(section_id)
        if section is None or section.content == text:
            return
        section.content = text
        section.updated_at = utc_now_iso()
        self._dirty_ids.add(section_id)
        self.sectionModel.section_changed(section_id)
        self._mark_unsaved()

    @Slot(str, str)
    def updateSectionNotes(self, section_id: str, notes: str) -> None:
        section = self._section(section_id)
        if section is None or section.notes == notes:
            return
        section.notes = notes
        section.updated_at = utc_now_iso()
        self._dirty_ids.add(section_id)
        self._mark_unsaved()

    @Slot(result=bool)
    def save(self) -> bool:
        if not self._project_id or self._script is None:
            return True
        if not self.dirty:
            self._set_save_state("Saved")
            return True
        self._autosave.stop()
        self._set_save_state("Saving…")
        try:
            for section_id in list(self._dirty_ids):
                section = self._section(section_id)
                if section is not None:
                    self.service.save_section(self._project_id, section)
            if self._dirty_script:
                self.service.save_script(self._script)
            self._dirty_ids.clear()
            self._dirty_script = False
            self._set_save_state("Saved")
            self.dirtyChanged.emit()
            return True
        except Exception as exc:
            self.logger.exception("Script autosave failed")
            self._set_save_state("Save failed")
            self.operationFailed.emit("Your script could not be saved. The unsaved changes are still open.")
            return False

    @Slot(str, str, result=str)
    def addSection(self, title: str, section_type: str = "body") -> str:
        if not self.save(): return ""
        try:
            section = self.service.add_section(self._project_id, title, section_type)
            self._reload_sections(section.section_id)
            return section.section_id
        except Exception as exc:
            self._fail(exc); return ""

    @Slot(str, str, result=bool)
    def renameSection(self, section_id: str, title: str) -> bool:
        if not self.save(): return False
        try:
            self.service.rename_section(self._project_id, section_id, title)
            self._reload_sections(section_id)
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, result=str)
    def duplicateSection(self, section_id: str) -> str:
        if not self.save(): return ""
        try:
            section = self.service.duplicate_section(self._project_id, section_id)
            self._reload_sections(section.section_id)
            return section.section_id
        except Exception as exc:
            self._fail(exc); return ""

    @Slot(str, result=bool)
    def deleteSection(self, section_id: str) -> bool:
        if not self.save(): return False
        try:
            self.service.delete_section(self._project_id, section_id)
            self._reload_sections("")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, int, result=bool)
    def moveSection(self, section_id: str, new_index: int) -> bool:
        if not self.save(): return False
        try:
            self.service.move_section(self._project_id, section_id, new_index)
            self._reload_sections(section_id)
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, bool, result=bool)
    def setSectionEnabled(self, section_id: str, enabled: bool) -> bool:
        if not self.save(): return False
        try:
            self.service.set_section_enabled(self._project_id, section_id, enabled)
            self._reload_sections(section_id)
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, bool, result=bool)
    def setSceneSource(self, section_id: str, enabled: bool) -> bool:
        if not self.save(): return False
        try:
            self.service.set_scene_source(self._project_id, section_id, enabled)
            self._reload_sections(section_id)
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, result=bool)
    def setLanguage(self, language: str) -> bool:
        if not self.save(): return False
        try:
            self._script = self.service.set_language(self._project_id, language)
            self._refresh_model(); self._recalculate_analysis(); self.scriptChanged.emit()
            self.operationSucceeded.emit("Script language updated. Existing text was not translated.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, result=bool)
    def setPace(self, pace: str) -> bool:
        if not self.save(): return False
        try:
            self._script = self.service.set_pace(self._project_id, pace)
            self._refresh_model(); self._recalculate_analysis(); self.scriptChanged.emit()
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, str, result=bool)
    def importText(self, path: str, mode: str) -> bool:
        if not self.save(): return False
        try:
            local = self._url_or_path(path)
            section = self.service.import_text(self._project_id, local, mode)
            self._reload_sections(section.section_id)
            self.operationSucceeded.emit("Script text imported.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, result=bool)
    def exportText(self, path: str) -> bool:
        if not self.save(): return False
        try:
            target = self.service.export_text(self._project_id, self._url_or_path(path))
            self.operationSucceeded.emit(f"Script exported to {target.name}.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot()
    def copyFullScript(self) -> None:
        try:
            QGuiApplication.clipboard().setText(self.service.get_combined_text(self._project_id))
            self.operationSucceeded.emit("Full script copied.")
        except Exception as exc:
            self._fail(exc)

    @Slot(result=bool)
    def flush(self) -> bool:
        return self.save()

    def _reload_sections(self, prefer_id: str) -> None:
        if self._script is None: return
        self._sections = self.service.repository.list_sections(self._script.script_id)
        ids = {item.section_id for item in self._sections}
        self._selected_id = prefer_id if prefer_id in ids else (self._sections[0].section_id if self._sections else "")
        self._dirty_ids.clear(); self._dirty_script = False
        self._refresh_model(); self._recalculate_analysis(); self.selectedSectionChanged.emit(); self.dirtyChanged.emit()
        self._set_save_state("Saved")

    def _refresh_model(self) -> None:
        language = self._script.language if self._script else "en"
        pace = str(self._script.pace) if self._script else "normal"
        self.sectionModel.set_sections(self._sections, language, pace, self._selected_id)

    def _recalculate_analysis(self) -> None:
        if self._script is None:
            self._analysis = self._empty_analysis()
        else:
            result = self.analysis_service.analyze_sections(self._sections, self._script.language, str(self._script.pace))
            self._analysis = {
                "wordCount": result.word_count,
                "characterCount": result.character_count,
                "metricLabel": result.metric_label,
                "metricValue": result.metric_value,
                "durationMs": result.estimated_duration_ms,
                "durationDisplay": self.analysis_service.format_duration(result.estimated_duration_ms),
            }
        self.analysisChanged.emit()

    def _mark_unsaved(self) -> None:
        self._set_save_state("Unsaved changes")
        self.dirtyChanged.emit()
        self._analysis_timer.start()
        self._autosave.start()

    def _set_save_state(self, value: str) -> None:
        if value != self._save_state:
            self._save_state = value
            self.saveStateChanged.emit()

    def _selected_section(self) -> ScriptSection | None:
        return self._section(self._selected_id)

    def _section(self, section_id: str) -> ScriptSection | None:
        return next((item for item in self._sections if item.section_id == section_id), None)

    def _fail(self, exc: Exception) -> None:
        self.logger.exception("Script operation failed")
        self.operationFailed.emit(self._friendly_error(exc))

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        if isinstance(exc, ScriptServiceError):
            return str(exc).strip() or exc.user_message
        return str(exc).strip() or "SP Video Studio could not complete that script action."

    @staticmethod
    def _empty_analysis() -> dict[str, object]:
        return {"wordCount": 0, "characterCount": 0, "metricLabel": "words", "metricValue": 0, "durationMs": 0, "durationDisplay": "~0 sec"}

    @staticmethod
    def _url_or_path(value: str) -> Path:
        from PySide6.QtCore import QUrl
        url = QUrl(value)
        return Path(url.toLocalFile() if url.isLocalFile() else value)

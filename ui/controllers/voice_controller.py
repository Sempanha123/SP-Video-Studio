from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from services.model_service import ModelService
from services.project_service import ProjectService
from services.voice_service import VoiceInUseError, VoiceService, VoiceServiceError
from ui.models.voice_list_model import VoiceListModel


class VoiceController(QObject):
    voicesChanged = Signal()
    selectionChanged = Signal()
    assignmentChanged = Signal()
    modelStateChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    deleteBlocked = Signal(str, int)

    def __init__(
        self,
        service: VoiceService,
        project_service: ProjectService,
        model_service: ModelService,
        logger: logging.Logger,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.project_service = project_service
        self.model_service = model_service
        self.logger = logger
        self.model = VoiceListModel(self)
        self._selected_id = ""
        self._project_id = ""
        self._section_id = ""
        self._query = ""
        self._category = "all"
        self._language = "all"
        self._engine = "all"
        self._sort = "recommended"
        self._preview_cache: dict[str, tuple[str, int]] = {}
        self._pending_preview_key = ""
        self.refresh()

    @Property(QObject, constant=True)
    def voices(self):
        return self.model

    @Property("QVariantMap", notify=selectionChanged)
    def selectedVoice(self) -> dict[str, object]:
        if not self._selected_id:
            return {}
        try:
            return self.service.get(self._selected_id).to_dict()
        except Exception:
            return {}

    @Property("QVariantMap", notify=assignmentChanged)
    def projectVoice(self) -> dict[str, object]:
        if not self._project_id:
            return {}
        try:
            voice = self.service.project_voice(self._project_id)
            return voice.to_dict() if voice else {}
        except Exception:
            return {}

    @Property("QVariantMap", notify=assignmentChanged)
    def sectionVoice(self) -> dict[str, object]:
        if not self._section_id:
            return {}
        try:
            voice = self.service.section_voice(self._section_id)
            return voice.to_dict() if voice else {}
        except Exception:
            return {}

    @Property(str, notify=assignmentChanged)
    def currentProjectId(self) -> str:
        return self._project_id

    @Property(str, notify=assignmentChanged)
    def currentSectionId(self) -> str:
        return self._section_id

    @Property(bool, notify=modelStateChanged)
    def modelReady(self) -> bool:
        try:
            installation = self.model_service.repository.get("voxcpm2")
            return bool(installation and installation.status_code == "installed" and self.model_service.install_path(self.model_service.registry.get("voxcpm2")).is_dir())
        except Exception:
            return False

    @Property(str, notify=selectionChanged)
    def defaultPreviewText(self) -> str:
        language = str(self.selectedVoice.get("language", "en")) if self.selectedVoice else "en"
        return self.service.preview_text(language)

    @Slot()
    def refresh(self) -> None:
        project_language = ""
        project_workflow = ""
        if self._project_id:
            try:
                project = self.project_service.repository.get_by_id(self._project_id)
                if project:
                    project_language = project.language
                    project_workflow = str(project.workflow)
            except Exception:
                pass
        voices = self.service.browse(
            self._query, self._category, self._language, self._engine, self._sort,
            project_language=project_language, project_workflow=project_workflow,
        )
        recommended_categories = set()
        if project_workflow:
            from services.voice_service import WORKFLOW_CATEGORIES
            recommended_categories = WORKFLOW_CATEGORIES.get(project_workflow, set())
        values = []
        for voice in voices:
            item = voice.to_dict()
            item["recommended"] = bool(
                (project_language and voice.language == project_language)
                and (not recommended_categories or voice.category in recommended_categories)
            )
            values.append(item)
        if self._selected_id and not any(item["id"] == self._selected_id for item in values):
            # Keep selected details even if a filter hides the card; don't change user selection.
            pass
        self.model.replace(values, self._selected_id)
        self.voicesChanged.emit()
        self.modelStateChanged.emit()

    @Slot(str)
    def setCurrentProject(self, project_id: str) -> None:
        self._project_id = (project_id or "").strip()
        self._section_id = ""
        self.assignmentChanged.emit()
        self.refresh()

    @Slot(str)
    def setCurrentSection(self, section_id: str) -> None:
        self._section_id = (section_id or "").strip()
        self.assignmentChanged.emit()

    @Slot(str)
    def selectVoice(self, voice_id: str) -> None:
        try:
            self.service.get(voice_id)
        except Exception as exc:
            self._fail(exc); return
        self._selected_id = voice_id
        self.model.set_selected(voice_id)
        self.selectionChanged.emit()

    @Slot(str)
    def setSearch(self, value: str) -> None:
        self._query = value or ""; self.refresh()

    @Slot(str)
    def setCategoryFilter(self, value: str) -> None:
        self._category = (value or "all").lower(); self.refresh()

    @Slot(str)
    def setLanguageFilter(self, value: str) -> None:
        self._language = (value or "all").lower(); self.refresh()

    @Slot(str)
    def setEngineFilter(self, value: str) -> None:
        self._engine = (value or "all").lower(); self.refresh()

    @Slot(str)
    def setSort(self, value: str) -> None:
        self._sort = (value or "recommended").lower(); self.refresh()

    @Slot(str, result=bool)
    def toggleFavorite(self, voice_id: str) -> bool:
        try:
            favorite = self.service.toggle_favorite(voice_id)
            self.refresh(); self.selectionChanged.emit()
            self.operationSucceeded.emit("Voice favorited." if favorite else "Voice removed from favorites.")
            return favorite
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, str, str, str, "QVariantList", result=str)
    def createDesigned(self, name: str, language: str, category: str, description: str, tags) -> str:
        try:
            voice = self.service.create_designed(name, language, category, description, [str(v) for v in tags or []])
            self._selected_id = voice.voice_id; self.refresh(); self.selectionChanged.emit()
            self.operationSucceeded.emit("Voice saved.")
            return voice.voice_id
        except Exception as exc:
            self._fail(exc); return ""

    @Slot(str, str, str, str, bool, result=str)
    def createReference(self, name: str, language: str, category: str, source_url: str, consent: bool) -> str:
        try:
            voice = self.service.create_reference(name, language, category, _local_path(source_url), consent)
            self._selected_id = voice.voice_id; self.refresh(); self.selectionChanged.emit()
            self.operationSucceeded.emit("Reference voice saved locally.")
            return voice.voice_id
        except Exception as exc:
            self._fail(exc); return ""

    @Slot(str, str, str, str, "QVariantList", str, result=bool)
    def editVoice(self, voice_id: str, name: str, language: str, category: str, description: str, tags, notes: str) -> bool:
        try:
            voice = self.service.edit_voice(
                voice_id, name=name, language=language, category=category,
                voice_description=description, style_tags=[str(v) for v in tags or []], notes=notes,
            )
            self._selected_id = voice.voice_id; self.refresh(); self.selectionChanged.emit()
            self.operationSucceeded.emit("Voice updated.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, str, bool, result=bool)
    def replaceReference(self, voice_id: str, source_url: str, consent: bool) -> bool:
        try:
            self.service.replace_reference(voice_id, _local_path(source_url), consent)
            self.refresh(); self.selectionChanged.emit()
            self.operationSucceeded.emit("Reference recording updated.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, result=int)
    def assignmentCount(self, voice_id: str) -> int:
        try:
            return self.service.assignment_count(voice_id)
        except Exception:
            return 0

    @Slot(str, result=str)
    def duplicateVoice(self, voice_id: str) -> str:
        try:
            voice = self.service.duplicate_voice(voice_id)
            self._selected_id = voice.voice_id; self.refresh(); self.selectionChanged.emit()
            self.operationSucceeded.emit("Voice duplicated.")
            return voice.voice_id
        except Exception as exc:
            self._fail(exc); return ""

    @Slot(str, bool, result=bool)
    def deleteVoice(self, voice_id: str, clear_assignments: bool = False) -> bool:
        try:
            self.service.delete_voice(voice_id, clear_assignments)
            if self._selected_id == voice_id:
                self._selected_id = ""
            self.refresh(); self.selectionChanged.emit(); self.assignmentChanged.emit()
            self.operationSucceeded.emit("Voice deleted.")
            return True
        except VoiceInUseError as exc:
            self.deleteBlocked.emit(voice_id, exc.count)
            return False
        except Exception as exc:
            self._fail(exc); return False

    @Slot(result=bool)
    def useSelectedForProject(self) -> bool:
        if not self._project_id or not self._selected_id:
            self.operationFailed.emit("Open a project and select a voice first.")
            return False
        try:
            voice = self.service.assign_project(self._project_id, self._selected_id)
            self.assignmentChanged.emit(); self.refresh()
            self.operationSucceeded.emit(f"Project voice updated to {voice.name}.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(result=bool)
    def useSelectedForSection(self) -> bool:
        if not self._project_id or not self._section_id or not self._selected_id:
            self.operationFailed.emit("Select a script section and a voice first.")
            return False
        try:
            voice = self.service.assign_section(self._project_id, self._section_id, self._selected_id)
            self.assignmentChanged.emit(); self.refresh()
            self.operationSucceeded.emit(f"Section voice updated to {voice.name}.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(result=bool)
    def clearSectionOverride(self) -> bool:
        if not self._project_id or not self._section_id:
            return False
        try:
            self.service.assign_section(self._project_id, self._section_id, None)
            self.assignmentChanged.emit()
            self.operationSucceeded.emit("Section now uses the project voice.")
            return True
        except Exception as exc:
            self._fail(exc); return False

    @Slot(str, str, str, str, str, result="QVariantMap")
    def previewRequest(self, text: str, pace: str, energy: str, tone: str, device: str) -> dict[str, object]:
        return self._preview_request(text, pace, energy, tone, device, None, None, "")

    @Slot(str, str, str, str, str, float, int, str, result="QVariantMap")
    def previewRequestAdvanced(self, text: str, pace: str, energy: str, tone: str, device: str, cfg: float, steps: int, seed_text: str) -> dict[str, object]:
        return self._preview_request(text, pace, energy, tone, device, cfg, steps, seed_text)

    @Slot(str, str, str, str, float, int, str, result="QVariantMap")
    def selectedConfig(self, pace: str, energy: str, tone: str, device: str, cfg: float, steps: int, seed_text: str) -> dict[str, object]:
        if not self._selected_id:
            self.operationFailed.emit("Select a voice first.")
            return {}
        try:
            config = self.service.voice_config(self._selected_id, device=device, pace=pace, energy=energy, tone=tone)
            if cfg > 0:
                config.cfg_value = float(cfg)
            if steps > 0:
                config.inference_timesteps = int(steps)
            clean_seed = (seed_text or "").strip()
            config.seed = int(clean_seed) if clean_seed else config.seed
            self.service.mark_used(self._selected_id)
            return {"voice": self.service.get(self._selected_id).to_dict(), **config.to_dict()}
        except Exception as exc:
            self._fail(exc); return {}

    def _preview_request(self, text: str, pace: str, energy: str, tone: str, device: str, cfg, steps, seed_text: str) -> dict[str, object]:
        if not self._selected_id:
            self.operationFailed.emit("Select a voice first.")
            return {}
        clean_text = (text or "").strip() or self.defaultPreviewText
        if len(clean_text) > 400:
            self.operationFailed.emit("Keep voice previews under 400 characters.")
            return {}
        try:
            config = self.service.voice_config(self._selected_id, device=device, pace=pace, energy=energy, tone=tone)
            if cfg is not None and float(cfg) > 0:
                config.cfg_value = float(cfg)
            if steps is not None and int(steps) > 0:
                config.inference_timesteps = int(steps)
            clean_seed = (seed_text or "").strip()
            if clean_seed:
                config.seed = int(clean_seed)
            settings = config.to_dict()
            key = self.service.preview_cache_key(self._selected_id, clean_text, settings, "openbmb/VoxCPM2")
            self._pending_preview_key = key
            self.service.mark_used(self._selected_id)
            cached = self._preview_cache.get(key)
            if cached and Path(cached[0]).is_file():
                return {"cachedPath": cached[0], "cachedDuration": cached[1], "text": clean_text, **settings}
            return {"cachedPath": "", "cachedDuration": 0, "text": clean_text, **settings}
        except Exception as exc:
            self._fail(exc); return {}

    @Slot(str, int)
    def previewGenerated(self, path: str, duration_ms: int) -> None:
        if self._pending_preview_key and Path(path).is_file():
            self._preview_cache[self._pending_preview_key] = (path, int(duration_ms))
        self._pending_preview_key = ""

    @Slot(str, str, str, result="QVariantMap")
    def resolvedConfig(self, project_id: str, section_id: str, device: str = "auto") -> dict[str, object]:
        try:
            voice = self.service.resolve_voice(project_id, section_id or None)
            if voice is None:
                return {}
            config = self.service.voice_config(voice.voice_id, device=device)
            self.service.mark_used(voice.voice_id)
            return {"voice": voice.to_dict(), **config.to_dict()}
        except Exception as exc:
            self._fail(exc); return {}

    def _fail(self, exc: Exception) -> None:
        self.logger.exception("Voice Studio operation failed")
        if isinstance(exc, VoiceServiceError):
            message = str(exc)
        else:
            message = str(exc).strip() or "SP Video Studio could not complete this voice action."
        self.operationFailed.emit(message)


def _local_path(value: str) -> str:
    raw = str(value or "")
    if raw.startswith("file:"):
        parsed = urlparse(raw)
        path = unquote(parsed.path)
        if parsed.netloc:
            path = f"//{parsed.netloc}{path}"
        if len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path
    return QUrl(raw).toLocalFile() if raw else ""

from __future__ import annotations

from datetime import datetime
from collections.abc import Callable

from PySide6.QtCore import QObject, Property, Signal, Slot

from domain.project import Project
from services.project_service import ProjectError, ProjectFilesMissingError, ProjectService


WORKFLOW_NAMES = {
    "news": "News Studio",
    "story": "Story Studio",
    "translate": "Translate & Dub",
    "video": "Video Studio",
    "shorts": "Shorts Maker",
    "batch": "Batch Factory",
}
LANGUAGE_NAMES = {"en": "English", "km": "Khmer"}


def _display_time(value: str | None) -> str:
    if not value:
        return "Never"
    try:
        moment = datetime.fromisoformat(value).astimezone()
        return moment.strftime("%b %d, %Y · %H:%M")
    except ValueError:
        return value


def project_to_ui(project: Project) -> dict[str, object]:
    return {
        "id": project.project_id,
        "title": project.title,
        "workflow": str(project.workflow),
        "workflowName": WORKFLOW_NAMES.get(str(project.workflow), str(project.workflow).title()),
        "language": project.language,
        "languageName": LANGUAGE_NAMES.get(project.language, project.language.upper()),
        "aspectRatio": project.aspect_ratio,
        "fps": project.fps,
        "status": str(project.status),
        "statusName": str(project.status).replace("_", " ").title(),
        "createdAt": project.created_at,
        "createdDisplay": _display_time(project.created_at),
        "updatedAt": project.updated_at,
        "updatedDisplay": _display_time(project.updated_at),
        "lastOpenedAt": project.last_opened_at or "",
        "lastActivityDisplay": _display_time(project.last_opened_at or project.updated_at),
        "thumbnailPath": project.thumbnail_path or "",
        "projectPath": project.project_path,
    }


class ProjectController(QObject):
    projectsChanged = Signal()
    recentProjectsChanged = Signal()
    currentProjectChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    missingProjectDetected = Signal(str)

    def __init__(self, service: ProjectService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self._projects: list[dict[str, object]] = []
        self._recent_projects: list[dict[str, object]] = []
        self._current_project: dict[str, object] = {}
        self._before_project_change: Callable[[], bool] | None = None
        self.refresh()


    def set_before_project_change(self, callback: Callable[[], bool] | None) -> None:
        self._before_project_change = callback

    def _can_change_project(self, target_id: str = "") -> bool:
        current_id = str(self._current_project.get("id", ""))
        if not current_id or current_id == target_id or self._before_project_change is None:
            return True
        if self._before_project_change():
            return True
        self.operationFailed.emit("Current project work could not be safely closed yet. Please try again when it finishes.")
        return False

    @Property("QVariantList", notify=projectsChanged)
    def projects(self) -> list[dict[str, object]]:
        return self._projects

    @Property("QVariantList", notify=recentProjectsChanged)
    def recentProjects(self) -> list[dict[str, object]]:
        return self._recent_projects

    @Property("QVariantMap", notify=currentProjectChanged)
    def currentProject(self) -> dict[str, object]:
        return self._current_project

    @Slot()
    def refresh(self) -> None:
        self._projects = [project_to_ui(item) for item in self.service.list_projects()]
        self._recent_projects = [
            project_to_ui(item) for item in self.service.list_recent_projects(6)
        ]
        self.projectsChanged.emit()
        self.recentProjectsChanged.emit()

    @Slot(str, str, str, str, int, result=str)
    def createProject(
        self,
        title: str,
        workflow: str,
        language: str,
        aspect_ratio: str,
        fps: int,
    ) -> str:
        try:
            if not self._can_change_project(""):
                return ""
            project = self.service.create_project(title, workflow, language, aspect_ratio, fps)
            self._set_current(project)
            self.refresh()
            self.operationSucceeded.emit("Project created successfully.")
            return project.project_id
        except Exception as exc:
            self._emit_error(exc)
            return ""

    @Slot(str, result=bool)
    def openProject(self, project_id: str) -> bool:
        try:
            if not self._can_change_project(project_id):
                return False
            project = self.service.open_project(project_id)
            self._set_current(project)
            self.refresh()
            return True
        except Exception as exc:
            if isinstance(exc, ProjectFilesMissingError):
                self.missingProjectDetected.emit(project_id)
            self._emit_error(exc)
            return False

    @Slot(str, str, result=bool)
    def renameProject(self, project_id: str, title: str) -> bool:
        try:
            project = self.service.rename_project(project_id, title)
            if self._current_project.get("id") == project_id:
                self._set_current(project)
            self.refresh()
            self.operationSucceeded.emit("Project renamed.")
            return True
        except Exception as exc:
            self._emit_error(exc)
            return False

    @Slot(str, result=str)
    def duplicateProject(self, project_id: str) -> str:
        try:
            project = self.service.duplicate_project(project_id)
            self.refresh()
            self.operationSucceeded.emit("Project duplicated.")
            return project.project_id
        except Exception as exc:
            self._emit_error(exc)
            return ""

    @Slot(str, result=bool)
    def deleteProject(self, project_id: str) -> bool:
        try:
            if self._current_project.get("id") == project_id and not self._can_change_project(""):
                return False
            self.service.delete_project(project_id)
            if self._current_project.get("id") == project_id:
                self._current_project = {}
                self.currentProjectChanged.emit()
            self.refresh()
            self.operationSucceeded.emit("Project deleted.")
            return True
        except Exception as exc:
            self._emit_error(exc)
            return False

    @Slot(str, result=bool)
    def removeFromLibrary(self, project_id: str) -> bool:
        try:
            if self._current_project.get("id") == project_id and not self._can_change_project(""):
                return False
            self.service.remove_from_library(project_id)
            if self._current_project.get("id") == project_id:
                self._current_project = {}
                self.currentProjectChanged.emit()
            self.refresh()
            self.operationSucceeded.emit("Project removed from library.")
            return True
        except Exception as exc:
            self._emit_error(exc)
            return False

    def _set_current(self, project: Project) -> None:
        self._current_project = project_to_ui(project)
        self.currentProjectChanged.emit()

    def _emit_error(self, exc: Exception) -> None:
        if isinstance(exc, ProjectError):
            message = str(exc).strip() or exc.user_message
        elif isinstance(exc, ValueError):
            message = str(exc)
        else:
            message = "SP Video Studio could not complete that project action."
        self.operationFailed.emit(message)

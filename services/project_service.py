from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from domain.project import (
    PROJECT_VERSION,
    Project,
    ProjectStatus,
    ProjectWorkflow,
    SUPPORTED_ASPECT_RATIOS,
    SUPPORTED_FPS,
    SUPPORTED_LANGUAGES,
    utc_now_iso,
)
from storage.json_writer import atomic_write_json, read_json
from storage.repositories.project_repository import ProjectRepository

if TYPE_CHECKING:
    from services.media_service import MediaService
    from services.script_service import ScriptService
    from services.narration_service import NarrationService
    from services.transcription_service import TranscriptionService
    from services.voice_service import VoiceService
    from services.translation_service import TranslationService
    from services.subtitle_service import SubtitleService
    from services.scene_service import SceneService
    from services.ai_director_service import AIDirectorService
    from services.timeline_service import TimelineService


PROJECT_DIRS = (
    "media",
    "audio",
    "subtitles",
    "generated",
    "thumbnails",
    "renders",
    "cache",
)
COPYABLE_DIRS = tuple(name for name in PROJECT_DIRS if name not in {"cache", "renders"})


class ProjectError(RuntimeError):
    user_message = "SP Video Studio could not complete this project action."


class ProjectNotFoundError(ProjectError):
    user_message = "This project could not be found."


class ProjectFilesMissingError(ProjectError):
    user_message = "Project files could not be found."


class InvalidProjectError(ProjectError):
    user_message = "This folder is not a valid SP Video Studio project."


class ProjectValidationError(ProjectError):
    user_message = "Please check the project details and try again."


class ProjectStorageError(ProjectError):
    user_message = "SP Video Studio could not save this project."


def safe_folder_slug(title: str) -> str:
    text = title.strip().lower()
    text = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", text)
    text = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-. ")
    return (text[:48].rstrip("-. ") or "project")


class ProjectService:
    """Application-facing project lifecycle coordinator.

    The repository owns SQL. This service coordinates DB state, the filesystem,
    portable project.json metadata, validation, and safe failure cleanup.
    """

    def __init__(
        self,
        repository: ProjectRepository,
        project_root: Path,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.project_root = Path(project_root).expanduser()
        self.logger = logger or logging.getLogger("sp_video_studio.projects")
        self._known_project_roots: set[Path] = {self.project_root.resolve()}
        self._media_service: MediaService | None = None
        self._script_service: ScriptService | None = None
        self._narration_service: NarrationService | None = None
        self._transcription_service: TranscriptionService | None = None
        self._voice_service: VoiceService | None = None
        self._translation_service: TranslationService | None = None
        self._subtitle_service: SubtitleService | None = None
        self._scene_service: SceneService | None = None
        self._director_service: AIDirectorService | None = None
        self._timeline_service: TimelineService | None = None
        for existing in self.repository.list_all():
            if existing.project_path:
                self._known_project_roots.add(Path(existing.project_path).resolve().parent)

    def set_media_service(self, media_service: "MediaService") -> None:
        """Attach media lifecycle integration without coupling earlier tests to it."""
        self._media_service = media_service

    def set_script_service(self, script_service: "ScriptService") -> None:
        """Attach script duplication integration while keeping the project service layered."""
        self._script_service = script_service

    def set_narration_service(self, narration_service: "NarrationService") -> None:
        self._narration_service = narration_service

    def set_transcription_service(self, transcription_service: "TranscriptionService") -> None:
        self._transcription_service = transcription_service

    def set_voice_service(self, voice_service: "VoiceService") -> None:
        self._voice_service = voice_service

    def set_translation_service(self, translation_service: "TranslationService") -> None:
        self._translation_service = translation_service

    def set_subtitle_service(self, subtitle_service: "SubtitleService") -> None:
        self._subtitle_service = subtitle_service

    def set_scene_service(self, scene_service: "SceneService") -> None:
        self._scene_service = scene_service

    def set_director_service(self, director_service: "AIDirectorService") -> None:
        self._director_service = director_service

    def set_timeline_service(self, timeline_service: "TimelineService") -> None:
        self._timeline_service = timeline_service

    def set_project_root(self, project_root: Path) -> None:
        """Change the location used only for newly created projects."""
        self.project_root = Path(project_root).expanduser()
        self._known_project_roots.add(self.project_root.resolve())

    def ensure_project_root(self) -> None:
        try:
            self.project_root.mkdir(parents=True, exist_ok=True)
            probe = self.project_root / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            self.logger.exception("Project root is unavailable: %s", self.project_root)
            raise ProjectStorageError(
                "Check that the selected project folder is writable."
            ) from exc

    def create_project(
        self,
        title: str,
        workflow: str,
        language: str = "en",
        aspect_ratio: str = "9:16",
        fps: int = 30,
    ) -> Project:
        self.ensure_project_root()
        project = Project(
            title=title.strip(),
            workflow=workflow,
            language=language,
            aspect_ratio=aspect_ratio,
            fps=int(fps),
            status=ProjectStatus.DRAFT,
        )
        self._validate_inputs(project)
        project_dir = self._new_project_path(project.title, project.project_id)
        project.project_path = str(project_dir)

        try:
            self._create_project_structure(project_dir)
            self._write_metadata(project)
            self.repository.create(project)
        except Exception as exc:
            self._cleanup_partial_project(project_dir, project.project_id)
            if isinstance(exc, ProjectError):
                raise
            self.logger.exception("Project creation failed for %s", project.project_id)
            raise ProjectStorageError(
                "SP Video Studio could not create this project. Check that the project folder is writable."
            ) from exc

        self.logger.info("Project created: %s (%s)", project.project_id, project.workflow)
        return project

    def open_project(self, project_id: str) -> Project:
        project = self._require_project(project_id)
        path = Path(project.project_path)
        if not path.is_dir():
            raise ProjectFilesMissingError()
        self.validate_project_folder(path, expected_id=project.project_id)

        old_metadata = project.to_metadata()
        project.last_opened_at = utc_now_iso()
        try:
            self._write_metadata(project)
            self.repository.update(project)
        except Exception as exc:
            try:
                atomic_write_json(path / "project.json", old_metadata)
            except Exception:
                self.logger.exception("Could not restore metadata after open timestamp failure")
            self.logger.exception("Failed to update open timestamp: %s", project.project_id)
            raise ProjectStorageError("The project opened, but its activity time could not be saved.") from exc
        self.logger.info("Project opened: %s", project.project_id)
        return project

    def rename_project(self, project_id: str, title: str) -> Project:
        project = self._require_project(project_id)
        new_title = title.strip()
        if not new_title:
            raise ProjectValidationError("Project name is required.")
        path = Path(project.project_path)
        if not path.is_dir():
            raise ProjectFilesMissingError()
        self.validate_project_folder(path, expected_id=project.project_id)

        old_metadata = project.to_metadata()
        project.title = new_title
        project.updated_at = utc_now_iso()
        try:
            self._write_metadata(project)
            self.repository.update(project)
        except Exception as exc:
            try:
                atomic_write_json(path / "project.json", old_metadata)
            except Exception:
                self.logger.exception("Could not restore metadata after rename failure")
            self.logger.exception("Project rename failed: %s", project.project_id)
            raise ProjectStorageError("SP Video Studio could not rename this project.") from exc
        self.logger.info("Project renamed: %s", project.project_id)
        return project

    def duplicate_project(self, project_id: str) -> Project:
        source = self._require_project(project_id)
        source_path = Path(source.project_path)
        if not source_path.is_dir():
            raise ProjectFilesMissingError()
        self.validate_project_folder(source_path, expected_id=source.project_id)
        self.ensure_project_root()

        now = utc_now_iso()
        duplicate = Project(
            title=f"{source.title} Copy",
            workflow=str(source.workflow),
            language=source.language,
            aspect_ratio=source.aspect_ratio,
            fps=source.fps,
            created_at=now,
            updated_at=now,
            status=ProjectStatus.DRAFT,
            thumbnail_path=None,
            version=source.version,
        )
        destination = self._new_project_path(duplicate.title, duplicate.project_id)
        duplicate.project_path = str(destination)

        try:
            self._create_project_structure(destination)
            for folder_name in COPYABLE_DIRS:
                src = source_path / folder_name
                dst = destination / folder_name
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            self._write_metadata(duplicate)
            self.repository.create(duplicate)
            media_id_map: dict[str, str] = {}
            script_id_map: dict[str, str] = {}
            script_section_map: dict[str, str] = {}
            transcript_id_map: dict[str, str] = {}
            transcript_segment_map: dict[str, str] = {}
            if self._media_service is not None:
                media_id_map = self._media_service.duplicate_project_media_map(source, duplicate)
            if self._script_service is not None:
                script_id_map, script_section_map = self._script_service.duplicate_project_script_with_map(
                    source.project_id, duplicate.project_id, duplicate.title
                )
            if self._voice_service is not None:
                self._voice_service.duplicate_project_assignments(source.project_id, duplicate.project_id)
            generated_audio_map: dict[str, str] = {}
            if self._narration_service is not None:
                generated_audio_map = self._narration_service.duplicate_project_audio(source.project_id, duplicate.project_id)
            if self._transcription_service is not None:
                transcript_id_map, transcript_segment_map = self._transcription_service.duplicate_project_transcripts_with_map(
                    source.project_id, duplicate.project_id, media_id_map
                )
            translation_id_map: dict[str, str] = {}
            translation_segment_map: dict[str, str] = {}
            if self._translation_service is not None:
                _, translation_id_map, translation_segment_map = self._translation_service.duplicate_project_translations_with_map(
                    source.project_id,
                    duplicate.project_id,
                    transcript_map=transcript_id_map,
                    transcript_segment_map=transcript_segment_map,
                    script_map=script_id_map,
                    script_section_map=script_section_map,
                )
            subtitle_track_map: dict[str, str] = {}
            if self._subtitle_service is not None:
                _, subtitle_track_map = self._subtitle_service.duplicate_project_subtitles_with_map(
                    source.project_id, duplicate.project_id, transcript_map=transcript_id_map,
                    translation_map=translation_id_map, transcript_segment_map=transcript_segment_map,
                    translation_segment_map=translation_segment_map,
                )
            scene_id_map: dict[str, str] = {}
            if self._scene_service is not None:
                scene_id_map = self._scene_service.duplicate_project_scenes(
                    source.project_id, duplicate.project_id, media_map=media_id_map,
                    audio_map=generated_audio_map, script_section_map=script_section_map,
                    transcript_segment_map=transcript_segment_map, translation_segment_map=translation_segment_map,
                    subtitle_track_map=subtitle_track_map,
                )
            if self._director_service is not None:
                self._director_service.duplicate_project_plans(
                    source.project_id, duplicate.project_id, script_map=script_id_map,
                    script_section_map=script_section_map, transcript_map=transcript_id_map,
                    translation_map=translation_id_map, scene_map=scene_id_map,
                )
            if self._timeline_service is not None:
                self._timeline_service.duplicate_project_timeline(source.project_id, duplicate.project_id)
        except Exception as exc:
            try:
                if self.repository.get_by_id(duplicate.project_id) is not None:
                    self.repository.delete(duplicate.project_id)
            except Exception:
                self.logger.exception("Could not roll back duplicate project database row")
            self._cleanup_partial_project(destination, duplicate.project_id)
            self.logger.exception("Project duplication failed: %s", source.project_id)
            raise ProjectStorageError("SP Video Studio could not duplicate this project.") from exc

        self.logger.info("Project duplicated: %s -> %s", source.project_id, duplicate.project_id)
        return duplicate


    def update_creative_settings(self, project_id: str, *, aspect_ratio: str | None = None) -> Project:
        """Persist project-level creative settings used by Director without regenerating assets."""
        project = self._require_project(project_id)
        if aspect_ratio is not None:
            if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
                raise ProjectValidationError("Unsupported aspect ratio.")
            project.aspect_ratio = aspect_ratio
        project.updated_at = utc_now_iso()
        project.validate()
        self.repository.update(project)
        self._write_metadata(project)
        return project

    def delete_project(self, project_id: str) -> None:
        project = self._require_project(project_id)
        project_path = Path(project.project_path)
        if not project_path.exists():
            raise ProjectFilesMissingError()
        self.validate_project_folder(project_path, expected_id=project.project_id)
        self._assert_safe_project_path(project_path, project.project_id)

        staging = project_path.resolve().parent / f".deleting-{project.project_id}-{uuid4().hex[:8]}"
        try:
            project_path.rename(staging)
        except OSError as exc:
            self.logger.exception("Could not stage project for deletion: %s", project.project_id)
            raise ProjectStorageError("SP Video Studio could not delete this project safely.") from exc

        try:
            self.repository.delete(project.project_id)
        except Exception as exc:
            try:
                staging.rename(project_path)
            except OSError:
                self.logger.exception("Could not restore project after database delete failure")
            self.logger.exception("Project deletion database step failed: %s", project.project_id)
            raise ProjectStorageError("SP Video Studio could not delete this project safely.") from exc

        try:
            shutil.rmtree(staging)
        except OSError:
            # The library delete is committed. Leave only a hidden, validated staging
            # folder inside the configured project root rather than report a false failure.
            self.logger.exception("Project files need later cleanup: %s", staging)
        self.logger.info("Project deleted: %s", project.project_id)

    def remove_from_library(self, project_id: str) -> None:
        self._require_project(project_id)
        self.repository.delete(project_id)
        self.logger.info("Project removed from library: %s", project_id)

    def list_projects(self) -> list[Project]:
        return self.repository.list_all()

    def list_recent_projects(self, limit: int = 6) -> list[Project]:
        return self.repository.list_recent(limit)

    def validate_project_folder(self, path: Path, expected_id: str | None = None) -> Project:
        path = Path(path)
        metadata_path = path / "project.json"
        if not metadata_path.is_file():
            raise InvalidProjectError("project.json is missing.")
        try:
            metadata = read_json(metadata_path)
            project = Project.from_metadata(metadata, path)
            project.validate()
        except (OSError, ValueError, TypeError) as exc:
            raise InvalidProjectError("project.json is invalid or unsupported.") from exc
        if expected_id is not None and project.project_id != expected_id:
            raise InvalidProjectError("Project ID does not match the library record.")
        if project.version != PROJECT_VERSION:
            raise InvalidProjectError("Project version is not supported.")
        return project

    def _validate_inputs(self, project: Project) -> None:
        if str(project.workflow) not in {item.value for item in ProjectWorkflow}:
            raise ProjectValidationError("Choose a supported workflow.")
        if project.language not in SUPPORTED_LANGUAGES:
            raise ProjectValidationError("Choose English or Khmer.")
        if project.aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            raise ProjectValidationError("Choose a supported aspect ratio.")
        if project.fps not in SUPPORTED_FPS:
            raise ProjectValidationError("Choose a supported FPS value.")
        if not project.title:
            raise ProjectValidationError("Project name is required.")
        project.validate()

    def _new_project_path(self, title: str, project_id: str) -> Path:
        slug = safe_folder_slug(title)
        candidate = self.project_root / f"{slug}_{project_id[:8]}"
        if candidate.exists():
            candidate = self.project_root / f"{slug}_{project_id}"
        if candidate.exists():
            raise ProjectStorageError("A project folder collision occurred. Please try again.")
        return candidate

    @staticmethod
    def _create_project_structure(path: Path) -> None:
        path.mkdir(parents=False, exist_ok=False)
        for name in PROJECT_DIRS:
            (path / name).mkdir()

    def _write_metadata(self, project: Project) -> None:
        atomic_write_json(Path(project.project_path) / "project.json", project.to_metadata())

    def _require_project(self, project_id: str) -> Project:
        project = self.repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()
        return project

    def _assert_safe_project_path(self, path: Path, expected_id: str | None = None) -> None:
        resolved = path.resolve()
        for known_root in self._known_project_roots:
            if resolved == known_root:
                raise InvalidProjectError("Refusing to delete a project root itself.")
            try:
                resolved.relative_to(known_root)
                return
            except ValueError:
                continue
        raise InvalidProjectError("Refusing to delete an unrecognized project folder.")

    def _cleanup_partial_project(self, path: Path, expected_id: str) -> None:
        if not path.exists():
            return
        try:
            self._assert_safe_project_path(path)
            metadata_path = path / "project.json"
            if metadata_path.exists():
                metadata = read_json(metadata_path)
                if str(metadata.get("id")) != expected_id:
                    return
            shutil.rmtree(path)
        except Exception:
            self.logger.exception("Could not clean partial project folder: %s", path)

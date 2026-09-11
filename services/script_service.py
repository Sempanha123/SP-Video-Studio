from __future__ import annotations

import codecs
import logging
from pathlib import Path
from uuid import uuid4

from domain.project import SUPPORTED_LANGUAGES, Project, utc_now_iso
from domain.script import Script, ScriptPace
from domain.script_section import ScriptSection, ScriptSectionType
from services.script_analysis_service import AnalysisResult, ScriptAnalysisService
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository


class ScriptServiceError(RuntimeError):
    user_message = "SP Video Studio could not complete this script action."


class ScriptNotFoundError(ScriptServiceError):
    user_message = "No script could be found for this project."


class ScriptValidationError(ScriptServiceError):
    user_message = "Please check the script details and try again."


class ScriptService:
    def __init__(
        self,
        repository: ScriptRepository,
        project_repository: ProjectRepository,
        analysis: ScriptAnalysisService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.project_repository = project_repository
        self.analysis = analysis or ScriptAnalysisService()
        self.logger = logger or logging.getLogger("sp_video_studio.scripts")

    def load_or_create(self, project_id: str) -> tuple[Script, list[ScriptSection]]:
        project = self._require_project(project_id)
        script = self.repository.get_primary_by_project(project_id)
        if script is None:
            script = self.create_default_script(project)
        return script, self.repository.list_sections(script.script_id)

    def create_default_script(self, project: Project) -> Script:
        existing = self.repository.get_primary_by_project(project.project_id)
        if existing is not None:
            return existing
        script = Script(
            project_id=project.project_id,
            title=f"{project.title} — Script",
            language=project.language,
        )
        sections = [
            ScriptSection(script.script_id, 0, ScriptSectionType.HOOK, "Hook"),
            ScriptSection(script.script_id, 1, ScriptSectionType.BODY, "Body"),
            ScriptSection(script.script_id, 2, ScriptSectionType.OUTRO, "Outro"),
        ]
        self.repository.create(script, sections)
        self.logger.info("Default script created for project %s", project.project_id)
        return script

    def save_script(self, script: Script) -> Script:
        self._assert_script_owner(script.project_id, script.script_id)
        script.updated_at = utc_now_iso()
        return self.repository.update_script(script)

    def save_section(self, project_id: str, section: ScriptSection) -> ScriptSection:
        if not self.repository.section_belongs_to_project(section.section_id, project_id):
            raise ScriptValidationError("This section does not belong to the current project.")
        section.updated_at = utc_now_iso()
        return self.repository.update_section(project_id, section)

    def add_section(self, project_id: str, title: str, section_type: str = "body") -> ScriptSection:
        script, sections = self.load_or_create(project_id)
        clean_title = title.strip() or "New Section"
        if section_type not in {ScriptSectionType.BODY.value, ScriptSectionType.CUSTOM.value}:
            section_type = ScriptSectionType.BODY.value
        section = ScriptSection(script.script_id, len(sections), section_type, clean_title)
        self.repository.create_section(project_id, section)
        self._touch_script(script)
        return section

    def rename_section(self, project_id: str, section_id: str, title: str) -> ScriptSection:
        section = self._require_owned_section(project_id, section_id)
        clean_title = title.strip()
        if not clean_title:
            raise ScriptValidationError("Section name is required.")
        section.title = clean_title
        return self.save_section(project_id, section)

    def duplicate_section(self, project_id: str, section_id: str) -> ScriptSection:
        script, sections = self.load_or_create(project_id)
        source = self._require_owned_section(project_id, section_id)
        index = next(i for i, item in enumerate(sections) if item.section_id == section_id)
        duplicate = ScriptSection(
            script_id=script.script_id,
            order=index + 1,
            section_type=source.type,
            title=f"{source.title} Copy",
            content=source.content,
            notes=source.notes,
            enabled=source.enabled,
            metadata=dict(source.metadata),
        )
        sections.insert(index + 1, duplicate)
        self.repository.replace_sections(project_id, script.script_id, self._normalized_copies(sections))
        self._touch_script(script)
        return duplicate

    def delete_section(self, project_id: str, section_id: str) -> None:
        script, sections = self.load_or_create(project_id)
        self._require_owned_section(project_id, section_id)
        remaining = [item for item in sections if item.section_id != section_id]
        self.repository.delete_section(project_id, section_id)
        now = utc_now_iso()
        for order, section in enumerate(remaining):
            if section.order != order:
                section.order = order
                section.updated_at = now
                self.repository.update_section(project_id, section)
        self._touch_script(script)

    def move_section(self, project_id: str, section_id: str, new_index: int) -> list[ScriptSection]:
        script, sections = self.load_or_create(project_id)
        self._require_owned_section(project_id, section_id)
        if not sections:
            return sections
        old_index = next(i for i, item in enumerate(sections) if item.section_id == section_id)
        target = max(0, min(int(new_index), len(sections) - 1))
        item = sections.pop(old_index)
        sections.insert(target, item)
        now = utc_now_iso()
        for order, section in enumerate(sections):
            section.order = order
            section.updated_at = now
        self.repository.save_order(project_id, script.script_id, sections)
        self._touch_script(script)
        return sections

    def set_section_enabled(self, project_id: str, section_id: str, enabled: bool) -> ScriptSection:
        section = self._require_owned_section(project_id, section_id)
        section.enabled = bool(enabled)
        return self.save_section(project_id, section)

    def set_scene_source(self, project_id: str, section_id: str, enabled: bool) -> ScriptSection:
        """Mark a section as eligible input for future scene generation; no scenes are created here."""
        section = self._require_owned_section(project_id, section_id)
        section.metadata["scene_source"] = bool(enabled)
        return self.save_section(project_id, section)

    def set_language(self, project_id: str, language: str) -> Script:
        if language not in SUPPORTED_LANGUAGES:
            raise ScriptValidationError("Choose English or Khmer.")
        script, _ = self.load_or_create(project_id)
        script.language = language
        return self.save_script(script)

    def set_pace(self, project_id: str, pace: str) -> Script:
        if pace not in {item.value for item in ScriptPace}:
            raise ScriptValidationError("Choose a supported narration pace.")
        script, _ = self.load_or_create(project_id)
        script.pace = pace
        return self.save_script(script)

    def analyze(self, project_id: str) -> AnalysisResult:
        script, sections = self.load_or_create(project_id)
        return self.analysis.analyze_sections(sections, script.language, str(script.pace))

    def get_combined_text(self, project_id: str, enabled_only: bool = True) -> str:
        _, sections = self.load_or_create(project_id)
        chosen = [s for s in sections if (s.enabled or not enabled_only) and s.content.strip()]
        return "\n\n".join(s.content.strip() for s in chosen)

    def prepare_for_tts(self, project_id: str) -> dict[str, object]:
        script, sections = self.load_or_create(project_id)
        chunks: list[str] = []
        boundaries: list[dict[str, object]] = []
        cursor = 0
        for section in sections:
            if not section.enabled or not section.content.strip():
                continue
            text = section.content.strip()
            if chunks:
                cursor += 2
            start = cursor
            chunks.append(text)
            cursor += len(text)
            boundaries.append({
                "section_id": section.section_id,
                "title": section.title,
                "text": text,
                "start_character": start,
                "end_character": cursor,
            })
        return {"language": script.language, "pace": str(script.pace), "text": "\n\n".join(chunks), "sections": boundaries}

    def import_text(self, project_id: str, path: str | Path, mode: str = "add") -> ScriptSection:
        source = Path(path)
        if source.suffix.lower() != ".txt" or not source.is_file():
            raise ScriptValidationError("Choose a valid TXT file.")
        try:
            text = source.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ScriptServiceError("SP Video Studio could not read this text file as UTF-8.") from exc
        except OSError as exc:
            raise ScriptServiceError("SP Video Studio could not read this text file.") from exc
        script, sections = self.load_or_create(project_id)
        imported = ScriptSection(script.script_id, 0, ScriptSectionType.CUSTOM, "Imported Script", content=text)
        if mode == "replace":
            self.repository.replace_sections(project_id, script.script_id, [imported])
        else:
            imported.order = len(sections)
            self.repository.create_section(project_id, imported)
        self._touch_script(script)
        return imported

    def export_text(self, project_id: str, path: str | Path) -> Path:
        target = Path(path)
        if target.suffix.lower() != ".txt":
            target = target.with_suffix(".txt")
        _, sections = self.load_or_create(project_id)
        parts = []
        for section in sections:
            if not section.enabled:
                continue
            parts.append(f"{section.title.upper()}\n\n{section.content.rstrip()}")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n\n".join(parts).rstrip() + "\n", encoding="utf-8")
        except OSError as exc:
            raise ScriptServiceError("SP Video Studio could not export this script.") from exc
        return target

    def duplicate_project_script(self, source_project_id: str, duplicate_project_id: str, duplicate_title: str) -> None:
        source = self.repository.get_primary_by_project(source_project_id)
        if source is None:
            return
        source_sections = self.repository.list_sections(source.script_id)
        now = utc_now_iso()
        clone = Script(
            project_id=duplicate_project_id,
            title=f"{duplicate_title} — Script",
            language=source.language,
            status=str(source.status),
            pace=str(source.pace),
            notes=source.notes,
            created_at=now,
            updated_at=now,
            version=source.version,
            metadata=dict(source.metadata),
        )
        cloned_sections = [
            ScriptSection(
                script_id=clone.script_id,
                order=section.order,
                section_type=section.type,
                title=section.title,
                content=section.content,
                notes=section.notes,
                enabled=section.enabled,
                metadata=dict(section.metadata),
                created_at=now,
                updated_at=now,
            )
            for section in source_sections
        ]
        self.repository.create(clone, cloned_sections)

    def _touch_script(self, script: Script) -> None:
        script.updated_at = utc_now_iso()
        self.repository.update_script(script)

    def _require_project(self, project_id: str) -> Project:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise ScriptValidationError("This project could not be found.")
        return project

    def _assert_script_owner(self, project_id: str, script_id: str) -> Script:
        script = self.repository.get_by_id(script_id)
        if script is None or script.project_id != project_id:
            raise ScriptValidationError("This script does not belong to the current project.")
        return script

    def _require_owned_section(self, project_id: str, section_id: str) -> ScriptSection:
        if not self.repository.section_belongs_to_project(section_id, project_id):
            raise ScriptValidationError("This section does not belong to the current project.")
        section = self.repository.get_section(section_id)
        if section is None:
            raise ScriptNotFoundError("This script section could not be found.")
        return section

    @staticmethod
    def _normalized_copies(sections: list[ScriptSection]) -> list[ScriptSection]:
        now = utc_now_iso()
        for order, section in enumerate(sections):
            section.order = order
            section.updated_at = now
        return sections

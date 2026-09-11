from __future__ import annotations

import json
from pathlib import Path

import pytest

from domain.project import Project
from services.project_service import (
    InvalidProjectError,
    ProjectFilesMissingError,
    ProjectService,
    safe_folder_slug,
)
from storage.database import SQLiteDatabase
from storage.repositories.project_repository import ProjectRepository


@pytest.fixture
def project_system(tmp_path: Path):
    database = SQLiteDatabase(tmp_path / "runtime" / "app.db")
    database.initialize()
    repository = ProjectRepository(database)
    root = tmp_path / "projects"
    service = ProjectService(repository, root)
    return database, repository, service, root


def test_project_path_generation_sanitizes_windows_characters(project_system):
    _, _, service, root = project_system
    project = service.create_project('News: Today / "World"?*', "news", "en", "9:16", 30)
    path = Path(project.project_path)
    assert path.parent == root
    assert project.project_id[:8] in path.name
    assert not any(char in path.name for char in '<>:"/\\|?*')
    assert safe_folder_slug("  Hello World  ") == "hello-world"


def test_create_project_persists_database_and_project_json(project_system):
    _, repository, service, _ = project_system
    project = service.create_project("My News Project", "news", "en", "9:16", 30)

    stored = repository.get_by_id(project.project_id)
    assert stored is not None
    assert stored.title == "My News Project"
    project_path = Path(project.project_path)
    assert (project_path / "project.json").is_file()
    for folder in ("media", "audio", "subtitles", "generated", "thumbnails", "renders", "cache"):
        assert (project_path / folder).is_dir()

    metadata = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
    assert metadata["id"] == project.project_id
    assert metadata["workflow"] == "news"
    assert metadata["version"] == 1


def test_project_repository_read_update_and_recent(project_system):
    _, repository, service, _ = project_system
    first = service.create_project("First", "video", "en", "16:9", 30)
    second = service.create_project("Second", "story", "km", "16:9", 25)
    service.open_project(first.project_id)

    stored = repository.get_by_id(second.project_id)
    assert stored is not None
    stored.status = "ready"
    repository.update(stored)
    assert repository.get_by_id(second.project_id).status == "ready"
    assert service.list_recent_projects(1)[0].project_id == first.project_id


def test_rename_updates_db_and_json_without_renaming_folder(project_system):
    _, repository, service, _ = project_system
    project = service.create_project("Before", "video", "en", "16:9", 30)
    original_path = project.project_path

    renamed = service.rename_project(project.project_id, "After")
    assert renamed.project_path == original_path
    assert repository.get_by_id(project.project_id).title == "After"
    metadata = json.loads((Path(original_path) / "project.json").read_text(encoding="utf-8"))
    assert metadata["title"] == "After"
    assert metadata["id"] == project.project_id


def test_duplicate_gets_new_identity_and_copies_project_content_not_cache(project_system):
    _, repository, service, _ = project_system
    source = service.create_project("Original", "story", "km", "16:9", 30)
    source_path = Path(source.project_path)
    (source_path / "media" / "note.txt").write_text("keep", encoding="utf-8")
    (source_path / "cache" / "preview.tmp").write_text("discard", encoding="utf-8")

    duplicate = service.duplicate_project(source.project_id)
    duplicate_path = Path(duplicate.project_path)
    assert duplicate.project_id != source.project_id
    assert duplicate.title == "Original Copy"
    assert duplicate_path != source_path
    assert (duplicate_path / "media" / "note.txt").read_text(encoding="utf-8") == "keep"
    assert not (duplicate_path / "cache" / "preview.tmp").exists()
    assert repository.get_by_id(duplicate.project_id) is not None
    metadata = json.loads((duplicate_path / "project.json").read_text(encoding="utf-8"))
    assert metadata["id"] == duplicate.project_id


def test_delete_project_removes_only_recognized_project(project_system):
    _, repository, service, _ = project_system
    project = service.create_project("Delete Me", "shorts", "en", "9:16", 30)
    project_path = Path(project.project_path)
    service.delete_project(project.project_id)
    assert repository.get_by_id(project.project_id) is None
    assert not project_path.exists()


def test_safe_deletion_refuses_project_outside_root(project_system, tmp_path: Path):
    _, repository, service, _ = project_system
    outside = tmp_path / "outside-project"
    outside.mkdir()
    for folder in ("media", "audio", "subtitles", "generated", "thumbnails", "renders", "cache"):
        (outside / folder).mkdir()
    project = Project(title="Outside", workflow="video", project_path=str(outside))
    (outside / "project.json").write_text(json.dumps(project.to_metadata()), encoding="utf-8")
    repository.create(project)

    with pytest.raises(Exception):
        service.delete_project(project.project_id)
    assert outside.exists()
    assert repository.get_by_id(project.project_id) is not None


def test_invalid_project_metadata_is_rejected(project_system):
    _, _, service, root = project_system
    bad = root / "bad"
    bad.mkdir(parents=True)
    (bad / "project.json").write_text('{"id": "broken"}', encoding="utf-8")
    with pytest.raises(InvalidProjectError):
        service.validate_project_folder(bad)


def test_missing_folder_does_not_remove_library_record(project_system):
    _, repository, service, _ = project_system
    project = service.create_project("Missing", "video", "en", "16:9", 30)
    project_path = Path(project.project_path)
    for child in sorted(project_path.iterdir(), reverse=True):
        if child.is_dir():
            child.rmdir()
        else:
            child.unlink()
    project_path.rmdir()

    with pytest.raises(ProjectFilesMissingError):
        service.open_project(project.project_id)
    assert repository.get_by_id(project.project_id) is not None


def test_remove_missing_project_from_library_keeps_filesystem_safe(project_system):
    _, repository, service, _ = project_system
    project = service.create_project("Library Only", "video", "en", "16:9", 30)
    project_path = Path(project.project_path)
    service.remove_from_library(project.project_id)
    assert repository.get_by_id(project.project_id) is None
    assert project_path.exists()


def test_restart_reloads_persisted_projects(tmp_path: Path):
    db_path = tmp_path / "runtime" / "app.db"
    root = tmp_path / "projects"

    first_db = SQLiteDatabase(db_path)
    first_db.initialize()
    first_service = ProjectService(ProjectRepository(first_db), root)
    created = first_service.create_project("Persistent", "news", "km", "9:16", 30)

    second_db = SQLiteDatabase(db_path)
    second_db.initialize()
    second_service = ProjectService(ProjectRepository(second_db), root)
    projects = second_service.list_projects()
    assert len(projects) == 1
    assert projects[0].project_id == created.project_id
    reopened = second_service.open_project(created.project_id)
    assert reopened.last_opened_at is not None


def test_create_cleans_partial_folder_when_database_insert_fails(project_system, monkeypatch):
    _, repository, service, root = project_system

    def fail_create(project):
        raise RuntimeError("database write failed")

    monkeypatch.setattr(repository, "create", fail_create)
    with pytest.raises(Exception):
        service.create_project("Rollback Me", "news", "en", "9:16", 30)
    assert list(root.iterdir()) == []

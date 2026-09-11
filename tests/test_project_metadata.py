from pathlib import Path

from domain.project import Project
from storage.json_writer import atomic_write_json, read_json


def test_project_metadata_round_trip(tmp_path: Path):
    project = Project(
        title="Khmer Project",
        workflow="news",
        language="km",
        aspect_ratio="9:16",
        fps=30,
        project_path=str(tmp_path),
    )
    target = tmp_path / "project.json"
    atomic_write_json(target, project.to_metadata())
    loaded = Project.from_metadata(read_json(target), tmp_path)
    assert loaded.project_id == project.project_id
    assert loaded.title == project.title
    assert loaded.language == "km"
    assert loaded.project_path == str(tmp_path)
    assert not (tmp_path / ".project.json.tmp").exists()

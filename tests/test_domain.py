from domain.project import Project
from domain.scene import Scene


def test_project_serializes_core_metadata():
    project = Project(title="Demo", workflow="news", language="en")
    data = project.to_dict()
    assert data["title"] == "Demo"
    assert data["workflow"] == "news"
    assert data["version"] == 1
    assert data["project_id"]


def test_scene_defaults_are_safe_collections():
    first = Scene(scene_id="a", index=0)
    second = Scene(scene_id="b", index=1)
    first.media.append("clip.mp4")
    assert second.media == []

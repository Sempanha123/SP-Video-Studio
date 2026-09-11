from pathlib import Path
from app.paths import AppPaths


def test_discovered_paths_share_root():
    paths = AppPaths.discover()
    assert paths.models.parent == paths.root
    assert paths.cache.parent == paths.root
    assert paths.logs.parent == paths.root


def test_ensure_creates_directories(tmp_path: Path):
    paths = AppPaths(
        root=tmp_path / "app",
        models=tmp_path / "app/models",
        cache=tmp_path / "app/cache",
        temp=tmp_path / "app/temp",
        logs=tmp_path / "app/logs",
        settings=tmp_path / "app/settings",
        downloads=tmp_path / "app/downloads",
    )
    paths.ensure()
    assert paths.root.is_dir()
    assert paths.models.is_dir()
    assert paths.cache.is_dir()
    assert paths.temp.is_dir()
    assert paths.logs.is_dir()
    assert paths.settings.is_dir()
    assert paths.downloads.is_dir()
